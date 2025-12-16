"""Hybrid Random Forest + LSTM training pipeline for predictive maintenance."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

LOGGER = logging.getLogger("hybrid_training")
DEFAULT_TEST_FRACTION = 0.2
MAX_SEQUENCE_LENGTH = 60
BATCH_SIZE = 32
LSTM_EPOCHS = 8
LEARNING_RATE = 1e-3
LEAD_TIME_THRESHOLD = 0.5


def parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "labeled_data",
        type=Path,
        help="CSV file produced by synthetic_failure_labeler",
    )
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=DEFAULT_TEST_FRACTION,
        help="Fraction of tail-window samples per vehicle reserved for testing",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=LSTM_EPOCHS,
        help="Number of training epochs for the LSTM",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=LEARNING_RATE,
        help="Optimizer learning rate for the LSTM",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/hybrid_eval_summary.json"),
        help="Where to store evaluation metrics",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory where trained artifacts will be stored",
    )
    return parser.parse_args(args)


def load_labeled_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["lstm_sequence"] = df["lstm_sequence"].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
    return df


def time_based_split(df: pd.DataFrame, test_fraction: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    train_frames: List[pd.DataFrame] = []
    test_frames: List[pd.DataFrame] = []

    for vehicle_id, group in df.sort_values("timestamp").groupby("vehicle_id"):
        cutoff_index = int(len(group) * (1 - test_fraction))
        if cutoff_index <= 0 or cutoff_index >= len(group):
            train_frames.append(group)
            continue
        train_frames.append(group.iloc[:cutoff_index])
        test_frames.append(group.iloc[cutoff_index:])

    train_df = pd.concat(train_frames).reset_index(drop=True)
    test_df = pd.concat(test_frames).reset_index(drop=True) if test_frames else pd.DataFrame(columns=train_df.columns)
    return train_df, test_df


def prepare_rf_dataset(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler, List[str]]:
    rf_columns = [col for col in train_df.columns if col.startswith("rf_") or col == "risk_score"]
    scaler = StandardScaler()

    X_train = scaler.fit_transform(train_df[rf_columns])
    y_train = train_df["label_imminent_fault"].to_numpy(dtype=np.int64)

    if not test_df.empty:
        X_test = scaler.transform(test_df[rf_columns])
        y_test = test_df["label_imminent_fault"].to_numpy(dtype=np.int64)
    else:
        X_test = np.empty((0, len(rf_columns)))
        y_test = np.empty((0,), dtype=np.int64)

    return X_train, y_train, X_test, y_test, scaler, rf_columns


def train_random_forest(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    return clf


@dataclass
class SequenceSample:
    sequence: List[List[float]]
    label: int
    timestamp: datetime
    vehicle_id: str
    failure_event: int


class TelemetrySequenceDataset(Dataset):
    def __init__(self, samples: List[SequenceSample], max_length: int) -> None:
        self.samples = samples
        self.max_length = max_length
        self.feature_dim = len(samples[0].sequence[0]) if samples else 0

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]
        seq = np.array(sample.sequence, dtype=np.float32)
        seq = seq[-self.max_length :]
        pad_length = self.max_length - len(seq)
        if pad_length > 0:
            padding = np.zeros((pad_length, seq.shape[1]), dtype=np.float32)
            seq = np.vstack([padding, seq])
        return {
            "sequence": torch.from_numpy(seq),
            "label": torch.tensor(sample.label, dtype=torch.float32),
            "timestamp": sample.timestamp,
            "vehicle_id": sample.vehicle_id,
            "failure_event": sample.failure_event,
        }


class LSTMClassifier(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 2) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
        )
        self.dropout = nn.Dropout(0.3)
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last_hidden = out[:, -1, :]
        logits = self.classifier(self.dropout(last_hidden))
        return logits.squeeze(-1)


def collate_samples(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    sequences = torch.stack([item["sequence"] for item in batch])
    labels = torch.stack([item["label"] for item in batch])
    return {
        "sequences": sequences,
        "labels": labels,
        "timestamps": [item["timestamp"] for item in batch],
        "vehicle_ids": [item["vehicle_id"] for item in batch],
        "failure_events": [item["failure_event"] for item in batch],
    }


def prepare_sequence_samples(df: pd.DataFrame) -> List[SequenceSample]:
    samples: List[SequenceSample] = []
    for _, row in df.sort_values("timestamp").iterrows():
        seq = row["lstm_sequence"]
        if not seq:
            continue
        samples.append(
            SequenceSample(
                sequence=seq,
                label=int(row["label_imminent_fault"]),
                timestamp=row["timestamp"],
                vehicle_id=row["vehicle_id"],
                failure_event=int(row["failure_event"]),
            )
        )
    return samples


def split_sequence_samples(
    samples: List[SequenceSample],
    val_fraction: float = 0.2,
) -> Tuple[List[SequenceSample], List[SequenceSample]]:
    if len(samples) <= 1:
        return samples, samples

    val_count = max(1, int(len(samples) * val_fraction))
    train_count = max(1, len(samples) - val_count)
    train_split = samples[:train_count]
    val_split = samples[-val_count:]
    if not train_split:
        train_split = val_split
    return train_split, val_split


def train_lstm(
    train_dataset: TelemetrySequenceDataset,
    val_dataset: TelemetrySequenceDataset | None,
    epochs: int,
    learning_rate: float,
) -> Tuple[LSTMClassifier, torch.device]:
    if train_dataset.feature_dim == 0:
        raise ValueError("Training dataset contains no sequence features")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMClassifier(input_dim=train_dataset.feature_dim).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=_compute_pos_weight(train_dataset))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_samples)
    val_loader = None
    if val_dataset is not None and len(val_dataset) > 0:
        val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_samples)

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            sequences = batch["sequences"].to(device)
            labels = batch["labels"].to(device)
            logits = model(sequences)
            loss = criterion(logits, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            epoch_loss += loss.item() * len(labels)
        avg_loss = epoch_loss / len(train_dataset)

        val_display = "N/A"
        if val_loader is not None:
            model.eval()
            with torch.no_grad():
                val_loss = 0.0
                for batch in val_loader:
                    sequences = batch["sequences"].to(device)
                    labels = batch["labels"].to(device)
                    logits = model(sequences)
                    loss = criterion(logits, labels)
                    val_loss += loss.item() * len(labels)
            val_loss = val_loss / max(1, len(val_dataset))
            val_display = f"{val_loss:.4f}"
        LOGGER.info("Epoch %d | train_loss=%.4f | val_loss=%s", epoch + 1, avg_loss, val_display)

    return model, device


def _compute_pos_weight(dataset: TelemetrySequenceDataset) -> torch.Tensor:
    labels = [sample.label for sample in dataset.samples]
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0:
        return torch.tensor(1.0)
    return torch.tensor(max(neg / pos, 1.0), dtype=torch.float32)


def predict_lstm(
    model: LSTMClassifier,
    dataset: TelemetrySequenceDataset,
    device: torch.device,
) -> Tuple[np.ndarray, List[datetime], List[str], List[int]]:
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_samples)
    model.eval()
    probs: List[float] = []
    timestamps: List[datetime] = []
    vehicle_ids: List[str] = []
    failure_events: List[int] = []

    with torch.no_grad():
        for batch in loader:
            sequences = batch["sequences"].to(device)
            logits = model(sequences)
            prob = torch.sigmoid(logits).cpu().numpy()
            probs.extend(prob.tolist())
            timestamps.extend(batch["timestamps"])
            vehicle_ids.extend(batch["vehicle_ids"])
            failure_events.extend(batch["failure_events"])

    return np.array(probs), timestamps, vehicle_ids, failure_events


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    report = classification_report(y_true, y_pred, zero_division=0, output_dict=True)
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "support": int(y_true.sum()),
        "report": report,
    }


def compute_lead_time_gain(
    timestamps: List[datetime],
    vehicle_ids: List[str],
    probs: np.ndarray,
    failure_events: List[int],
    threshold: float,
) -> Dict[str, Any]:
    events: Dict[str, List[Tuple[datetime, float, int]]] = {}
    for ts, vid, prob, failure in zip(timestamps, vehicle_ids, probs, failure_events):
        events.setdefault(vid, []).append((ts, prob, failure))

    lead_times: List[float] = []
    detection_rates: List[float] = []

    for vid, records in events.items():
        records.sort(key=lambda x: x[0])
        failures = [ts for ts, _, failure in records if failure]
        if not failures:
            continue
        first_failure = failures[0]
        positives = [ts for ts, prob, _ in records if prob >= threshold and ts <= first_failure]
        if positives:
            first_positive = positives[0]
            lead_minutes = (first_failure - first_positive).total_seconds() / 60.0
            lead_times.append(lead_minutes)
            detection_rates.append(1.0)
        else:
            detection_rates.append(0.0)

    avg_lead_time = float(np.mean(lead_times)) if lead_times else 0.0
    detection_rate = float(np.mean(detection_rates)) if detection_rates else 0.0
    return {
        "average_lead_minutes": avg_lead_time,
        "detection_rate": detection_rate,
        "evaluated_failures": len(detection_rates),
    }


def persist_artifacts(
    artifact_dir: Path,
    rf_model: RandomForestClassifier,
    scaler: StandardScaler,
    lstm_model: LSTMClassifier,
    metadata: Dict[str, Any],
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    rf_model_path = artifact_dir / "rf_model.pkl"
    scaler_path = artifact_dir / "rf_scaler.pkl"
    lstm_path = artifact_dir / "lstm_model.pt"
    metadata_path = artifact_dir / "model_metadata.json"

    joblib.dump(rf_model, rf_model_path)
    joblib.dump(scaler, scaler_path)
    torch.save(lstm_model.state_dict(), lstm_path)

    metadata = {
        **metadata,
        "rf_model_path": rf_model_path.name,
        "rf_scaler_path": scaler_path.name,
        "lstm_model_path": lstm_path.name,
    }

    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, default=_json_default)
    LOGGER.info("Persisted artifacts to %s", artifact_dir)


def run_pipeline(args: argparse.Namespace) -> Dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    LOGGER.info("Loading labeled dataset from %s", args.labeled_data)
    df = load_labeled_dataset(args.labeled_data)
    train_df, test_df = time_based_split(df, args.test_fraction)
    LOGGER.info("Train samples: %d | Test samples: %d", len(train_df), len(test_df))
    artifact_dir = args.artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Artifacts will be stored in %s", artifact_dir)

    # Random Forest branch
    X_train, y_train, X_test, y_test, scaler, rf_columns = prepare_rf_dataset(train_df, test_df)
    rf_model = train_random_forest(X_train, y_train)
    rf_metrics: Dict[str, Any] = {}
    if len(y_test) > 0:
        rf_probs = rf_model.predict_proba(X_test)[:, 1]
        rf_preds = (rf_probs >= 0.5).astype(int)
        rf_metrics = evaluate_predictions(y_test, rf_preds)
        LOGGER.info("Random Forest | precision=%.3f | recall=%.3f | f1=%.3f", rf_metrics["precision"], rf_metrics["recall"], rf_metrics["f1_score"])
    else:
        LOGGER.warning("Random Forest | Test set empty; skipping evaluation")

    # LSTM branch
    train_sequences = prepare_sequence_samples(train_df)
    if not train_sequences:
        raise ValueError("Insufficient sequence data to train LSTM model")
    train_split, val_split = split_sequence_samples(train_sequences)
    train_dataset = TelemetrySequenceDataset(train_split, MAX_SEQUENCE_LENGTH)
    val_dataset = TelemetrySequenceDataset(val_split, MAX_SEQUENCE_LENGTH)
    test_sequences = prepare_sequence_samples(test_df)
    test_dataset = (
        TelemetrySequenceDataset(test_sequences, MAX_SEQUENCE_LENGTH)
        if test_sequences
        else None
    )

    lstm_metrics: Dict[str, Any] = {}
    lead_time_metrics: Dict[str, Any] = {}
    model, device = train_lstm(train_dataset, val_dataset, args.epochs, args.learning_rate)
    if test_dataset is not None and len(test_dataset) > 0:
        probs, timestamps, vehicle_ids, failure_events = predict_lstm(model, test_dataset, device)
        lstm_preds = (probs >= 0.5).astype(int)
        y_true = np.array([sample.label for sample in test_dataset.samples])
        lstm_metrics = evaluate_predictions(y_true, lstm_preds)
        LOGGER.info("LSTM | precision=%.3f | recall=%.3f | f1=%.3f", lstm_metrics["precision"], lstm_metrics["recall"], lstm_metrics["f1_score"])
        lead_time_metrics = compute_lead_time_gain(timestamps, vehicle_ids, probs, failure_events, LEAD_TIME_THRESHOLD)
        LOGGER.info(
            "Lead-time | avg_minutes=%.2f | detection_rate=%.2f",
            lead_time_metrics["average_lead_minutes"],
            lead_time_metrics["detection_rate"],
        )
    else:
        LOGGER.warning("LSTM | Test set empty; evaluation skipped")
        probs = np.array([])

    summary = {
        "random_forest": rf_metrics,
        "lstm": lstm_metrics,
        "lead_time": lead_time_metrics,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
    }
    summary["artifact_dir"] = str(artifact_dir)

    model_cpu = model.to(torch.device("cpu"))
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rf_feature_order": rf_columns,
        "sequence_window": MAX_SEQUENCE_LENGTH,
        "rf_threshold": 0.7,
        "lstm_threshold": 0.6,
        "ensemble_weights": {"rf": 0.7, "lstm": 0.3},
        "failure_horizons": {"next_7_days": 7, "next_30_days": 30},
        "metrics": {
            "rf": rf_metrics,
            "lstm": lstm_metrics,
            "lead_time_gain_days": lead_time_metrics,
        },
    }
    persist_artifacts(artifact_dir, rf_model, scaler, model_cpu, metadata)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=_json_default)
    LOGGER.info("Wrote evaluation summary to %s", args.output)
    return summary


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


if __name__ == "__main__":
    summary = run_pipeline(parse_args())
    print(json.dumps(summary, indent=2))

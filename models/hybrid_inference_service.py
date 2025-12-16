"""Hybrid RF+LSTM inference service for predictive maintenance scoring."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import torch
from torch import nn

LOGGER = logging.getLogger("hybrid_inference_service")


class LSTMClassifier(nn.Module):
    """Mirror of the training-time LSTM architecture for loading artifacts."""

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


class HybridInferenceService:
    """Loads persisted artifacts and produces ensemble risk assessments."""

    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir
        metadata_path = artifact_dir / "model_metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

        with metadata_path.open("r", encoding="utf-8") as handle:
            self.metadata = json.load(handle)

        self.rf_threshold = float(self.metadata.get("rf_threshold", 0.7))
        self.lstm_threshold = float(self.metadata.get("lstm_threshold", 0.6))
        self.window_size = int(self.metadata.get("window_size", 60))
        self.sequence_feature_dim = int(self.metadata.get("sequence_feature_dim", 8))
        weights = self.metadata.get("ensemble_weights", {"rf": 0.7, "lstm": 0.3})
        self.rf_weight = float(weights.get("rf", 0.7))
        self.lstm_weight = float(weights.get("lstm", 0.3))
        self.feature_order = list(self.metadata.get("rf_feature_order", []))

        rf_model_path = artifact_dir / self.metadata.get("rf_model_path", "rf_model.pkl")
        scaler_path = artifact_dir / self.metadata.get("rf_scaler_path", "rf_scaler.pkl")
        lstm_path = artifact_dir / self.metadata.get("lstm_model_path", "lstm_model.pt")

        self.rf_model = joblib.load(rf_model_path)
        self.scaler = joblib.load(scaler_path)
        self.lstm = LSTMClassifier(self.sequence_feature_dim)
        state_dict = torch.load(lstm_path, map_location="cpu")
        self.lstm.load_state_dict(state_dict)
        self.lstm.eval()

    def score(self, feature_payload: Dict[str, Any]) -> Dict[str, Any]:
        rf_features = feature_payload.get("rf_features", {})
        lstm_sequence = feature_payload.get("lstm_sequence", [])
        risk_score = _compute_risk_score(rf_features)

        rf_vector = self._prepare_rf_vector(rf_features, risk_score)
        scaled_vector = self.scaler.transform(rf_vector)
        rf_prob = float(self.rf_model.predict_proba(scaled_vector)[0, 1])

        lstm_conf = self._score_lstm(lstm_sequence)
        ensemble_score = float(self.rf_weight * rf_prob + self.lstm_weight * lstm_conf)
        risk_level, urgency = self._apply_gating(rf_prob, lstm_conf)
        estimated_days_to_failure = _estimate_days_to_failure(rf_prob, lstm_conf, risk_score)
        latest_reading = feature_payload.get("latest_reading", {})
        affected_component = _infer_component(rf_features, latest_reading)
        confidence = _compute_confidence(rf_prob, lstm_conf)
        event_timestamp = _resolve_timestamp(feature_payload)
        window_size = self.window_size

        horizons = self.metadata.get("failure_horizons", {"next_7_days": 7, "next_30_days": 30})
        prob_next_7 = self._compute_failure_probability(
            estimated_days_to_failure, ensemble_score, horizons.get("next_7_days", 7)
        )
        prob_next_30 = self._compute_failure_probability(
            estimated_days_to_failure, ensemble_score, horizons.get("next_30_days", 30)
        )

        event = {
            "event_type": "PREDICTIVE_RISK_SIGNAL",
            "vehicle_id": feature_payload.get("vehicle_id"),
            "risk_level": risk_level,
            "rf_fault_prob": float(rf_prob),
            "lstm_degradation_score": lstm_conf,
            "ensemble_risk_score": ensemble_score,
            "immediate_risk_score": ensemble_score,
            "failure_probability_next_7_days": prob_next_7,
            "failure_probability_next_30_days": prob_next_30,
            "estimated_days_to_failure": estimated_days_to_failure,
            "affected_component": affected_component,
            "confidence": confidence,
            "timestamp": event_timestamp,
            "urgency": urgency,
            "context": {
                "usage_pattern": feature_payload.get("usage_pattern"),
                "dtc": feature_payload.get("dtc", []),
                "risk_score": ensemble_score,
                "urgency_signal": lstm_conf,
                "ensemble_score": ensemble_score,
                "window_size": window_size,
                "failure_probabilities": {
                    "next_7_days": prob_next_7,
                    "next_30_days": prob_next_30,
                },
            },
        }

        return event

    def _prepare_rf_vector(self, rf_features: Dict[str, Any], risk_score: float) -> np.ndarray:
        feature_map = {f"rf_{key}": float(value) for key, value in rf_features.items()}
        feature_map["risk_score"] = risk_score
        vector = [feature_map.get(name, 0.0) for name in self.feature_order]
        if not vector:
            raise ValueError("Random Forest feature vector is empty; metadata may be inconsistent")
        return np.array([vector], dtype=np.float32)

    def _score_lstm(self, sequence: List[List[float]]) -> float:
        if not sequence:
            padded = np.zeros((self.window_size, self.sequence_feature_dim), dtype=np.float32)
        else:
            arr = np.array(sequence, dtype=np.float32)
            if arr.ndim != 2 or arr.shape[1] != self.sequence_feature_dim:
                raise ValueError(
                    f"Expected sequence dimension ({self.sequence_feature_dim}), received {arr.shape}"
                )
            arr = arr[-self.window_size :]
            pad_len = self.window_size - len(arr)
            if pad_len > 0:
                padding = np.zeros((pad_len, arr.shape[1]), dtype=np.float32)
                arr = np.vstack([padding, arr])
            padded = arr
        tensor = torch.from_numpy(padded).unsqueeze(0)
        with torch.no_grad():
            logit = self.lstm(tensor)
            prob = torch.sigmoid(logit).item()
        return float(prob)

    def _apply_gating(self, rf_prob: float, lstm_conf: float) -> tuple[str, float]:
        if rf_prob > self.rf_threshold:
            return "HIGH", lstm_conf
        if lstm_conf > self.lstm_threshold:
            return "MEDIUM", lstm_conf
        return "LOW", lstm_conf

    def _compute_failure_probability(
        self,
        days_to_failure: float,
        immediate_risk: float,
        horizon_days: int,
    ) -> float:
        if not math.isfinite(days_to_failure) or days_to_failure < 0:
            return float(np.clip(0.85 * immediate_risk + 0.15, 0.0, 1.0))
        margin = (horizon_days - days_to_failure) / max(horizon_days, 1)
        base = 1 / (1 + math.exp(-margin * 4))
        blended = (0.6 * base) + (0.4 * immediate_risk)
        return float(np.clip(blended, 0.0, 1.0))

    def _build_context(
        self,
        rf_features: Dict[str, Any],
        latest_reading: Dict[str, Any],
        risk_score: float,
        urgency: float,
        ensemble_score: float,
    ) -> Dict[str, Any]:
        dtc_field = latest_reading.get("dtc")
        if dtc_field is None:
            dtc_codes: List[str] = []
        elif isinstance(dtc_field, list):
            dtc_codes = [str(code) for code in dtc_field]
        else:
            dtc_codes = [str(dtc_field)] if str(dtc_field).strip() else []

        return {
            "usage_pattern": latest_reading.get("usage_pattern"),
            "dtc": dtc_codes,
            "risk_score": round(risk_score, 4),
            "urgency_signal": round(float(urgency), 4),
            "ensemble_score": round(ensemble_score, 4),
            "window_size": self.window_size,
        }


def _compute_risk_score(rf_features: Dict[str, Any]) -> float:
    temp_mean = float(rf_features.get("engine_temp_mean", 0.0))
    temp_max = float(rf_features.get("engine_temp_max", temp_mean))
    brake_wear = float(rf_features.get("brake_wear_current", 0.0))
    tire_dev = abs(float(rf_features.get("tire_pressure_mean_dev", 0.0)))
    voltage_min = float(rf_features.get("battery_voltage_min", 0.0))
    dtc_count = float(rf_features.get("dtc_count", 0.0))
    critical = float(rf_features.get("critical_dtc_present", 0.0))

    temp_component = max(temp_mean - 95.0, 0.0) / 30.0
    spike_component = max(temp_max - temp_mean, 0.0) / 40.0
    brake_component = brake_wear / 100.0
    tire_component = tire_dev / 6.0
    voltage_component = max(12.5 - voltage_min, 0.0) / 3.0
    dtc_component = (dtc_count / 5.0) + critical

    risk = (
        0.35 * temp_component
        + 0.1 * spike_component
        + 0.2 * brake_component
        + 0.1 * tire_component
        + 0.15 * voltage_component
        + 0.1 * dtc_component
    )
    return float(min(risk, 1.5))


def _estimate_days_to_failure(rf_prob: float, lstm_conf: float, risk_score: float) -> int:
    severity = 0.45 * rf_prob + 0.35 * lstm_conf + 0.2 * min(risk_score, 1.5) / 1.5
    days = max(1.0, 14.0 * (1.0 - min(severity, 1.0)))
    return int(round(days))


def _infer_component(rf_features: Dict[str, Any], latest_reading: Dict[str, Any]) -> str:
    brake_wear = float(rf_features.get("brake_wear_current", 0.0))
    engine_temp = float(rf_features.get("engine_temp_mean", 0.0))
    battery_min = float(rf_features.get("battery_voltage_min", 0.0))
    tire_dev = abs(float(rf_features.get("tire_pressure_mean_dev", 0.0)))
    dtc_field = latest_reading.get("dtc")
    dtc_codes: List[str]
    if dtc_field is None:
        dtc_codes = []
    elif isinstance(dtc_field, list):
        dtc_codes = [str(code).upper() for code in dtc_field]
    else:
        dtc_codes = [str(dtc_field).upper()]

    if brake_wear >= 70 or "C" in {code[:1] for code in dtc_codes}:
        return "Brakes"
    if engine_temp >= 105 or any(code.startswith("P0") for code in dtc_codes):
        return "Powertrain"
    if battery_min <= 12.0:
        return "Electrical"
    if tire_dev >= 2.5:
        return "Tire"
    return "General"


def _compute_confidence(rf_prob: float, lstm_conf: float) -> float:
    return 0.6 * max(rf_prob, lstm_conf) + 0.4 * min(rf_prob, lstm_conf)


def _resolve_timestamp(feature_payload: Dict[str, Any]) -> str:
    ts = feature_payload.get("timestamp")
    if ts:
        return ts
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory containing persisted model artifacts",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional path to a JSON file containing a telemetry feature payload",
    )
    return parser.parse_args()


def load_payload(path: Path | None) -> Dict[str, Any]:
    if path is not None:
        text = path.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
        if not text:
            raise ValueError("No input received from stdin; provide --input or pipe JSON payload")
    return json.loads(text)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    service = HybridInferenceService(args.artifacts_dir)
    payload = load_payload(args.input)
    result = service.score(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

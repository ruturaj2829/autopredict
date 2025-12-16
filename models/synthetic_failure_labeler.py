"""Synthetic failure and maintenance label generator for telemetry features."""

from __future__ import annotations

import argparse
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

LOGGER = logging.getLogger("synthetic_failure_labeler")
DEFAULT_LEAD_WINDOW_MINUTES = 15
FAILURE_COOLDOWN_MINUTES = 30
MAINTENANCE_DELAY_MINUTES = 20


@dataclass
class LabeledRecord:
    """Container mapping telemetry features to synthetic labels."""

    vehicle_id: str
    timestamp: datetime
    rf_features: Dict[str, Any]
    lstm_sequence: List[List[float]]
    failure_event: int
    maintenance_event: int
    label_imminent_fault: int
    time_to_failure_min: Optional[float]
    risk_score: float

    def to_flattened_record(self) -> Dict[str, Any]:
        """Flatten record for downstream storage."""

        flat = {
            "vehicle_id": self.vehicle_id,
            "timestamp": self.timestamp.isoformat(),
            "failure_event": self.failure_event,
            "maintenance_event": self.maintenance_event,
            "label_imminent_fault": self.label_imminent_fault,
            "time_to_failure_min": self.time_to_failure_min,
            "risk_score": self.risk_score,
        }
        for key, value in self.rf_features.items():
            flat[f"rf_{key}"] = value
        flat["sequence_length"] = len(self.lstm_sequence)
        flat["lstm_sequence"] = json.dumps(self.lstm_sequence)
        return flat


def parse_args(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "feature_file",
        type=Path,
        help="Path to JSON Lines file produced by telemetry_consumer",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/labeled_features.csv"),
        help="Destination CSV for synthetic labels",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--lead-window-min",
        type=int,
        default=DEFAULT_LEAD_WINDOW_MINUTES,
        help="Minutes defining positive imminent fault label",
    )
    return parser.parse_args(args)


def load_feature_records(path: Path) -> pd.DataFrame:
    """Load telemetry feature payloads captured from telemetry_consumer."""

    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.warning("Skipping malformed JSON line: %s", line)
                continue
            records.append(payload)

    if not records:
        raise ValueError(f"No telemetry feature records found in {path}")

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


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
    return min(risk, 1.5)


def _assign_events_for_vehicle(
    vehicle_df: pd.DataFrame,
    lead_window: timedelta,
    rng: random.Random,
) -> List[LabeledRecord]:
    records: List[LabeledRecord] = []
    failure_times: List[datetime] = []
    maintenance_times: List[datetime] = []

    cooldown = timedelta(minutes=FAILURE_COOLDOWN_MINUTES)
    maintenance_delay = timedelta(minutes=MAINTENANCE_DELAY_MINUTES)

    last_failure_time: Optional[datetime] = None

    for _, row in vehicle_df.iterrows():
        timestamp: pd.Timestamp = row["timestamp"]
        ts = timestamp.to_pydatetime()
        rf_features = row["rf_features"]
        lstm_sequence = row["lstm_sequence"]

        risk = _compute_risk_score(rf_features)
        base_prob = 0.005
        prob = min(base_prob + risk * 0.12, 0.65)

        eligible_for_failure = True
        if last_failure_time is not None and ts - last_failure_time < cooldown:
            eligible_for_failure = False

        failure_event = 0
        if eligible_for_failure and rng.random() < prob:
            failure_event = 1
            failure_times.append(ts)
            last_failure_time = ts
            maintenance_times.append(ts + maintenance_delay)

        records.append(
            LabeledRecord(
                vehicle_id=row["vehicle_id"],
                timestamp=ts,
                rf_features=rf_features,
                lstm_sequence=lstm_sequence,
                failure_event=failure_event,
                maintenance_event=0,
                label_imminent_fault=0,
                time_to_failure_min=None,
                risk_score=risk,
            )
        )

    if records:
        for maintenance_time in maintenance_times:
            for record in records:
                if record.timestamp >= maintenance_time:
                    record.maintenance_event = 1
                    break

        for idx, record in enumerate(records):
            next_failure = next(
                (ft for ft in failure_times if ft >= record.timestamp),
                None,
            )
            if next_failure is None:
                continue
            delta = next_failure - record.timestamp
            minutes = delta.total_seconds() / 60.0
            record.time_to_failure_min = minutes
            if delta <= lead_window:
                record.label_imminent_fault = 1

    return records


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _ensure_sequence(value: Any) -> List[List[float]]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return list(value)


def generate_labeled_dataset(
    df: pd.DataFrame,
    lead_window_minutes: int,
    seed: int,
) -> List[LabeledRecord]:
    rng = random.Random(seed)
    lead_window = timedelta(minutes=lead_window_minutes)

    df_sorted = df.sort_values(["vehicle_id", "timestamp"]).reset_index(drop=True)
    df_sorted["rf_features"] = df_sorted["rf_features"].apply(_ensure_dict)
    df_sorted["lstm_sequence"] = df_sorted["lstm_sequence"].apply(_ensure_sequence)

    labeled_records: List[LabeledRecord] = []
    for vehicle_id, vehicle_df in df_sorted.groupby("vehicle_id"):
        labeled_records.extend(_assign_events_for_vehicle(vehicle_df, lead_window, rng))

    return labeled_records


def write_dataset(records: List[LabeledRecord], output_path: Path) -> None:
    rows = [record.to_flattened_record() for record in records]
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    LOGGER.info("Wrote %d labeled records to %s", len(df), output_path)


def run(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    LOGGER.info("Loading telemetry features from %s", args.feature_file)
    df = load_feature_records(args.feature_file)
    LOGGER.info("Loaded %d feature rows", len(df))
    labeled = generate_labeled_dataset(df, args.lead_window_min, args.seed)
    write_dataset(labeled, args.output)


if __name__ == "__main__":
    run(parse_args())

"""End-to-end smoke test for the hybrid predictive maintenance stack."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.master_agent import build_master_agent
from models.hybrid_inference_service import HybridInferenceService

EXPECTED_EVENT_FIELDS = {
    "event_type",
    "vehicle_id",
    "risk_level",
    "rf_fault_prob",
    "lstm_degradation_score",
    "ensemble_risk_score",
    "estimated_days_to_failure",
    "affected_component",
    "confidence",
    "timestamp",
    "urgency",
    "context",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory containing persisted hybrid model artifacts",
    )
    parser.add_argument(
        "--sample",
        type=Path,
        help="Optional path to a telemetry feature payload JSON to reuse",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Emit debug-level logs for deeper inspection",
    )
    return parser.parse_args()


def load_sample_payload(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_synthetic_payload(service: HybridInferenceService) -> Dict[str, Any]:
    ts = datetime.now(timezone.utc).replace(microsecond=0)
    rf_features: Dict[str, Any] = {
        "engine_temp_mean": 107.5,
        "engine_temp_max": 114.2,
        "engine_temp_std": 3.1,
        "engine_temp_rate_per_min": 4.6,
        "battery_voltage_mean": 12.4,
        "battery_voltage_min": 11.9,
        "battery_voltage_drop_per_min": 0.15,
        "brake_wear_current": 82.0,
        "brake_wear_rate_per_min": 0.8,
        "tire_pressure_mean_dev": -1.3,
        "dtc_count": 2,
        "critical_dtc_present": 1,
        "usage_city": 1,
        "usage_highway": 0,
        "usage_mixed": 0,
        "hour_of_day": ts.hour,
        "day_of_week": ts.weekday(),
        "window_size": 12,
        "window_span_minutes": 10.0,
    }

    sequence_template = [
        [103.5, 12.8, 68.0, 31.5, 0.0, 1.0, 0.0, 0.0],
        [105.2, 12.4, 70.0, 31.0, 0.0, 1.0, 0.0, 0.0],
        [108.7, 12.1, 72.5, 30.6, 1.0, 1.0, 0.0, 0.0],
        [110.9, 12.0, 75.1, 30.4, 1.0, 1.0, 0.0, 0.0],
        [112.6, 11.9, 78.0, 30.1, 1.0, 1.0, 0.0, 0.0],
        [113.8, 11.8, 80.5, 29.9, 1.0, 1.0, 0.0, 0.0],
        [114.2, 11.9, 82.0, 29.7, 1.0, 1.0, 0.0, 0.0],
        [112.9, 12.0, 83.5, 29.8, 1.0, 1.0, 0.0, 0.0],
        [111.2, 12.1, 84.0, 30.0, 1.0, 1.0, 0.0, 0.0],
        [110.6, 12.2, 84.5, 30.2, 1.0, 1.0, 0.0, 0.0],
        [109.1, 12.3, 85.0, 30.4, 1.0, 1.0, 0.0, 0.0],
        [108.4, 12.4, 85.2, 30.5, 1.0, 1.0, 0.0, 0.0],
    ]

    latest_reading = {
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "engine_temp": 114.2,
        "battery_voltage": 11.9,
        "brake_wear": 82.0,
        "tire_pressure": 29.7,
        "dtc": ["P0300", "P0420"],
        "usage_pattern": "city",
    }

    payload: Dict[str, Any] = {
        "vehicle_id": "TEST-VEH-001",
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "rf_features": rf_features,
        "lstm_sequence": sequence_template,
        "latest_reading": latest_reading,
    }

    expected_dim = service.sequence_feature_dim
    for row in payload["lstm_sequence"]:
        if len(row) != expected_dim:
            raise ValueError(
                f"Synthetic sequence width {len(row)} does not match expected {expected_dim}"
            )
    return payload


def validate_event(event: Dict[str, Any]) -> None:
    missing = EXPECTED_EVENT_FIELDS - set(event.keys())
    if missing:
        raise AssertionError(f"Risk event missing fields: {sorted(missing)}")

    if event["event_type"] != "PREDICTIVE_RISK_SIGNAL":
        raise AssertionError(f"Unexpected event_type: {event['event_type']}")

    if event["risk_level"] not in {"LOW", "MEDIUM", "HIGH"}:
        raise AssertionError(f"Unexpected risk level: {event['risk_level']}")

    days = int(event.get("estimated_days_to_failure", 0))
    if days <= 0:
        raise AssertionError("Estimated days to failure must be positive")

    confidence = float(event.get("confidence", 0.0))
    if confidence < 0.0 or confidence > 1.5:
        raise AssertionError("Confidence value out of expected range")


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    logging.info("Loading hybrid inference artifacts from %s", args.artifacts_dir)
    service = HybridInferenceService(args.artifacts_dir)

    if args.sample:
        logging.info("Using sample payload from %s", args.sample)
        payload = load_sample_payload(args.sample)
    else:
        logging.info("Constructing synthetic telemetry payload")
        payload = build_synthetic_payload(service)

    logging.info("Scoring payload through hybrid inference service")
    event = service.score(payload)
    validate_event(event)

    logging.info("Routing event through master agent")
    master_agent = build_master_agent()
    master_agent.handle_risk_event(event)

    logging.info("Smoke test completed successfully")
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()

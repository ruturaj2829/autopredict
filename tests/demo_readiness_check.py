"""
End-to-end demo readiness check for the AutoPredict prototype.

This script assumes:
- The FastAPI backend is running on BACKEND_URL (default http://localhost:8080)
- The core model artifacts are available in ./artifacts

It exercises the main demo flows:
1. Hybrid RF + LSTM risk scoring
2. LangGraph orchestration + Safety Twin
3. UEBA guard + scheduler optimization
4. Manufacturing analytics + CAPA recommendations

It prints a JSON summary with PASS/FAIL for each feature and basic details.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import requests


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")


@dataclass
class DemoCheck:
    name: str
    status: bool
    reason: str
    payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "PASS" if self.status else "FAIL",
            "reason": self.reason,
            "payload": self.payload or {},
        }


def _backend_url(path: str) -> str:
    return f"{BACKEND_URL.rstrip('/')}{path}"


def check_hybrid_risk() -> DemoCheck:
    """Call /api/v1/telemetry/risk and validate core fields.

    Uses the same feature schema as tests/hybrid_stack_smoke_test.py to avoid
    shape mismatches with the trained artifacts.
    """
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
        "vehicle_id": "DEMO-VEH-001",
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "rf_features": rf_features,
        "lstm_sequence": sequence_template,
        "latest_reading": latest_reading,
    }
    try:
        resp = requests.post(_backend_url("/api/v1/telemetry/risk"), json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # pragma: no cover - external call
        return DemoCheck("Hybrid RF+LSTM risk", False, str(exc))

    required = {
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
    }
    missing = required - set(data.keys())
    if missing:
        return DemoCheck("Hybrid RF+LSTM risk", False, f"Missing fields: {sorted(missing)}", data)

    return DemoCheck("Hybrid RF+LSTM risk", True, "OK", data)


def check_orchestration(last_event: Dict[str, Any]) -> DemoCheck:
    """Call /api/v1/orchestration/run with the last risk event."""
    try:
        resp = requests.post(_backend_url("/api/v1/orchestration/run"), json=last_event, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # pragma: no cover
        return DemoCheck("LangGraph orchestration", False, str(exc))

    required = {"primary_decision", "safety_decision", "divergence"}
    missing = required - set(data.keys())
    if missing:
        return DemoCheck("LangGraph orchestration", False, f"Missing fields: {sorted(missing)}", data)

    return DemoCheck("LangGraph orchestration", True, "OK", data)


def check_scheduler_guard() -> DemoCheck:
    """Call /api/v1/scheduler/optimize and ensure schedule + UEBA guard decision."""
    now = datetime.utcnow()
    payload = {
        "jobs": [
            {
                "vehicle_id": "DEMO-VEH-001",
                "risk_level": "HIGH",
                "location": "Mumbai, IN",
                "preferred_by": (now + timedelta(days=2)).isoformat(),
                "duration_minutes": 90,
                "days_to_failure": 5,
            }
        ],
        "slots": [
            {
                "technician_id": "tech-01",
                "location": "Mumbai, IN",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "capacity_minutes": 180,
            }
        ],
    }
    try:
        resp = requests.post(_backend_url("/api/v1/scheduler/optimize"), json=payload, timeout=20)
        # even if UEBA blocks (403), we want to see the guard payload
        data = resp.json()
    except Exception as exc:  # pragma: no cover
        return DemoCheck("Scheduler + UEBA guard", False, str(exc))

    if resp.status_code == 403:
        return DemoCheck("Scheduler + UEBA guard", True, "Blocked by UEBA (expected in some scenarios)", data)

    if resp.status_code != 200:
        return DemoCheck("Scheduler + UEBA guard", False, f"Unexpected status: {resp.status_code}", data)

    if "schedule" not in data or "ueba_guard" not in data:
        return DemoCheck("Scheduler + UEBA guard", False, "Missing schedule or UEBA guard in response", data)

    return DemoCheck("Scheduler + UEBA guard", True, "OK", data)


def check_manufacturing_analytics() -> DemoCheck:
    """Call /api/v1/manufacturing/analytics and ensure clusters + CAPA.

    Needs at least as many events as KMeans clusters (4) to avoid fitting errors.
    """
    now_iso = datetime.utcnow().isoformat()
    payload = [
        {
            "vehicle_id": "VEH-101",
            "component": "Brakes",
            "failure_risk": "HIGH",
            "lead_time_days": 5,
            "dtc": ["P0300"],
            "usage_pattern": "city",
            "timestamp": now_iso,
        },
        {
            "vehicle_id": "VEH-102",
            "component": "Engine",
            "failure_risk": "MEDIUM",
            "lead_time_days": 7,
            "dtc": ["P0420"],
            "usage_pattern": "mixed",
            "timestamp": now_iso,
        },
        {
            "vehicle_id": "VEH-103",
            "component": "Battery",
            "failure_risk": "MEDIUM",
            "lead_time_days": 6,
            "dtc": ["P0128"],
            "usage_pattern": "city",
            "timestamp": now_iso,
        },
        {
            "vehicle_id": "VEH-104",
            "component": "Suspension",
            "failure_risk": "LOW",
            "lead_time_days": 9,
            "dtc": ["P0442"],
            "usage_pattern": "highway",
            "timestamp": now_iso,
        },
    ]
    try:
        resp = requests.post(_backend_url("/api/v1/manufacturing/analytics"), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # pragma: no cover
        return DemoCheck("Manufacturing analytics", False, str(exc))

    required = {"clusters", "heatmap", "azure_export_payload", "capa_recommendations"}
    missing = required - set(data.keys())
    if missing:
        return DemoCheck("Manufacturing analytics", False, f"Missing fields: {sorted(missing)}", data)

    return DemoCheck("Manufacturing analytics", True, "OK", data)


def main() -> None:
    checks: List[DemoCheck] = []

    # 1) Hybrid risk
    hybrid = check_hybrid_risk()
    checks.append(hybrid)

    # 2) Orchestration, only if hybrid succeeded
    if hybrid.status:
        checks.append(check_orchestration(hybrid.payload or {}))  # type: ignore[arg-type]
    else:
        checks.append(DemoCheck("LangGraph orchestration", False, "Skipped because hybrid risk failed"))

    # 3) Scheduler + UEBA guard
    checks.append(check_scheduler_guard())

    # 4) Manufacturing analytics
    checks.append(check_manufacturing_analytics())

    summary = {
        "backend_url": BACKEND_URL,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "overall_status": "PASS" if all(c.status for c in checks) else "FAIL",
        "checks": [c.to_dict() for c in checks],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()



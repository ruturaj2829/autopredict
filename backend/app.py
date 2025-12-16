from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from dateutil.parser import isoparse

from models.hybrid_inference_service import HybridInferenceService
from scheduler.optimizer import MaintenanceJob, SchedulingOptimizer, TechnicianSlot
from manufacturing.analytics import ManufacturingAnalytics, ManufacturingEvent
from ueba.engine import UEBAEngine, BehaviorRecord
from ueba.guard import UEBAGuard
from agents.orchestration_graph import build_orchestration_graph

LOGGER = logging.getLogger("backend.app")

app = FastAPI(title="Predictive Maintenance Platform", version="1.0.0")

# CORS so that the Next.js frontend (localhost:3000) can call the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ARTIFACTS_DIR = Path("artifacts")
INFERENCE_SERVICE = HybridInferenceService(ARTIFACTS_DIR)
UEBA_ENGINE = UEBAEngine()
ANALYTICS = ManufacturingAnalytics()
SCHEDULER = SchedulingOptimizer()
SCHEDULER_GUARD = UEBAGuard(UEBA_ENGINE, subject_id="scheduling-agent", allowed_operations=["optimize"])
ORCHESTRATION_GRAPH = build_orchestration_graph()


def _normalize_telemetry_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Accept multiple payload shapes and normalize to the hybrid service schema.

    Supported forms:
    - Native hybrid payload: contains ``rf_features`` and ``lstm_sequence``.
    - Health-check / legacy payloads: ``rolling_features`` + ``sequence``.
    """
    if "rf_features" in payload and "lstm_sequence" in payload:
        return payload

    # Backwards-compatible mapping for health-check tests
    if "rolling_features" in payload and "sequence" in payload:
        return {
            "vehicle_id": payload.get("vehicle_id"),
            "timestamp": payload.get("timestamp"),
            "rf_features": payload["rolling_features"],
            "lstm_sequence": payload["sequence"],
            "latest_reading": {
                "usage_pattern": payload.get("usage_pattern"),
                "dtc": payload.get("dtc", []),
            },
        }

    raise ValueError("Unsupported telemetry payload format")


@app.options("/api/v1/telemetry/risk")
def options_score_vehicle() -> Response:
    """Handle CORS preflight for telemetry risk endpoint."""
    return Response(status_code=200)


@app.post("/api/v1/telemetry/risk")
def score_vehicle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        normalized = _normalize_telemetry_payload(payload)
        event = INFERENCE_SERVICE.score(normalized)
        return event
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/ueba/ingest")
def ueba_ingest(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    parsed = [
        BehaviorRecord(
            timestamp=isoparse(record["timestamp"]),
            subject_id=record["subject_id"],
            operation=record["operation"],
            features=record.get("features", {}),
            metadata=record.get("metadata", {}),
        )
        for record in records
    ]
    return UEBA_ENGINE.ingest(parsed)


@app.options("/api/v1/scheduler/optimize")
def options_schedule_jobs() -> Response:
    """Handle CORS preflight for scheduler endpoint."""
    return Response(status_code=200)


@app.post("/api/v1/scheduler/optimize")
def schedule_jobs(payload: Dict[str, Any]) -> Dict[str, Any]:
    jobs = [
        MaintenanceJob(
            vehicle_id=job["vehicle_id"],
            risk_level=job["risk_level"],
            location=job["location"],
            preferred_by=isoparse(job["preferred_by"]) if job.get("preferred_by") else None,
            duration_minutes=job["duration_minutes"],
            days_to_failure=job.get("days_to_failure"),
        )
        for job in payload["jobs"]
    ]
    slots = [
        TechnicianSlot(
            technician_id=slot["technician_id"],
            location=slot["location"],
            start_time=isoparse(slot["start_time"]),
            capacity_minutes=slot["capacity_minutes"],
        )
        for slot in payload["slots"]
    ]
    # Feature vector for UEBA – simple count of jobs and slots, plus high-risk job ratio.
    high_risk = sum(1 for job in jobs if str(job.risk_level).upper() == "HIGH")
    features = {
        "jobs": float(len(jobs)),
        "slots": float(len(slots)),
        "high_risk_jobs": float(high_risk),
    }
    metadata = {"operation": "optimize"}
    guard_result = SCHEDULER_GUARD.guard_call(
        operation="optimize",
        features=features,
        metadata=metadata,
        func=SCHEDULER.optimize,
        jobs=jobs,
        slots=slots,
    )

    if not guard_result["guard_decision"]["allowed"]:
        raise HTTPException(status_code=403, detail=guard_result)

    schedule = SCHEDULER.optimize(jobs, slots)
    return {
        "schedule": [asdict(assignment) for assignment in schedule],
        "ueba_guard": guard_result["guard_decision"],
    }


@app.options("/api/v1/manufacturing/analytics")
def options_manufacturing_insights() -> Response:
    """Handle CORS preflight for manufacturing analytics endpoint."""
    return Response(status_code=200)


@app.post("/api/v1/manufacturing/analytics")
def manufacturing_insights(events: List[Dict]) -> Dict[str, object]:
    parsed = [ManufacturingEvent(**event) for event in events]
    clusters = ANALYTICS.fit_clusters(parsed)
    heatmap_path = ANALYTICS.plot_heatmap(clusters)
    explorer_payload = ANALYTICS.export_to_azure_data_explorer(clusters)
    # Persist a cluster-level RCA summary for later review / audit.
    summary_path = Path("manufacturing_cluster_summary.json")
    ANALYTICS.save_cluster_summary(clusters, summary_path)
    capa = ANALYTICS.generate_capa_recommendations(clusters)
    return {
        "clusters": clusters.to_dict(orient="records"),
        "heatmap": str(heatmap_path),
        "azure_export_payload": explorer_payload,
        "rca_summary_path": str(summary_path),
        "capa_recommendations": capa,
    }


@app.post("/api/v1/orchestration/run")
def run_orchestration(event: Dict[str, Any]) -> Dict[str, Any]:
    """Execute primary + safety twin orchestration for a predictive risk event.

    This endpoint is demo-focused: it expects a canonical PREDICTIVE_RISK_SIGNAL
    event (as produced by the hybrid inference service) and returns the
    comparison between the primary master agent and the Safety Twin.
    """
    if event.get("event_type") != "PREDICTIVE_RISK_SIGNAL":
        raise HTTPException(status_code=400, detail="Unsupported event_type for orchestration")
    try:
        state = ORCHESTRATION_GRAPH.invoke({"event": event})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "primary_decision": state.get("primary_decision"),
        "safety_decision": state.get("safety_decision"),
        "divergence": state.get("divergence"),
    }

# manufacturing package marker
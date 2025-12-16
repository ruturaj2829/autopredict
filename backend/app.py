from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dateutil.parser import isoparse

from models.hybrid_inference_service import HybridInferenceService
from scheduler.optimizer import MaintenanceJob, SchedulingOptimizer, TechnicianSlot
from manufacturing.analytics import ManufacturingAnalytics, ManufacturingEvent
from ueba.engine import UEBAEngine, BehaviorRecord
from ueba.guard import UEBAGuard
from agents.orchestration_graph import build_orchestration_graph

LOGGER = logging.getLogger("backend.app")

app = FastAPI(title="Predictive Maintenance Platform", version="1.0.0")

# CORS MUST be added BEFORE other middleware and routes
# Get allowed origins from environment or use defaults
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://autopredict.vercel.app",  # Vercel production frontend
]
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

# Log CORS configuration for debugging
LOGGER.info("CORS allowed origins: %s", ALLOWED_ORIGINS)

# CORS middleware - MUST be added first, before any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Additional CORS middleware to ensure headers are always set
class CORSMiddlewareOverride(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

app.add_middleware(CORSMiddlewareOverride)


@app.on_event("startup")
async def startup_event():
    """Log startup completion."""
    LOGGER.info("FastAPI application startup complete")
    LOGGER.info("App is ready to accept requests")
    LOGGER.info("Health check endpoints: GET /, GET /health")
    LOGGER.info("CORS enabled for all origins")

ARTIFACTS_DIR = Path("artifacts")

# Lazy initialization to avoid startup failures if artifacts are missing
_INFERENCE_SERVICE: HybridInferenceService | None = None
_UEBA_ENGINE: UEBAEngine | None = None
_ANALYTICS: ManufacturingAnalytics | None = None
_SCHEDULER: SchedulingOptimizer | None = None
_SCHEDULER_GUARD: UEBAGuard | None = None
_ORCHESTRATION_GRAPH = None


def get_inference_service() -> HybridInferenceService:
    """Lazy-load inference service, creating it if needed."""
    global _INFERENCE_SERVICE
    if _INFERENCE_SERVICE is None:
        try:
            _INFERENCE_SERVICE = HybridInferenceService(ARTIFACTS_DIR)
            LOGGER.info("HybridInferenceService initialized successfully")
        except FileNotFoundError as e:
            LOGGER.warning("Model artifacts not found, inference service unavailable: %s", e)
            raise HTTPException(
                status_code=503,
                detail="Model artifacts not available. Please ensure artifacts are deployed."
            ) from e
    return _INFERENCE_SERVICE


def get_ueba_engine() -> UEBAEngine:
    """Lazy-load UEBA engine."""
    global _UEBA_ENGINE
    if _UEBA_ENGINE is None:
        _UEBA_ENGINE = UEBAEngine()
    return _UEBA_ENGINE


def get_analytics() -> ManufacturingAnalytics:
    """Lazy-load manufacturing analytics."""
    global _ANALYTICS
    if _ANALYTICS is None:
        _ANALYTICS = ManufacturingAnalytics()
    return _ANALYTICS


def get_scheduler() -> SchedulingOptimizer:
    """Lazy-load scheduler."""
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = SchedulingOptimizer()
    return _SCHEDULER


def get_scheduler_guard() -> UEBAGuard:
    """Lazy-load scheduler guard."""
    global _SCHEDULER_GUARD
    if _SCHEDULER_GUARD is None:
        _SCHEDULER_GUARD = UEBAGuard(
            get_ueba_engine(),
            subject_id="scheduling-agent",
            allowed_operations=["optimize"]
        )
    return _SCHEDULER_GUARD


def get_orchestration_graph():
    """Lazy-load orchestration graph."""
    global _ORCHESTRATION_GRAPH
    if _ORCHESTRATION_GRAPH is None:
        _ORCHESTRATION_GRAPH = build_orchestration_graph()
    return _ORCHESTRATION_GRAPH


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
@app.options("/api/v1/{path:path}")
def options_handler(path: str = None) -> Response:
    """Handle CORS preflight for all endpoints."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Max-Age": "3600",
        }
    )


@app.get("/")
def root() -> Dict[str, str]:
    """Health check endpoint that doesn't require models."""
    return {
        "status": "ok",
        "service": "AutoPredict Backend",
        "version": "1.0.0",
        "message": "Service is running"
    }


@app.get("/docs")
def docs_redirect():
    """Ensure /docs endpoint exists for Railway health checks."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> Dict[str, Any]:
    """Detailed health check endpoint."""
    artifacts_exist = (ARTIFACTS_DIR / "model_metadata.json").exists()
    return {
        "status": "ok",
        "artifacts_available": artifacts_exist,
        "service": "AutoPredict Backend",
    }


@app.post("/api/v1/telemetry/risk")
def score_vehicle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        normalized = _normalize_telemetry_payload(payload)
        inference_service = get_inference_service()
        event = inference_service.score(normalized)
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
    return get_ueba_engine().ingest(parsed)


@app.options("/api/v1/scheduler/optimize")
def options_schedule_jobs() -> Response:
    """Handle CORS preflight for scheduler endpoint."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )


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
    scheduler = get_scheduler()
    scheduler_guard = get_scheduler_guard()
    
    guard_result = scheduler_guard.guard_call(
        operation="optimize",
        features=features,
        metadata=metadata,
        func=scheduler.optimize,
        jobs=jobs,
        slots=slots,
    )

    if not guard_result["guard_decision"]["allowed"]:
        raise HTTPException(status_code=403, detail=guard_result)

    schedule = scheduler.optimize(jobs, slots)
    return {
        "schedule": [asdict(assignment) for assignment in schedule],
        "ueba_guard": guard_result["guard_decision"],
    }




@app.post("/api/v1/manufacturing/analytics")
def manufacturing_insights(events: List[Dict]) -> Dict[str, object]:
    parsed = [ManufacturingEvent(**event) for event in events]
    analytics = get_analytics()
    clusters = analytics.fit_clusters(parsed)
    heatmap_path = analytics.plot_heatmap(clusters)
    explorer_payload = analytics.export_to_azure_data_explorer(clusters)
    # Persist a cluster-level RCA summary for later review / audit.
    summary_path = Path("manufacturing_cluster_summary.json")
    analytics.save_cluster_summary(clusters, summary_path)
    capa = analytics.generate_capa_recommendations(clusters)
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
        graph = get_orchestration_graph()
        state = graph.invoke({"event": event})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "primary_decision": state.get("primary_decision"),
        "safety_decision": state.get("safety_decision"),
        "divergence": state.get("divergence"),
    }

# manufacturing package marker
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.types import ASGIApp
from dateutil.parser import isoparse
import traceback

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

# Additional CORS middleware to ensure headers are ALWAYS set, even on errors
class CORSMiddlewareOverride(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Expose-Headers": "*",
                    "Access-Control-Max-Age": "3600",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        try:
            response = await call_next(request)
        except Exception as exc:
            # If an exception occurs, create a response with CORS headers
            LOGGER.error("Exception in request: %s", exc, exc_info=True)
            response = JSONResponse(
                status_code=500,
                content={"error": str(exc), "detail": traceback.format_exc()},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Expose-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Always add CORS headers to response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, Origin"
        response.headers["Access-Control-Expose-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        response.headers["Access-Control-Allow-Credentials"] = "true"
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
        try:
            _ORCHESTRATION_GRAPH = build_orchestration_graph()
            LOGGER.info("Orchestration graph initialized successfully")
        except Exception as e:
            LOGGER.warning("Orchestration graph initialization failed: %s", e)
            # Return None to indicate demo mode
            _ORCHESTRATION_GRAPH = None
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


@app.options("/{full_path:path}")
async def options_handler(full_path: str, request: Request) -> Response:
    """Handle CORS preflight for ALL endpoints - catch-all handler."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Max-Age": "3600",
            "Access-Control-Allow-Credentials": "true",
        }
    )


# Global exception handler to ensure CORS headers on all errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that ensures CORS headers are always present."""
    LOGGER.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url),
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler with CORS headers."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
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


def _generate_demo_response(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Generate demo risk response when model artifacts are unavailable."""
    rf_features = normalized.get("rf_features", {})
    vehicle_id = normalized.get("vehicle_id", "DEMO-VEH-001")
    timestamp = normalized.get("timestamp", datetime.now(timezone.utc).isoformat())
    
    # Mock risk scores based on input features
    engine_temp = float(rf_features.get("engine_temp_mean", 100.0))
    battery_voltage = float(rf_features.get("battery_voltage_min", 12.5))
    brake_wear = float(rf_features.get("brake_wear_current", 50.0))
    dtc_count = int(rf_features.get("dtc_count", 0))
    
    # Simple heuristic-based risk scoring for demo
    rf_prob = min(0.95, max(0.1, (engine_temp - 90) / 30.0 + dtc_count * 0.1))
    lstm_conf = min(0.9, max(0.2, (12.5 - battery_voltage) / 2.0 + brake_wear / 200.0))
    ensemble_score = 0.7 * rf_prob + 0.3 * lstm_conf
    
    risk_level = "HIGH" if ensemble_score > 0.7 else "MEDIUM" if ensemble_score > 0.4 else "LOW"
    urgency = "IMMEDIATE" if ensemble_score > 0.8 else "SOON" if ensemble_score > 0.5 else "SCHEDULED"
    
    return {
        "event_type": "PREDICTIVE_RISK_SIGNAL",
        "vehicle_id": vehicle_id,
        "risk_level": risk_level,
        "rf_fault_prob": round(rf_prob, 4),
        "lstm_degradation_score": round(lstm_conf, 4),
        "ensemble_risk_score": round(ensemble_score, 4),
        "immediate_risk_score": round(ensemble_score, 4),
        "failure_probability_next_7_days": round(min(0.95, ensemble_score * 1.2), 4),
        "failure_probability_next_30_days": round(min(0.98, ensemble_score * 1.5), 4),
        "estimated_days_to_failure": max(1, int(14 * (1 - ensemble_score))),
        "affected_component": "Engine" if engine_temp > 105 else "Battery" if battery_voltage < 12.0 else "Brakes" if brake_wear > 70 else "General",
        "confidence": round(ensemble_score * 0.9, 4),
        "timestamp": timestamp,
        "urgency": urgency,
        "context": {
            "demo_mode": True,
            "message": "Model artifacts not deployed - using heuristic-based demo response",
            "usage_pattern": normalized.get("latest_reading", {}).get("usage_pattern", "mixed"),
            "dtc": normalized.get("latest_reading", {}).get("dtc", []),
        },
    }


@app.post("/api/v1/telemetry/risk")
def score_vehicle(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        normalized = _normalize_telemetry_payload(payload)
        inference_service = get_inference_service()
        event = inference_service.score(normalized)
        return event
    except HTTPException as exc:
        # If it's a 503 (artifacts missing), return demo response instead
        if exc.status_code == 503 and "artifacts" in str(exc.detail).lower():
            LOGGER.info("Artifacts missing, returning demo response")
            return _generate_demo_response(normalized)
        # Re-raise other HTTP exceptions
        raise exc
    except FileNotFoundError as exc:
        # Return demo response when artifacts are missing
        LOGGER.info("Artifacts missing, returning demo response")
        return _generate_demo_response(normalized)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/ueba/ingest")
def ueba_ingest(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        if not records:
            return {"status": "no_records", "events": [], "count": 0}
        
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
    except Exception as exc:
        LOGGER.warning("UEBA ingest failed: %s", exc)
        # Return a safe demo response
        return {
            "status": "error",
            "events": [],
            "count": 0,
            "error": str(exc),
            "demo_mode": True,
        }


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


def _generate_demo_schedule_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate demo schedule response when scheduler is unavailable."""
    jobs = payload.get("jobs", [])
    slots = payload.get("slots", [])
    
    # Simple demo scheduling: assign jobs to slots in order
    schedule = []
    slot_idx = 0
    for job in jobs[:len(slots)]:
        if slot_idx < len(slots):
            schedule.append({
                "job_id": job.get("vehicle_id", f"JOB-{slot_idx}"),
                "technician_id": slots[slot_idx].get("technician_id", f"TECH-{slot_idx}"),
                "start_time": slots[slot_idx].get("start_time"),
                "duration_minutes": job.get("duration_minutes", 60),
            })
            slot_idx += 1
    
    return {
        "schedule": schedule,
        "ueba_guard": {
            "allowed": True,
            "confidence": 0.8,
            "reason": "Demo mode - simplified scheduling",
        },
        "demo_mode": True,
    }


@app.post("/api/v1/scheduler/optimize")
def schedule_jobs(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
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
    except Exception as exc:
        # If scheduler fails, return demo response
        LOGGER.warning("Scheduler failed, returning demo response: %s", exc)
        return _generate_demo_schedule_response(payload)




def _generate_demo_manufacturing_response(events: List[Dict]) -> Dict[str, object]:
    """Generate demo manufacturing analytics response when analytics unavailable."""
    # Simple demo clustering: group by defect type
    clusters = []
    for i, event in enumerate(events[:5]):  # Limit to 5 clusters for demo
        clusters.append({
            "cluster_id": i,
            "defect_type": event.get("defect_type", "UNKNOWN"),
            "count": 1,
            "severity": event.get("severity", "MEDIUM"),
        })
    
    return {
        "clusters": clusters,
        "heatmap": "demo_heatmap.png",
        "azure_export_payload": {"demo": True, "event_count": len(events)},
        "rca_summary_path": "demo_cluster_summary.json",
        "capa_recommendations": [
            {
                "recommendation": "Review manufacturing process for identified defect patterns",
                "priority": "MEDIUM",
                "demo_mode": True,
            }
        ],
        "demo_mode": True,
    }


@app.post("/api/v1/manufacturing/analytics")
def manufacturing_insights(events: List[Dict]) -> Dict[str, object]:
    try:
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
    except Exception as exc:
        # If analytics fails, return demo response
        LOGGER.warning("Manufacturing analytics failed, returning demo response: %s", exc)
        return _generate_demo_manufacturing_response(events)




def _generate_demo_orchestration_response(event: Dict[str, Any]) -> Dict[str, Any]:
    """Generate demo orchestration response when agents are unavailable."""
    risk_level = event.get("risk_level", "MEDIUM")
    urgency = event.get("urgency", "SOON")
    days_to_failure = event.get("estimated_days_to_failure", 7)
    ensemble_score = event.get("ensemble_risk_score", 0.5)
    
    # Demo primary decision
    primary_decision = {
        "risk_level": risk_level,
        "urgency": urgency,
        "days_to_failure": days_to_failure,
        "action": "SCHEDULE_MAINTENANCE" if ensemble_score > 0.5 else "MONITOR",
        "confidence": round(ensemble_score, 4),
    }
    
    # Demo safety twin decision (slightly more conservative)
    safety_decision = {
        "risk_level": "HIGH" if risk_level == "MEDIUM" and ensemble_score > 0.6 else risk_level,
        "urgency": "IMMEDIATE" if urgency == "SOON" and ensemble_score > 0.7 else urgency,
        "days_to_failure": max(1, days_to_failure - 2),
        "action": "SCHEDULE_MAINTENANCE",
        "confidence": round(min(0.95, ensemble_score * 1.1), 4),
    }
    
    # Demo divergence
    divergence = {
        "has_divergence": primary_decision["action"] != safety_decision["action"],
        "primary_action": primary_decision["action"],
        "safety_action": safety_decision["action"],
        "escalation_recommended": safety_decision["risk_level"] == "HIGH" and primary_decision["risk_level"] != "HIGH",
        "demo_mode": True,
    }
    
    return {
        "primary_decision": primary_decision,
        "safety_decision": safety_decision,
        "divergence": divergence,
    }


@app.post("/api/v1/orchestration/run")
def run_orchestration(event: Dict[str, Any]) -> Dict[str, Any]:
    """Execute primary + safety twin orchestration for a predictive risk event.

    This endpoint is demo-focused: it expects a canonical PREDICTIVE_RISK_SIGNAL
    event (as produced by the hybrid inference service) and returns the
    comparison between the primary master agent and the Safety Twin.
    """
    try:
        # Validate event type
        if not event or event.get("event_type") != "PREDICTIVE_RISK_SIGNAL":
            LOGGER.warning("Invalid event type for orchestration: %s", event.get("event_type") if event else "None")
            # Return demo response instead of error for better UX
            return _generate_demo_orchestration_response(event or {})
        
        graph = get_orchestration_graph()
        if graph is None:
            # Demo mode: return mock orchestration response
            LOGGER.info("Orchestration graph unavailable, returning demo response")
            return _generate_demo_orchestration_response(event)
        
        try:
            state = graph.invoke({"event": event})
            return {
                "primary_decision": state.get("primary_decision"),
                "safety_decision": state.get("safety_decision"),
                "divergence": state.get("divergence"),
            }
        except Exception as graph_exc:
            # If graph execution fails, return demo response
            LOGGER.warning("Orchestration graph execution failed: %s", graph_exc)
            return _generate_demo_orchestration_response(event)
    except Exception as exc:
        # Catch-all: return demo response instead of error
        LOGGER.warning("Orchestration endpoint error, returning demo response: %s", exc)
        return _generate_demo_orchestration_response(event if isinstance(event, dict) else {})

# manufacturing package marker
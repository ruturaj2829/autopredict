import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore

try:
    import pyodbc
except ImportError:
    pyodbc = None  # type: ignore

try:
    from azure.cognitiveservices.speech import SpeechConfig
except ImportError:
    SpeechConfig = None  # type: ignore


BACKEND = os.getenv("BACKEND_URL", "http://localhost:8080")


@dataclass
class Check:
    name: str
    status: bool
    reason: str
    payload: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "PASS" if self.status else "FAIL",
            "reason": self.reason,
            "payload": self.payload or {},
        }


def check_ueba() -> Check:
    sample = [
        {
            "timestamp": "2025-12-14T12:00:00Z",
            "subject_id": "hc-tech-1",
            "operation": "login",
            "features": {"latency": 0.3, "risk_factor": 0.7},
        }
    ]
    try:
        resp = requests.post(f"{BACKEND}/api/v1/ueba/ingest", json=sample, timeout=10)
        if resp.status_code == 200:
            return Check("UEBA ingest", True, "OK", resp.json())
        return Check("UEBA ingest", False, f"Status {resp.status_code}", resp.json())
    except requests.RequestException as exc:
        return Check("UEBA ingest", False, str(exc))


def check_scheduler() -> Check:
    sample = {
        "jobs": [
            {
                "vehicle_id": "hc-001",
                "risk_level": "HIGH",
                "location": "Detroit",
                "preferred_by": "2025-12-16T08:00:00Z",
                "duration_minutes": 60,
            }
        ],
        "slots": [
            {
                "technician_id": "tech-01",
                "location": "Detroit",
                "start_time": "2025-12-15T08:00:00Z",
                "capacity_minutes": 120,
            }
        ],
    }
    try:
        resp = requests.post(f"{BACKEND}/api/v1/scheduler/optimize", json=sample, timeout=10)
        if resp.status_code == 200:
            return Check("Scheduler optimize", True, "OK", resp.json())
        return Check("Scheduler optimize", False, f"Status {resp.status_code}", resp.json())
    except requests.RequestException as exc:
        return Check("Scheduler optimize", False, str(exc))


def check_timescale(dsn: Optional[str]) -> Check:
    if not psycopg2:
        return Check("TimescaleDB", False, "psycopg2-binary not installed")
    if not dsn:
        return Check("TimescaleDB", False, "TIMESCALE_DSN not set")
    try:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT NOW();")
            return Check("TimescaleDB", True, "Connected", {"now": str(cur.fetchone()[0])})
    except Exception as exc:
        return Check("TimescaleDB", False, str(exc))


def check_azure_postgres(dsn: Optional[str]) -> Check:
    if not psycopg2:
        return Check("Azure PostgreSQL", False, "psycopg2-binary not installed")
    if not dsn:
        return Check("Azure PostgreSQL", False, "AZURE_POSTGRES_DSN not set")
    try:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT version();")
            return Check("Azure PostgreSQL", True, "Connected", {"version": cur.fetchone()[0]})
    except Exception as exc:
        return Check("Azure PostgreSQL", False, str(exc))


def check_azure_sql(conn_str: Optional[str]) -> Check:
    if not pyodbc:
        return Check("Azure SQL Database", False, "pyodbc not installed")
    if not conn_str:
        return Check("Azure SQL Database", False, "AZURE_SQL_CONNECTION not set")
    try:
        with pyodbc.connect(conn_str, timeout=5) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION;")
            return Check("Azure SQL Database", True, "Connected", {"version": cursor.fetchone()[0]})
    except Exception as exc:
        return Check("Azure SQL Database", False, str(exc))


def check_speech(key: Optional[str], region: Optional[str]) -> Check:
    if not key or not region:
        return Check("Azure Speech Service", False, "Key/region not set")
    if not SpeechConfig:
        return Check("Azure Speech Service", False, "azure-cognitiveservices-speech not installed")
    try:
        SpeechConfig(subscription=key, region=region)
        return Check("Azure Speech Service", True, "Configured")
    except Exception as exc:
        return Check("Azure Speech Service", False, str(exc))


def main() -> None:
    results: List[Check] = [
        check_ueba(),
        check_scheduler(),
        check_timescale(os.getenv("TIMESCALE_DSN")),
        check_azure_postgres(os.getenv("AZURE_POSTGRES_DSN")),
        check_azure_sql(os.getenv("AZURE_SQL_CONNECTION")),
        check_speech(os.getenv("AZURE_SPEECH_KEY"), os.getenv("AZURE_SPEECH_REGION")),
    ]
    print(json.dumps([r.as_dict() for r in results], indent=2))


if __name__ == "__main__":
    main()
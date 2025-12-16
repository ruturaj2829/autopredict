import json
import os
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
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


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
TELEMETRY_ENDPOINT = f"{BACKEND_URL}/api/v1/telemetry/risk"
UEBA_ENDPOINT = f"{BACKEND_URL}/api/v1/ueba/ingest"
SCHEDULER_ENDPOINT = f"{BACKEND_URL}/api/v1/scheduler/optimize"
MANUFACTURING_ENDPOINT = f"{BACKEND_URL}/api/v1/manufacturing/analytics"
ELASTIC_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
SUMMARY_PATH = Path("tests/system_health_report.json")


@dataclass
class CheckResult:
    name: str
    status: bool
    detail: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthReport:
    timestamp: str
    results: List[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    @property
    def ok(self) -> bool:
        return all(result.status for result in self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_status": "PASS" if self.ok else "FAIL",
            "results": [
                {
                    "name": result.name,
                    "status": "PASS" if result.status else "FAIL",
                    "detail": result.detail,
                    "metadata": result.metadata,
                }
                for result in self.results
            ],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))
        print(f"[INFO] Health summary written to {path}")


def ping_tcp(host: str, port: int, timeout: float = 5.0) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def check_backend() -> CheckResult:
    try:
        resp = requests.get(f"{BACKEND_URL}/docs", timeout=10)
        status = resp.status_code == 200
        detail = f"/docs responded with {resp.status_code}"
    except requests.RequestException as exc:
        status = False
        detail = f"Failed to reach backend: {exc}"
    return CheckResult("FastAPI backend", status, detail)


def check_inference() -> CheckResult:
    payload = {
        "vehicle_id": "HEALTH-CHECK-001",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "usage_pattern": "city",
        "dtc": ["P0420"],
        "rolling_features": {"speed_mean": 45.2, "speed_std": 3.1, "brake_pressure_mean": 32.5},
        "sequence": [[0.1, 0.2, 0.3]] * 60,
    }
    try:
        resp = requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=15)
        status = resp.status_code == 200
        detail = f"Telemetry risk endpoint returned {resp.status_code}"
        metadata = resp.json() if status else {}
    except requests.RequestException as exc:
        status = False
        detail = f"Telemetry risk call failed: {exc}"
        metadata = {}
    return CheckResult("Hybrid inference service", status, detail, metadata)


def check_ueba() -> CheckResult:
    payload = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "subject_id": "technician-42",
            "operation": "login",
            "features": {"latency": 0.23, "access_level": 2.0, "geo_distance": 3.4},
            "metadata": {"ip": "192.168.1.5"},
        }
    ]
    try:
        resp = requests.post(UEBA_ENDPOINT, json=payload, timeout=15)
        status = resp.status_code == 200
        detail = f"UEBA ingest returned {resp.status_code}"
        metadata = resp.json() if status else {}
    except requests.RequestException as exc:
        status = False
        detail = f"UEBA ingest call failed: {exc}"
        metadata = {}
    return CheckResult("UEBA engine", status, detail, metadata)


def check_scheduler() -> CheckResult:
    now = datetime.utcnow()
    payload = {
        "jobs": [
            {
                "vehicle_id": "HEALTH-CHECK-001",
                "risk_level": "HIGH",
                "location": "Detroit, MI",
                "preferred_by": (now + timedelta(days=2)).isoformat(),
                "duration_minutes": 90,
                "days_to_failure": 8,
            }
        ],
        "slots": [
            {
                "technician_id": "tech-01",
                "location": "Detroit, MI",
                "start_time": (now + timedelta(days=1)).isoformat(),
                "capacity_minutes": 180,
            }
        ],
    }
    try:
        resp = requests.post(SCHEDULER_ENDPOINT, json=payload, timeout=15)
        status = resp.status_code == 200 and len(resp.json().get("schedule", [])) > 0
        detail = f"Scheduler returned {resp.status_code}"
        metadata = resp.json() if resp.ok else {}
    except requests.RequestException as exc:
        status = False
        detail = f"Scheduler call failed: {exc}"
        metadata = {}
    return CheckResult("Scheduling optimizer", status, detail, metadata)


def check_manufacturing() -> CheckResult:
    payload = [
        {
            "vehicle_id": f"VEH-{idx:03d}",
            "component": component,
            "failure_risk": "HIGH" if idx % 2 == 0 else "MEDIUM",
            "lead_time_days": 10 - idx,
            "dtc": ["P0300"],
            "usage_pattern": "city",
            "timestamp": datetime.utcnow().isoformat(),
        }
        for idx, component in enumerate(["Brakes", "Engine", "Battery", "Suspension"], start=1)
    ]
    try:
        resp = requests.post(MANUFACTURING_ENDPOINT, json=payload, timeout=30)
        status = resp.status_code == 200
        detail = f"Manufacturing analytics returned {resp.status_code}"
        metadata = {"heatmap": resp.json().get("heatmap")} if status else {}
    except requests.RequestException as exc:
        status = False
        detail = f"Manufacturing analytics call failed: {exc}"
        metadata = {}
    return CheckResult("Manufacturing analytics", status, detail, metadata)


def check_elasticsearch() -> CheckResult:
    try:
        resp = requests.get(f"{ELASTIC_URL}/_cluster/health", timeout=10)
        status = resp.status_code == 200
        detail = f"Elasticsearch health status: {resp.json().get('status') if status else 'unknown'}"
    except requests.RequestException as exc:
        status = False
        detail = f"Elasticsearch unreachable: {exc}"
    return CheckResult("Elasticsearch cluster", status, detail)


def check_timescale() -> CheckResult:
    dsn = os.getenv("TIMESCALE_DSN")
    if not (dsn and psycopg2):
        return CheckResult("TimescaleDB", False, "DSN missing or psycopg2 not installed")
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        current = cur.fetchone()[0]
        cur.close()
        conn.close()
        return CheckResult("TimescaleDB", True, "Connection successful", {"server_time": str(current)})
    except Exception as exc:  # pragma: no cover
        return CheckResult("TimescaleDB", False, f"Connection failed: {exc}")


def check_postgres() -> CheckResult:
    dsn = os.getenv("AZURE_POSTGRES_DSN")
    if not (dsn and psycopg2):
        return CheckResult("Azure PostgreSQL", False, "AZURE_POSTGRES_DSN missing or psycopg2 not installed")
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return CheckResult("Azure PostgreSQL", True, "Connection successful", {"version": version})
    except Exception as exc:  # pragma: no cover
        return CheckResult("Azure PostgreSQL", False, f"Connection failed: {exc}")


def check_sql_server() -> CheckResult:
    conn_string = os.getenv("AZURE_SQL_CONNECTION")
    if not conn_string:
        return CheckResult("Azure SQL Database", False, "AZURE_SQL_CONNECTION missing")
    if not pyodbc:
        return CheckResult("Azure SQL Database", False, "pyodbc not installed")
    try:
        conn = pyodbc.connect(conn_string, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION;")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return CheckResult("Azure SQL Database", True, "Connection successful", {"version": version})
    except Exception as exc:  # pragma: no cover
        return CheckResult("Azure SQL Database", False, f"Connection failed: {exc}")


def check_azure_speech() -> CheckResult:
    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if not (key and region):
        return CheckResult("Azure Speech Service", False, "Speech key/region not set")
    if not SpeechConfig:
        return CheckResult("Azure Speech Service", False, "azure-cognitiveservices-speech not installed")
    try:
        SpeechConfig(subscription=key, region=region)
        return CheckResult("Azure Speech Service", True, "Configuration instantiated successfully")
    except Exception as exc:  # pragma: no cover
        return CheckResult("Azure Speech Service", False, f"Failed to instantiate SpeechConfig: {exc}")


def main() -> None:
    report = SystemHealthReport(timestamp=datetime.utcnow().isoformat() + "Z")

    print("[INFO] Running system health checks…")
    for check in (
        check_backend,
        check_inference,
        check_ueba,
        check_scheduler,
        check_manufacturing,
        check_elasticsearch,
        check_timescale,
        check_postgres,
        check_sql_server,
        check_azure_speech,
    ):
        start = time.perf_counter()
        result = check()
        elapsed = time.perf_counter() - start
        result.metadata.setdefault("duration_sec", round(elapsed, 3))
        report.add(result)
        print(f"[{result.name}] {'PASS' if result.status else 'FAIL'} – {result.detail}")

    report.save(SUMMARY_PATH)
    if report.ok:
        print("\n✅  All services verified successfully.")
    else:
        print("\n❌  Some checks failed. Review the health report for details.")


if __name__ == "__main__":
    main()
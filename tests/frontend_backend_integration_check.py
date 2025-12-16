"""
Lightweight frontend–backend integration check for the AutoPredict prototype.

What this script verifies:
1. The Next.js frontend is running and serving the main page.
2. The FastAPI backend is running and serving /docs.
3. The frontend build has the expected title text so we know the right app is running.

Note: This script does not execute the browser-side button clicks. Use it as a
quick sanity check before doing a manual demo walkthrough.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")


@dataclass
class CheckResult:
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


def check_frontend_root() -> CheckResult:
    try:
        resp = requests.get(FRONTEND_URL, timeout=15)
        status_ok = resp.status_code == 200
        if not status_ok:
            return CheckResult(
                "Frontend /",
                False,
                f"Unexpected status code: {resp.status_code}",
                {"status_code": resp.status_code},
            )
        html = resp.text
        if "AutoPredict \u2013 Judge-Friendly Frontend" not in html:
            return CheckResult(
                "Frontend /",
                False,
                "Page loaded but expected title text not found",
            )
        return CheckResult("Frontend /", True, "OK")
    except Exception as exc:  # pragma: no cover - external call
        return CheckResult("Frontend /", False, str(exc))


def check_backend_docs() -> CheckResult:
    try:
        resp = requests.get(f"{BACKEND_URL.rstrip('/')}/docs", timeout=15)
        status_ok = resp.status_code == 200
        if not status_ok:
            return CheckResult(
                "Backend /docs",
                False,
                f"Unexpected status code: {resp.status_code}",
                {"status_code": resp.status_code},
            )
        return CheckResult("Backend /docs", True, "OK")
    except Exception as exc:  # pragma: no cover
        return CheckResult("Backend /docs", False, str(exc))


def main() -> None:
    checks = [
        check_frontend_root(),
        check_backend_docs(),
    ]
    summary = {
        "frontend_url": FRONTEND_URL,
        "backend_url": BACKEND_URL,
        "overall_status": "PASS" if all(c.status for c in checks) else "FAIL",
        "checks": [c.to_dict() for c in checks],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()



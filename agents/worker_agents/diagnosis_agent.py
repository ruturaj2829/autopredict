"""Diagnosis agent that turns risk events into clear fault hypotheses."""

from __future__ import annotations

import logging
from typing import Any, Dict

LOGGER = logging.getLogger("diagnosis_agent")


class DiagnosisAgent:
    """Generates simple, human-readable diagnostic hypotheses from risk events."""

    def hypothesize_fault(self, event: Dict[str, Any]) -> str:
        component = str(event.get("affected_component", "System"))
        risk_level = str(event.get("risk_level", "LOW")).upper()
        days = event.get("estimated_days_to_failure")

        if risk_level == "HIGH":
            msg = f"Likely imminent {component.lower()} failure within {days} days."
        elif risk_level == "MEDIUM":
            msg = f"Progressive degradation detected in {component.lower()}; schedule inspection soon."
        else:
            msg = f"No immediate fault suspected; continue monitoring {component.lower()}."

        LOGGER.info("Diagnosis: %s | vehicle=%s", msg, event.get("vehicle_id"))
        return msg



"""Data analysis agent for summarizing telemetry and risk trends."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

LOGGER = logging.getLogger("data_analysis_agent")


class DataAnalysisAgent:
    """Performs lightweight analytics over recent risk events for explainability."""

    def summarize_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not events:
            return {"count": 0, "components": {}, "avg_confidence": 0.0}

        components: Dict[str, int] = {}
        confidences: List[float] = []

        for event in events:
            component = str(event.get("affected_component", "Unknown"))
            components[component] = components.get(component, 0) + 1
            try:
                confidences.append(float(event.get("confidence", 0.0)))
            except (TypeError, ValueError):
                continue

        summary = {
            "count": len(events),
            "components": components,
            "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
        }
        LOGGER.info("Analytics summary: %s", json.dumps(summary))
        return summary



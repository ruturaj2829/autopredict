"""Manufacturing insights agent to close the production feedback loop."""

from __future__ import annotations

import json
import logging
from typing import Dict

LOGGER = logging.getLogger("manufacturing_insights_agent")


class ManufacturingInsightsAgent:
	"""Publishes structured insights for manufacturing and quality teams."""

	def publish(self, event: Dict[str, object], emphasize_monitoring: bool = False) -> None:
		payload = self._build_payload(event)
		payload["monitoring_mode"] = emphasize_monitoring
		LOGGER.info("Manufacturing insight event: %s", json.dumps(payload))

	def log(self, event: Dict[str, object]) -> None:
		payload = self._build_payload(event)
		LOGGER.debug("Low-risk event recorded for manufacturing review: %s", json.dumps(payload))

	def _build_payload(self, event: Dict[str, object]) -> Dict[str, object]:
		context = event.get("context", {}) if isinstance(event.get("context"), dict) else {}
		return {
			"vehicle_id": event.get("vehicle_id"),
			"component": event.get("affected_component", "General"),
			"failure_risk": event.get("risk_level"),
			"lead_time_days": event.get("estimated_days_to_failure"),
			"dtc": context.get("dtc", []),
			"usage_pattern": context.get("usage_pattern"),
			"confidence": event.get("confidence"),
		}

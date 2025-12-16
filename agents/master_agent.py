"""Decision router that orchestrates worker agents using risk events."""

from __future__ import annotations

import logging
from typing import Any, Dict

from agents.worker_agents.scheduling_agent import SchedulingAgent
from agents.worker_agents.voice_agent import CustomerEngagementAgent
from agents.worker_agents.feedback_agent import ManufacturingInsightsAgent

LOGGER = logging.getLogger("master_agent")


class MasterAgent:
	"""Routes canonical predictive risk events to specialized worker agents."""

	def __init__(
		self,
		scheduler: SchedulingAgent,
		customer_agent: CustomerEngagementAgent,
		manufacturing_agent: ManufacturingInsightsAgent,
	) -> None:
		self.scheduler = scheduler
		self.customer_agent = customer_agent
		self.manufacturing_agent = manufacturing_agent

	def handle_risk_event(self, event: Dict[str, Any]) -> None:
		self._validate_event(event)
		risk_level = str(event["risk_level"]).upper()
		LOGGER.info("Received risk signal for %s | level=%s", event["vehicle_id"], risk_level)

		days_to_failure = int(event.get("estimated_days_to_failure", 0))
		if risk_level == "HIGH":
			self.customer_agent.send_urgent_message(event)
			self.scheduler.schedule_priority_visit(event["vehicle_id"], risk_level, days_to_failure)
			self.manufacturing_agent.publish(event)
		elif risk_level == "MEDIUM":
			self.customer_agent.send_preventive_message(event)
			self.scheduler.schedule_standard_visit(event["vehicle_id"], risk_level, days_to_failure)
			self.manufacturing_agent.publish(event, emphasize_monitoring=True)
		else:
			LOGGER.info("Risk level LOW for %s | monitoring only", event["vehicle_id"])
			self.manufacturing_agent.log(event)

	def _validate_event(self, event: Dict[str, Any]) -> None:
		required = {
			"event_type",
			"vehicle_id",
			"risk_level",
			"rf_fault_prob",
			"lstm_degradation_score",
			"estimated_days_to_failure",
			"timestamp",
		}
		missing = required - event.keys()
		if missing:
			raise ValueError(f"Risk event missing required fields: {sorted(missing)}")
		if event["event_type"] != "PREDICTIVE_RISK_SIGNAL":
			raise ValueError(f"Unsupported event type: {event['event_type']}")


def build_master_agent() -> MasterAgent:
	scheduler = SchedulingAgent()
	customer = CustomerEngagementAgent()
	manufacturing = ManufacturingInsightsAgent()
	return MasterAgent(scheduler, customer, manufacturing)


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
	agent = build_master_agent()
	sample_event = {
		"event_type": "PREDICTIVE_RISK_SIGNAL",
		"vehicle_id": "VEH-000",
		"risk_level": "HIGH",
		"rf_fault_prob": 0.8,
		"lstm_degradation_score": 0.85,
		"estimated_days_to_failure": 5,
		"timestamp": "2025-12-13T12:00:00Z",
		"affected_component": "Brakes",
		"confidence": 0.83,
		"context": {
			"usage_pattern": "city",
			"dtc": ["P0300"],
		},
	}
	agent.handle_risk_event(sample_event)

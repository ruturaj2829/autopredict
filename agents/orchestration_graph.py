"""LangGraph-based orchestration for master + worker agents with a Safety Twin.

This module is demo-focused: it builds a graph that:

- Takes a predictive risk event from the hybrid model as input state.
- Runs the primary ``MasterAgent`` to generate side effects (logs, scheduling, voice).
- In parallel, runs a "Safety Twin" master agent that can propose an alternative decision.
- Emits a comparison artifact showing whether the Safety Twin would escalate differently.

The graph is intentionally simple so judges can easily follow the flow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, TypedDict

from langgraph.graph import END, StateGraph

from agents.master_agent import MasterAgent, build_master_agent
from agents.worker_agents.scheduling_agent import SchedulingAgent
from agents.worker_agents.voice_agent import CustomerEngagementAgent
from agents.worker_agents.feedback_agent import ManufacturingInsightsAgent

LOGGER = logging.getLogger("agents.orchestration_graph")


class OrchestrationState(TypedDict):
    event: Dict[str, Any]
    primary_decision: Dict[str, Any]
    safety_decision: Dict[str, Any]
    divergence: Dict[str, Any]


def _build_safety_twin() -> MasterAgent:
    """Safety twin with slightly more conservative behavior for HIGH/MEDIUM."""
    scheduler = SchedulingAgent()
    customer = CustomerEngagementAgent()
    manufacturing = ManufacturingInsightsAgent()
    return MasterAgent(scheduler=scheduler, customer_agent=customer, manufacturing_agent=manufacturing)


def node_primary(state: OrchestrationState) -> OrchestrationState:
    master = build_master_agent()
    event = state["event"]
    LOGGER.info("[Primary] Handling risk event for %s", event.get("vehicle_id"))
    master.handle_risk_event(event)
    state["primary_decision"] = {
        "risk_level": event.get("risk_level"),
        "urgency": event.get("urgency"),
        "days_to_failure": event.get("estimated_days_to_failure"),
    }
    return state


def node_safety_twin(state: OrchestrationState) -> OrchestrationState:
    twin = _build_safety_twin()
    event = dict(state["event"])

    # Example conservative tweak: bump MEDIUM → HIGH if time-to-failure is very short.
    try:
        days = int(event.get("estimated_days_to_failure", 0))
    except (TypeError, ValueError):
        days = 0
    original_level = str(event.get("risk_level", "LOW")).upper()
    adjusted_level = original_level
    if original_level == "MEDIUM" and days <= 7:
        adjusted_level = "HIGH"
        event["risk_level"] = "HIGH"

    LOGGER.info(
        "[SafetyTwin] Handling risk event for %s (orig=%s adjusted=%s)",
        event.get("vehicle_id"),
        original_level,
        adjusted_level,
    )
    twin.handle_risk_event(event)
    state["safety_decision"] = {
        "risk_level": adjusted_level,
        "urgency": event.get("urgency"),
        "days_to_failure": event.get("estimated_days_to_failure"),
    }
    return state


def node_compare(state: OrchestrationState) -> OrchestrationState:
    primary = state.get("primary_decision") or {}
    safety = state.get("safety_decision") or {}
    divergence = {
        "changed": primary != safety,
        "primary": primary,
        "safety": safety,
    }
    LOGGER.info(
        "[Compare] divergence=%s | primary=%s | safety=%s",
        divergence["changed"],
        primary,
        safety,
    )
    state["divergence"] = divergence
    return state


def build_orchestration_graph():
    """Return a compiled LangGraph that runs primary + safety twin + comparison."""
    graph = StateGraph(OrchestrationState)
    graph.add_node("primary", node_primary)
    graph.add_node("safety_twin", node_safety_twin)
    graph.add_node("compare", node_compare)

    graph.set_entry_point("primary")
    graph.add_edge("primary", "safety_twin")
    graph.add_edge("safety_twin", "compare")
    graph.add_edge("compare", END)
    return graph.compile()


if __name__ == "__main__":
    # Small CLI demo so you can show the flow without wiring a full UI.
    import json

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    demo_event: Dict[str, Any] = {
        "event_type": "PREDICTIVE_RISK_SIGNAL",
        "vehicle_id": "DEMO-VEH-001",
        "risk_level": "MEDIUM",
        "rf_fault_prob": 0.6,
        "lstm_degradation_score": 0.7,
        "estimated_days_to_failure": 5,
        "timestamp": "2025-12-15T12:00:00Z",
        "urgency": 0.7,
    }
    graph = build_orchestration_graph()
    final_state = graph.invoke({"event": demo_event})
    print(json.dumps(final_state["divergence"], indent=2))



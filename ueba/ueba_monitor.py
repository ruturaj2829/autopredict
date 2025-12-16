"""UEBA monitoring helpers for intent deviation and replay simulation.

This module does not run a service itself; instead, it provides utilities that
can be called from notebooks, scripts, or dashboards to:

- Track sequences of UEBA events for each agent / subject.
- Detect basic intent deviation (unexpected operations for a given subject).
- Produce a replay-friendly timeline for audit and demo purposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List

from .engine import UEBAEvent


@dataclass
class IntentViolation:
    subject_id: str
    operation: str
    reason: str
    timestamp: str


class UEBAMonitor:
    """Lightweight in-memory monitor for UEBA events and replay."""

    def __init__(self, allowed_intents: Dict[str, List[str]] | None = None) -> None:
        # Map subject → allowed operations
        self.allowed_intents: Dict[str, List[str]] = allowed_intents or {}
        self._events: List[UEBAEvent] = []
        self._violations: List[IntentViolation] = []

    def record_events(self, events: Iterable[UEBAEvent]) -> None:
        for event in events:
            self._events.append(event)
            self._check_intent(event)

    def _check_intent(self, event: UEBAEvent) -> None:
        allowed = self.allowed_intents.get(event.subject_id)
        operation = event.context.get("operation") or (event.intent_path[0] if event.intent_path else "unknown")
        if allowed is not None and operation not in allowed:
            violation = IntentViolation(
                subject_id=event.subject_id,
                operation=operation,
                reason="Intent deviation: operation not in allowed set",
                timestamp=event.timestamp,
            )
            self._violations.append(violation)

    def violations(self) -> List[IntentViolation]:
        return list(self._violations)

    def timeline(self) -> List[Dict[str, object]]:
        """Return a replay-friendly event timeline for UI / demo."""
        return [
            {
                "timestamp": event.timestamp,
                "subject_id": event.subject_id,
                "risk_level": event.risk_level,
                "anomaly_score": event.anomaly_score,
                "intent_path": event.intent_path,
                "context": event.context,
            }
            for event in sorted(self._events, key=lambda e: datetime.fromisoformat(e.timestamp))
        ]



"""UEBA-powered guard layer for blocking risky agent operations.

This is intentionally lightweight and demo-focused:

- Wraps calls from agents (e.g., SchedulingAgent) to critical APIs.
- Uses UEBA anomaly score + intent metadata to decide ALLOW vs BLOCK.
- Produces a structured decision object that can be shown in the UI / logs.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from .engine import BehaviorRecord, UEBAEngine


@dataclass
class GuardDecision:
    allowed: bool
    reason: str
    anomaly_score: Optional[float] = None
    risk_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UEBAGuard:
    """Simple wrapper around UEBAEngine used as a policy guard."""

    def __init__(self, engine: UEBAEngine, subject_id: str, allowed_operations: Optional[list[str]] = None) -> None:
        self.engine = engine
        self.subject_id = subject_id
        self.allowed_operations = set(allowed_operations or [])

    def evaluate(self, operation: str, features: Dict[str, float], metadata: Optional[Dict[str, str]] = None) -> GuardDecision:
        """Return a GuardDecision without invoking the protected action."""
        now = datetime.now(timezone.utc)
        record = BehaviorRecord(
            timestamp=now,
            subject_id=self.subject_id,
            operation=operation,
            features=features,
            metadata=metadata or {},
        )

        # If UEBA has no baseline yet, treat the first calls as benign training data.
        if not self.engine._fitted:  # type: ignore[attr-defined]
            self.engine.partial_fit([record])
            return GuardDecision(allowed=True, reason="Baseline training – UEBA not yet active")

        event = self.engine.score(record)

        # Basic allowed-intents rule
        if self.allowed_operations and operation not in self.allowed_operations:
            return GuardDecision(
                allowed=False,
                reason=f"Operation '{operation}' not in allowed set for subject '{self.subject_id}'",
                anomaly_score=event.anomaly_score,
                risk_level=event.risk_level,
            )

        # Anomaly-based blocking
        if event.risk_level == "HIGH":
            return GuardDecision(
                allowed=False,
                reason="UEBA high-risk anomaly – call blocked",
                anomaly_score=event.anomaly_score,
                risk_level=event.risk_level,
            )

        return GuardDecision(
            allowed=True,
            reason="UEBA check passed",
            anomaly_score=event.anomaly_score,
            risk_level=event.risk_level,
        )

    def guard_call(
        self,
        operation: str,
        features: Dict[str, float],
        metadata: Optional[Dict[str, str]],
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Evaluate UEBA policy and conditionally execute ``func``."""
        decision = self.evaluate(operation, features, metadata)
        result: Dict[str, Any] = {"guard_decision": decision.to_dict()}

        if decision.allowed:
            func(*args, **kwargs)
        return result



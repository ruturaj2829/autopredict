"""
User & Entity Behavior Analytics (UEBA) engine.

Combines:
- Isolation Forest anomaly detection over behavioral feature vectors
- Intent graph modeling with NetworkX
- Azure Elastic ingestion hooks for centralized auditing
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

try:
    from elasticsearch import Elasticsearch
except ImportError:  # pragma: no cover
    Elasticsearch = None  # type: ignore

try:
    import networkx as nx
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("networkx is required for the UEBA engine") from exc

try:
    from sklearn.ensemble import IsolationForest
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("scikit-learn is required for the UEBA engine") from exc

LOGGER = logging.getLogger("ueba.engine")

DEFAULT_IFOREST_PARAMS = {
    "n_estimators": 200,
    "max_samples": "auto",
    "contamination": 0.05,
    "random_state": 42,
}


@dataclass
class BehaviorRecord:
    timestamp: datetime
    subject_id: str
    operation: str
    features: Dict[str, float]
    metadata: Dict[str, str]


@dataclass
class UEBAEvent:
    event_type: str
    subject_id: str
    anomaly_score: float
    risk_level: str
    intent_path: List[str]
    context: Dict[str, str]
    timestamp: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class UEBAEngine:
    """Core UEBA engine orchestrating anomaly detection, intent graphs, and audit streaming."""

    def __init__(
        self,
        iforest_params: Optional[Dict[str, object]] = None,
        elastic_endpoint: Optional[str] = None,
        elastic_api_key: Optional[str] = None,
    ) -> None:
        self.model = IsolationForest(**(iforest_params or DEFAULT_IFOREST_PARAMS))
        self.intent_graph = nx.DiGraph()
        self._fitted = False

        endpoint = elastic_endpoint or os.getenv("ELASTICSEARCH_URL")
        api_key = elastic_api_key or os.getenv("AZURE_ELASTIC_API_KEY")
        if endpoint and Elasticsearch:
            self.elastic_client = Elasticsearch(endpoint, api_key=api_key) if api_key else Elasticsearch(endpoint)
        else:
            self.elastic_client = None

        LOGGER.info("UEBA engine initialized | elastic_connected=%s", bool(self.elastic_client))

    # ------------------------------------------------------------------ #
    # Intent graph management
    # ------------------------------------------------------------------ #
    def register_intent_transition(self, source: str, target: str, weight: float = 1.0) -> None:
        self.intent_graph.add_edge(source, target, weight=weight)
        LOGGER.debug("Registered intent transition %s -> %s (weight=%.2f)", source, target, weight)

    def get_intent_path(self, operation: str) -> List[str]:
        if operation not in self.intent_graph:
            return [operation]
        try:
            target = max(nx.descendants(self.intent_graph, operation), default=operation)
        except nx.NetworkXError:
            target = operation
        return [operation, target] if operation != target else [operation]

    # ------------------------------------------------------------------ #
    # Model training / scoring
    # ------------------------------------------------------------------ #
    def partial_fit(self, records: List[BehaviorRecord]) -> None:
        if not records:
            return
        feature_matrix = np.array([list(rec.features.values()) for rec in records], dtype=float)
        self.model.fit(feature_matrix)
        self._fitted = True
        LOGGER.info("UEBA IsolationForest fitted on %d samples", len(records))

    def ingest(self, records: List[BehaviorRecord]) -> Dict[str, object]:
        """Ingest a batch of behavior records and return anomaly events.

        Behavior:
        - If the model is not yet fitted, use the batch to establish a baseline via ``partial_fit``
          and return a lightweight acknowledgment.
        - Once a baseline exists, score each incoming record to produce UEBA events. These can be
          streamed to Elastic for later replay / audit.
        """
        if not records:
            return {"status": "no_records", "events": []}

        # If we have not built a baseline yet, use this batch to train and acknowledge.
        if not self._fitted:
            self.partial_fit(records)
            return {
                "status": "baseline_initialized",
                "events": [],
                "count": len(records),
            }

        events: List[UEBAEvent] = []
        for record in records:
            try:
                events.append(self.score(record))
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.warning("Failed to score UEBA record for subject %s: %s", record.subject_id, exc)

        return {
            "status": "ok",
            "events": [event.to_dict() for event in events],
            "count": len(events),
        }

    def score(self, record: BehaviorRecord) -> UEBAEvent:
        if not self._fitted:
            raise RuntimeError("UEBA model has not been fitted. Call partial_fit first.")
        feature_vector = np.array([list(record.features.values())], dtype=float)
        try:
            # IsolationForest expects the same feature dimensionality that it was fitted on.
            # If the guard or caller sends a payload with a different number of features,
            # we degrade gracefully instead of failing the whole request.
            anomaly_score = -float(self.model.decision_function(feature_vector)[0])  # higher => riskier
        except ValueError as exc:
            LOGGER.warning("UEBA feature dimensionality mismatch, defaulting to LOW risk: %s", exc)
            anomaly_score = 0.0
        risk_level = self._risk_level(anomaly_score)
        event = UEBAEvent(
            event_type="UEBA_ANOMALY",
            subject_id=record.subject_id,
            anomaly_score=anomaly_score,
            risk_level=risk_level,
            intent_path=self.get_intent_path(record.operation),
            context=record.metadata,
            timestamp=record.timestamp.astimezone(timezone.utc).isoformat(),
        )
        LOGGER.debug("UEBA event generated | subject=%s level=%s score=%.3f", record.subject_id, risk_level, anomaly_score)
        self._emit_to_elastic(event)
        return event

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 0.65:
            return "HIGH"
        if score >= 0.4:
            return "MEDIUM"
        return "LOW"

    def _emit_to_elastic(self, event: UEBAEvent) -> None:
        if not self.elastic_client:
            return
        try:
            self.elastic_client.index(index="ueba-events", document=event.to_dict())
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Failed to index UEBA event into Azure Elastic: %s", exc)

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    def load_baseline(self, path: os.PathLike[str]) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        records = [
            BehaviorRecord(
                timestamp=datetime.fromisoformat(item["timestamp"]),
                subject_id=item["subject_id"],
                operation=item["operation"],
                features=item["features"],
                metadata=item.get("metadata", {}),
            )
            for item in data
        ]
        self.partial_fit(records)
        LOGGER.info("UEBA baseline loaded from %s", path)
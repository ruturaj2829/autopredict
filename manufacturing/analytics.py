from __future__ import annotations
# filepath: c:\Users\Acer\AutoPredict\manufacturing\analytics.py
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import json
import logging

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.cluster import KMeans


LOGGER = logging.getLogger("manufacturing.analytics")


@dataclass
class ManufacturingEvent:
    vehicle_id: str
    component: str
    failure_risk: str
    lead_time_days: float
    dtc: List[str]
    usage_pattern: str
    timestamp: str


class ManufacturingAnalytics:
    def __init__(self, clusters: int = 4) -> None:
        self.default_clusters = clusters
        self.cluster_model = KMeans(n_clusters=clusters, n_init="auto", random_state=42)

    def fit_clusters(self, events: Iterable[ManufacturingEvent]) -> pd.DataFrame:
        df = pd.DataFrame([event.__dict__ for event in events])
        if df.empty:
            raise ValueError("No manufacturing events provided")
        embeddings = self._create_embeddings(df)
        # Ensure we never request more clusters than we have samples; this can
        # happen in demo flows where a small synthetic batch is used.
        n_samples = embeddings.shape[0]
        n_clusters = min(self.default_clusters, n_samples)
        if n_clusters <= 0:
            raise ValueError("No samples available for clustering")
        if n_clusters != self.cluster_model.n_clusters:
            self.cluster_model = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
        self.cluster_model.fit(embeddings)
        df["cluster"] = self.cluster_model.labels_
        LOGGER.info("Manufacturing events clustered into %d segments", self.cluster_model.n_clusters)
        return df

    def plot_heatmap(self, df: pd.DataFrame, output_html: Optional[Path] = None) -> Path:
        pivot = (
            df.groupby(["component", "failure_risk"])
            .agg(count=("vehicle_id", "count"), lead_time=("lead_time_days", "mean"))
            .reset_index()
        )
        fig = px.density_heatmap(
            pivot,
            x="component",
            y="failure_risk",
            z="count",
            color_continuous_scale="Magma",
            title="Manufacturing Defect Heatmap",
        )
        path = output_html or Path("manufacturing_heatmap.html")
        fig.write_html(path)
        LOGGER.info("Manufacturing heatmap exported to %s", path)
        return path

    def export_to_azure_data_explorer(self, df: pd.DataFrame, table: str = "ManufacturingInsights") -> Dict[str, object]:
        payload = {"table": table, "records": df.to_dict(orient="records")}
        LOGGER.debug("Prepared payload for Azure Data Explorer | rows=%d table=%s", len(df), table)
        return payload

    @staticmethod
    def _create_embeddings(df: pd.DataFrame) -> np.ndarray:
        component_codes = {comp: idx for idx, comp in enumerate(sorted(df["component"].unique()))}
        risk_codes = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        return np.column_stack(
            [
                df["lead_time_days"].to_numpy(dtype=float),
                df["usage_pattern"].map({"city": 0, "highway": 1, "mixed": 2}).to_numpy(dtype=float),
                df["failure_risk"].map(risk_codes).to_numpy(dtype=float),
                df["component"].map(component_codes).to_numpy(dtype=float),
            ]
        )

    def save_cluster_summary(self, df: pd.DataFrame, path: Path) -> None:
        summary = (
            df.groupby("cluster")
            .agg(
                vehicles=("vehicle_id", "nunique"),
                avg_lead_time=("lead_time_days", "mean"),
                top_component=("component", lambda s: s.value_counts().idxmax()),
            )
            .reset_index()
        )
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(summary.to_dict(orient="records"), handle, indent=2)
        LOGGER.info("Cluster summary saved to %s", path)

    def generate_capa_recommendations(self, df: pd.DataFrame) -> List[Dict[str, object]]:
        """Generate simple RCA/CAPA-style recommendations per cluster.

        This is intentionally rule-based and demo-oriented. It looks at the dominant
        component and failure risk in each cluster and proposes a human-readable
        corrective / preventive action.
        """
        recommendations: List[Dict[str, object]] = []
        grouped = df.groupby("cluster")

        for cluster_id, group in grouped:
            top_component = group["component"].value_counts().idxmax()
            risk_mode = group["failure_risk"].value_counts().idxmax()
            vehicles = group["vehicle_id"].nunique()

            if top_component.lower() == "brakes":
                action = "Initiate supplier inspection for brake calipers and review pad material spec."
            elif top_component.lower() in {"engine", "powertrain"}:
                action = "Deep-dive into powertrain calibration and cooling design; consider design review."
            elif top_component.lower() in {"battery"}:
                action = "Audit battery supplier batches and charging system diagnostics."
            else:
                action = "Open cross-functional quality review for this component family."

            if risk_mode == "HIGH":
                priority = "Immediate design / supplier action"
            elif risk_mode == "MEDIUM":
                priority = "Planned design improvement and monitoring"
            else:
                priority = "Monitor trend; no urgent CAPA required"

            recommendations.append(
                {
                    "cluster": int(cluster_id),
                    "vehicles": int(vehicles),
                    "top_component": top_component,
                    "dominant_risk": risk_mode,
                    "recommended_action": action,
                    "priority": priority,
                }
            )

        return recommendations
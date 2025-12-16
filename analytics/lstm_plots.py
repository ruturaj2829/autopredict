"""
Visualization helpers for LSTM degradation forecasts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import plotly.graph_objects as go


def plot_trend(
    sequences: Iterable[List[float]],
    predictions: Iterable[float],
    output_path: Optional[Path] = None,
    title: str = "LSTM Degradation Trend",
) -> Path:
    seq_array = np.array(list(sequences))
    preds = np.array(list(predictions))
    timesteps = list(range(seq_array.shape[1]))

    fig = go.Figure()
    for idx, sequence in enumerate(seq_array):
        fig.add_trace(go.Scatter(x=timesteps, y=sequence, mode="lines", name=f"Sequence {idx+1}"))
    fig.add_trace(go.Scatter(x=list(range(len(preds))), y=preds, mode="lines+markers", name="LSTM prediction", line=dict(color="firebrick")))
    fig.update_layout(title=title, xaxis_title="Timestep", yaxis_title="Feature magnitude")

    path = output_path or Path("lstm_trend.html")
    fig.write_html(path)
    return path
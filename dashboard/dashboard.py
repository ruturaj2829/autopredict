"""Simple web dashboard for digital twin monitoring and risk scores.

This is intentionally lightweight: it reads the streaming feature file produced by
``simulation/telemetry_consumer.py`` and exposes:

- ``GET /api/vehicles``: latest summarized state per vehicle.
- ``GET /``: minimal HTML dashboard that polls the API every few seconds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "telemetry_features.jsonl"

app = FastAPI(title="Vehicle Digital Twin Dashboard", version="1.0.0")


def _load_latest_states(max_lines: int = 1000) -> Dict[str, Dict[str, Any]]:
    if not DATA_PATH.exists():
        return {}

    latest: Dict[str, Dict[str, Any]] = {}

    # Read from the end of the file to keep it efficient for demos.
    lines: List[str] = DATA_PATH.read_text(encoding="utf-8").splitlines()[-max_lines:]
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        vehicle_id = str(payload.get("vehicle_id", "")).strip()
        if not vehicle_id:
            continue
        latest[vehicle_id] = payload
    return latest


@app.get("/api/vehicles")
def list_vehicles() -> JSONResponse:
    """Return latest telemetry-derived state and heuristic risk scores for each vehicle."""
    state = _load_latest_states()
    vehicles: List[Dict[str, Any]] = []
    for vid, payload in state.items():
        rf = payload.get("rf_features", {})
        # Heuristic multi-dimensional scores (0–1) derived from RF features.
        brake_risk = float(rf.get("brake_wear_current", 0.0)) / 100.0
        temp_risk = max(float(rf.get("engine_temp_mean", 0.0)) - 95.0, 0.0) / 30.0
        dtc_risk = float(rf.get("dtc_count", 0.0)) / 5.0
        critical = float(rf.get("critical_dtc_present", 0.0))
        immediate_risk = min(brake_risk * 0.5 + temp_risk * 0.3 + (dtc_risk + critical) * 0.2, 1.0)
        warranty_risk = min((brake_risk + dtc_risk + critical) / 3.0, 1.0)
        recurring_defect = min(dtc_risk + 0.2 * critical, 1.0)
        retention_risk = min(immediate_risk * 0.5 + warranty_risk * 0.5, 1.0)
        vehicles.append(
            {
                "vehicle_id": vid,
                "timestamp": payload.get("timestamp"),
                "engine_temp_mean": rf.get("engine_temp_mean"),
                "battery_voltage_min": rf.get("battery_voltage_min"),
                "brake_wear_current": rf.get("brake_wear_current"),
                "tire_pressure_mean_dev": rf.get("tire_pressure_mean_dev"),
                "irs": immediate_risk,
                "wrs": warranty_risk,
                "rds": recurring_defect,
                "crs": retention_risk,
            }
        )
    return JSONResponse({"vehicles": vehicles})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Minimal HTML dashboard with auto-refreshing vehicle table."""
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Vehicle Digital Twin</title>
    <style>
      body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; background: #050816; color: #e5e7eb; }
      h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
      .subtitle { color: #9ca3af; margin-bottom: 1.5rem; }
      table { border-collapse: collapse; width: 100%; background: #020617; border-radius: 0.75rem; overflow: hidden; }
      th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #1f2937; font-size: 0.9rem; }
      th { background: #111827; color: #9ca3af; font-weight: 500; }
      tr:nth-child(even) { background: #020617; }
      tr:nth-child(odd) { background: #020617; }
      .risk-high { color: #f97373; }
      .risk-medium { color: #facc15; }
      .risk-low { color: #22c55e; }
    </style>
  </head>
  <body>
    <h1>Vehicle Digital Twin</h1>
    <div class="subtitle">Live engine, battery, brakes, tire telemetry, and multi-dimensional risk scores.</div>
    <p class="subtitle"><a href="/manufacturing" style="color:#38bdf8;">View manufacturing defect heatmap ↗</a></p>
    <table>
      <thead>
        <tr>
          <th>Vehicle</th>
          <th>Timestamp</th>
          <th>Engine Temp (mean)</th>
          <th>Battery Voltage (min)</th>
          <th>Brake Wear (%)</th>
          <th>Tire Pressure Δ</th>
          <th>IRS</th>
          <th>WRS</th>
          <th>RDS</th>
          <th>CRS</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
    <script>
      async function refresh() {
        try {
          const res = await fetch('/api/vehicles');
          const data = await res.json();
          const tbody = document.getElementById('tbody');
          tbody.innerHTML = '';
          for (const v of data.vehicles) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td>${v.vehicle_id}</td>
              <td>${v.timestamp ?? ''}</td>
              <td>${v.engine_temp_mean?.toFixed ? v.engine_temp_mean.toFixed(1) : ''}</td>
              <td>${v.battery_voltage_min?.toFixed ? v.battery_voltage_min.toFixed(2) : ''}</td>
              <td>${v.brake_wear_current?.toFixed ? v.brake_wear_current.toFixed(1) : ''}</td>
              <td>${v.tire_pressure_mean_dev?.toFixed ? v.tire_pressure_mean_dev.toFixed(2) : ''}</td>
              <td>${v.irs?.toFixed ? v.irs.toFixed(2) : ''}</td>
              <td>${v.wrs?.toFixed ? v.wrs.toFixed(2) : ''}</td>
              <td>${v.rds?.toFixed ? v.rds.toFixed(2) : ''}</td>
              <td>${v.crs?.toFixed ? v.crs.toFixed(2) : ''}</td>
            `;
            tbody.appendChild(tr);
          }
        } catch (err) {
          console.error('Failed to refresh vehicles', err);
        }
      }
      refresh();
      setInterval(refresh, 4000);
    </script>
  </body>
</html>
"""


@app.get("/manufacturing", response_class=HTMLResponse)
def manufacturing_heatmap() -> str:
    """Serve the latest manufacturing defect heatmap, if available."""
    heatmap_path = Path("manufacturing_heatmap.html")
    if not heatmap_path.exists():
        return "<html><body><h2>No manufacturing heatmap has been generated yet.</h2></body></html>"
    return heatmap_path.read_text(encoding="utf-8")



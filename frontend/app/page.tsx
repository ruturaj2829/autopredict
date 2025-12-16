"use client";

import { useState } from "react";

const BACKEND_URL =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080"
    : "http://localhost:8080";

type Json = unknown;

function JsonBlock({ label, value }: { label: string; value: Json }) {
  return (
    <div className="response-box">
      <div className="json-label">{label}</div>
      <pre className="code-block monospace">
        {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

export default function HomePage() {
  const [riskResponse, setRiskResponse] = useState<Json>("// Click “Run live call” to fetch from /api/v1/telemetry/risk");
  const [orchestrationResponse, setOrchestrationResponse] = useState<Json>("// First run risk scoring above, then click “Use last event in orchestration”");
  const [lastRiskEvent, setLastRiskEvent] = useState<Json | null>(null);
  const [schedulerResponse, setSchedulerResponse] = useState<Json>("// Try an optimization call to see UEBA guard decisions");
  const [manufacturingResponse, setManufacturingResponse] = useState<Json>("// Trigger manufacturing analytics to see clusters + CAPA");

  // Static sample payload so that server-rendered and client-rendered HTML match
  // (using Date.now() here would cause React hydration warnings). This schema
  // mirrors the one used by tests/hybrid_stack_smoke_test.py so that it aligns
  // with the trained RF + LSTM artifacts.
  const baseRiskPayload = {
    vehicle_id: "DEMO-VEH-001",
    timestamp: "<ISO-8601 timestamp>", // e.g. 2025-12-15T19:01:12Z
    rf_features: {
      engine_temp_mean: 107.5,
      engine_temp_max: 114.2,
      engine_temp_std: 3.1,
      engine_temp_rate_per_min: 4.6,
      battery_voltage_mean: 12.4,
      battery_voltage_min: 11.9,
      battery_voltage_drop_per_min: 0.15,
      brake_wear_current: 82.0,
      brake_wear_rate_per_min: 0.8,
      tire_pressure_mean_dev: -1.3,
      dtc_count: 2,
      critical_dtc_present: 1,
      usage_city: 1,
      usage_highway: 0,
      usage_mixed: 0,
      hour_of_day: 12,
      day_of_week: 1,
      window_size: 12,
      window_span_minutes: 10.0
    },
    lstm_sequence: [
      [103.5, 12.8, 68.0, 31.5, 0.0, 1.0, 0.0, 0.0],
      [105.2, 12.4, 70.0, 31.0, 0.0, 1.0, 0.0, 0.0],
      [108.7, 12.1, 72.5, 30.6, 1.0, 1.0, 0.0, 0.0],
      [110.9, 12.0, 75.1, 30.4, 1.0, 1.0, 0.0, 0.0],
      [112.6, 11.9, 78.0, 30.1, 1.0, 1.0, 0.0, 0.0],
      [113.8, 11.8, 80.5, 29.9, 1.0, 1.0, 0.0, 0.0],
      [114.2, 11.9, 82.0, 29.7, 1.0, 1.0, 0.0, 0.0],
      [112.9, 12.0, 83.5, 29.8, 1.0, 1.0, 0.0, 0.0],
      [111.2, 12.1, 84.0, 30.0, 1.0, 1.0, 0.0, 0.0],
      [110.6, 12.2, 84.5, 30.2, 1.0, 1.0, 0.0, 0.0],
      [109.1, 12.3, 85.0, 30.4, 1.0, 1.0, 0.0, 0.0],
      [108.4, 12.4, 85.2, 30.5, 1.0, 1.0, 0.0, 0.0]
    ],
    latest_reading: {
      timestamp: "<ISO-8601 timestamp>",
      engine_temp: 114.2,
      battery_voltage: 11.9,
      brake_wear: 82.0,
      tire_pressure: 29.7,
      dtc: ["P0300", "P0420"],
      usage_pattern: "city"
    }
  };

  async function runRisk() {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/telemetry/risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(baseRiskPayload)
      });
      const data = await res.json();
      setRiskResponse(data);
      if (res.ok) {
        setLastRiskEvent(data);
      }
    } catch (err) {
      setRiskResponse({ error: String(err) });
    }
  }

  async function runOrchestration() {
    if (!lastRiskEvent) {
      setOrchestrationResponse("// No risk event available yet. Run the hybrid risk scoring section first.");
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/orchestration/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastRiskEvent)
      });
      const data = await res.json();
      setOrchestrationResponse(data);
    } catch (err) {
      setOrchestrationResponse({ error: String(err) });
    }
  }

  async function runScheduler() {
    const now = new Date();
    const payload = {
      jobs: [
        {
          vehicle_id: "DEMO-VEH-001",
          risk_level: "HIGH",
          location: "Mumbai, IN",
          preferred_by: new Date(now.getTime() + 2 * 24 * 3600 * 1000).toISOString(),
          duration_minutes: 90,
          days_to_failure: 5
        }
      ],
      slots: [
        {
          technician_id: "tech-01",
          location: "Mumbai, IN",
          start_time: new Date(now.getTime() + 1 * 24 * 3600 * 1000).toISOString(),
          capacity_minutes: 180
        }
      ]
    };
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/scheduler/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setSchedulerResponse(data);
    } catch (err) {
      setSchedulerResponse({ error: String(err) });
    }
  }

  async function runManufacturing() {
    const nowIso = new Date().toISOString();
    const payload = [
      {
        vehicle_id: "VEH-101",
        component: "Brakes",
        failure_risk: "HIGH",
        lead_time_days: 5,
        dtc: ["P0300"],
        usage_pattern: "city",
        timestamp: nowIso
      },
      {
        vehicle_id: "VEH-102",
        component: "Engine",
        failure_risk: "MEDIUM",
        lead_time_days: 7,
        dtc: ["P0420"],
        usage_pattern: "mixed",
        timestamp: nowIso
      }
    ];
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/manufacturing/analytics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setManufacturingResponse(data);
    } catch (err) {
      setManufacturingResponse({ error: String(err) });
    }
  }

  return (
    <div>
      <header className="mb-6">
        <div className="pill-row">
          <span className="badge badge-pill-strong">Prototype</span>
          <span className="badge badge-pill">LangGraph</span>
          <span className="badge badge-pill">Hybrid RF + LSTM</span>
          <span className="badge badge-pill">UEBA Guard</span>
          <span className="badge badge-pill">Voice AI</span>
          <span className="badge badge-pill">RCA / CAPA</span>
        </div>
        <h1 className="text-3xl font-semibold mb-1">AutoPredict – Judge-Friendly Frontend</h1>
        <p className="section-subtitle">
          This single page explains what each backend feature does, shows example JSON payloads, and lets you
          trigger real calls against the FastAPI backend. Set <code className="monospace">NEXT_PUBLIC_BACKEND_URL</code>{" "}
          if your backend is not on <code className="monospace">http://localhost:8080</code>.
        </p>
        <p className="small">
          Tip: keep the FastAPI docs open at <code className="monospace">{BACKEND_URL}/docs</code> while you explore this
          page.
        </p>
      </header>

      {/* 1. Digital Twin & Hybrid Risk */}
      <section>
        <h2 className="section-title">1. Continuous Monitoring + Hybrid RF + LSTM Risk</h2>
        <p className="section-subtitle">
          The backend consumes time-series telemetry, builds RF features + LSTM sequences, and returns a canonical{" "}
          <code className="monospace">PREDICTIVE_RISK_SIGNAL</code> event.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>1A. Example telemetry feature payload (request)</h3>
            <p className="small">
              You can tweak this JSON and replay it via curl/Postman or the button below. Rolling features and
              sequences are simplified here for readability.
            </p>
            <JsonBlock label="POST /api/v1/telemetry/risk – sample request" value={baseRiskPayload} />
            <button className="btn btn-primary mt-3" onClick={runRisk}>
              Run live call against /api/v1/telemetry/risk
            </button>
          </div>

          <div className="card">
            <h3>1B. Hybrid RF + LSTM risk event (response)</h3>
            <p className="small">
              Fields like <code className="monospace">rf_fault_prob</code>,{" "}
              <code className="monospace">lstm_degradation_score</code>,{" "}
              <code className="monospace">estimated_days_to_failure</code>, and{" "}
              <code className="monospace">failure_probability_next_7_days</code> are what drive the agents.
            </p>
            <JsonBlock label="Hybrid inference response" value={riskResponse} />
          </div>
        </div>

        <p className="small mt-2">
          Try this: change <code className="monospace">brake_wear_current</code> or{" "}
          <code className="monospace">engine_temp_mean</code> in the request (via a manual curl) and see how risk level
          and days-to-failure respond.
        </p>
      </section>

      {/* 2. LangGraph Orchestration + Safety Twin */}
      <section>
        <h2 className="section-title">2. LangGraph Orchestration + Shadow “Safety Twin”</h2>
        <p className="section-subtitle">
          We feed the risk event into a LangGraph that runs the primary MasterAgent and a Safety Twin in sequence, then
          compares their decisions.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>2A. Orchestration input JSON</h3>
            <p className="small">
              Input is the exact event produced by Section 1. For convenience, this UI reuses the last successful
              response from <code className="monospace">/api/v1/telemetry/risk</code>.
            </p>
            <JsonBlock
              label="POST /api/v1/orchestration/run – sample request"
              value={
                lastRiskEvent || "// Run the hybrid risk section first; the last event will be shown here automatically."
              }
            />
            <button className="btn btn-primary mt-3" onClick={runOrchestration}>
              Use last risk event in orchestration graph
            </button>
          </div>

          <div className="card">
            <h3>2B. Primary vs Safety Twin decisions (response)</h3>
            <p className="small">
              The response includes <code className="monospace">primary_decision</code>,{" "}
              <code className="monospace">safety_decision</code>, and a{" "}
              <code className="monospace">divergence.changed</code> flag that is perfect for governance slides.
            </p>
            <JsonBlock label="Orchestration comparison" value={orchestrationResponse} />
          </div>
        </div>
      </section>

      {/* 3. UEBA Guard + Scheduler Optimization */}
      <section>
        <h2 className="section-title">3. UEBA Guard + Multi-Objective Scheduler</h2>
        <p className="section-subtitle">
          The scheduling endpoint wraps the OR-Tools optimizer in a UEBA guard. If UEBA flags a high-risk anomaly or
          intent deviation, the optimization is blocked with a 403.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>3A. Schedule optimization request</h3>
            <p className="small">
              This JSON defines one HIGH-risk job and a single technician slot. You can add more jobs/slots and replay
              via curl to stress the guard.
            </p>
            <JsonBlock
              label="POST /api/v1/scheduler/optimize – sample request"
              value={{
                jobs: [
                  {
                    vehicle_id: "DEMO-VEH-001",
                    risk_level: "HIGH",
                    location: "Mumbai, IN",
                    preferred_by: "<ISO-8601 timestamp>",
                    duration_minutes: 90,
                    days_to_failure: 5
                  }
                ],
                slots: [
                  {
                    technician_id: "tech-01",
                    location: "Mumbai, IN",
                    start_time: "<ISO-8601 timestamp>",
                    capacity_minutes: 180
                  }
                ]
              }}
            />
            <button className="btn btn-primary mt-3" onClick={runScheduler}>
              Run optimization + UEBA guard
            </button>
          </div>

          <div className="card">
            <h3>3B. Schedule + UEBA decision (response)</h3>
            <p className="small">
              The response combines <code className="monospace">schedule</code> (technician assignments) and{" "}
              <code className="monospace">ueba_guard</code> (decision, reason, anomaly score, risk level).
            </p>
            <JsonBlock label="Optimizer + guard response" value={schedulerResponse} />
          </div>
        </div>
      </section>

      {/* 4. Voice AI + Customer Engagement */}
      <section>
        <h2 className="section-title">4. Voice AI – Persuasive, Mood-Adaptive Messaging</h2>
        <p className="section-subtitle">
          The <code className="monospace">CustomerEngagementAgent</code> uses Azure TTS to turn risk events into
          persuasive scripts. This frontend doesn&apos;t stream audio, but it shows you the exact message templates and
          how to plug them into a call workflow.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>4A. Example urgent script</h3>
            <p className="small">
              This is an example of the text we synthesize for a HIGH risk brake failure within ~10 days.
            </p>
            <JsonBlock
              label="Urgent engagement example"
              value={
                "Hello. This is your vehicle care assistant. Our system detected HIGH risk for the brakes on vehicle DEMO-VEH-001. It could impact safety within 10 days. Booking a preventive service now could save significant repair costs and avoid roadside breakdowns."
              }
            />
            <p className="small mt-2">
              Try this: wire this text into your call center / IVR system, or drive it from a button in your CRM UI.
            </p>
          </div>

          <div className="card">
            <h3>4B. Roadside emergency variant</h3>
            <p className="small">
              For a critical event (<code className="monospace">estimated_days_to_failure ≈ 0–1</code>), the same
              template can be adapted to a &quot;please stop driving&quot; script.
            </p>
            <JsonBlock
              label="Roadside emergency message"
              value={
                "URGENT: Please safely pull over. Your vehicle shows an imminent risk that could lead to roadside breakdown. We are booking roadside assistance and sharing live vehicle data with the support team."
              }
            />
          </div>
        </div>
      </section>

      {/* 5. Manufacturing RCA / CAPA */}
      <section>
        <h2 className="section-title">5. Manufacturing RCA / CAPA Insights</h2>
        <p className="section-subtitle">
          The manufacturing analytics pipeline clusters failure events, renders a heatmap, and generates rule-based CAPA
          recommendations per cluster.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>5A. Failure events (request)</h3>
            <p className="small">
              In a full deployment, these come from the Manufacturing Insights Agent and service records. Here we use a
              small synthetic batch.
            </p>
            <JsonBlock
              label="POST /api/v1/manufacturing/analytics – sample request"
              value={[
                {
                  vehicle_id: "VEH-101",
                  component: "Brakes",
                  failure_risk: "HIGH",
                  lead_time_days: 5,
                  dtc: ["P0300"],
                  usage_pattern: "city",
                  timestamp: "<ISO-8601>"
                },
                {
                  vehicle_id: "VEH-102",
                  component: "Engine",
                  failure_risk: "MEDIUM",
                  lead_time_days: 7,
                  dtc: ["P0420"],
                  usage_pattern: "mixed",
                  timestamp: "<ISO-8601>"
                }
              ]}
            />
            <button className="btn btn-primary mt-3" onClick={runManufacturing}>
              Run clustering + heatmap + CAPA
            </button>
          </div>

          <div className="card">
            <h3>5B. Clusters, heatmap, and CAPA (response)</h3>
            <p className="small">
              Response includes raw clusters, an HTML heatmap path, an export payload, and{" "}
              <code className="monospace">capa_recommendations</code>.
            </p>
            <JsonBlock label="Manufacturing analytics response" value={manufacturingResponse} />
            <p className="small mt-2">
              Visualization: open the heatmap view at <code className="monospace">/manufacturing</code> (served by the
              dashboard service) to show failure frequency by component and risk.
            </p>
          </div>
        </div>
      </section>

      {/* 6. Where to go next */}
      <section>
        <h2 className="section-title">6. How to run this prototype</h2>
        <p className="section-subtitle">
          This is a build-ready Next.js app. You can run it locally for the demo or containerize it alongside the
          backend.
        </p>
        <div className="card">
          <h3>Local commands</h3>
          <pre className="code-block monospace">
{`cd frontend
npm install
set NEXT_PUBLIC_BACKEND_URL=http://localhost:8080  # Windows PowerShell
npm run dev  # or: npm run build && npm start`}
          </pre>
          <p className="small mt-2">
            For Docker, you can copy the <code className="monospace">frontend</code> folder into an existing Node image,
            run <code className="monospace">npm install && npm run build</code>, and expose port 3000.
          </p>
        </div>
      </section>
    </div>
  );
}



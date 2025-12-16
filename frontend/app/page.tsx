"use client";

import { useState, useEffect } from "react";
import VoiceTour from "./components/VoiceTour";
import RiskCharts from "./components/RiskCharts";
import UEBAVisualization from "./components/UEBAVisualization";

// Get backend URL from environment variable
const RAILWAY_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://autopredict-production.up.railway.app";
const BACKEND_URL = RAILWAY_BACKEND_URL.replace(/\/+$/, "");

if (typeof window !== "undefined") {
  console.log("🔗 Backend URL:", BACKEND_URL);
  console.log("🔍 Environment variable:", process.env.NEXT_PUBLIC_BACKEND_URL);
}

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

function LoadingSpinner() {
  return (
    <div className="loading-spinner">
      <div className="spinner"></div>
      <span>Processing...</span>
    </div>
  );
}

export default function HomePage() {
  const [riskResponse, setRiskResponse] = useState<Json>("// Click 'Run live call' to fetch from /api/v1/telemetry/risk");
  const [orchestrationResponse, setOrchestrationResponse] = useState<Json>("// First run risk scoring above, then click 'Use last event in orchestration'");
  const [lastRiskEvent, setLastRiskEvent] = useState<Json | null>(null);
  const [schedulerResponse, setSchedulerResponse] = useState<Json>("// Try an optimization call to see UEBA guard decisions");
  const [manufacturingResponse, setManufacturingResponse] = useState<Json>("// Trigger manufacturing analytics to see clusters + CAPA");
  const [uebaResponse, setUebaResponse] = useState<Json>("// Run UEBA ingest to see behavior analysis");
  const [uebaEvents, setUebaEvents] = useState<any[]>([]);

  // Loading states
  const [loadingRisk, setLoadingRisk] = useState(false);
  const [loadingOrchestration, setLoadingOrchestration] = useState(false);
  const [loadingScheduler, setLoadingScheduler] = useState(false);
  const [loadingManufacturing, setLoadingManufacturing] = useState(false);
  const [loadingUeba, setLoadingUeba] = useState(false);

  // Static sample payload
  const baseRiskPayload = {
    vehicle_id: "DEMO-VEH-001",
    timestamp: new Date().toISOString(),
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
      timestamp: new Date().toISOString(),
      engine_temp: 114.2,
      battery_voltage: 11.9,
      brake_wear: 82.0,
      tire_pressure: 29.7,
      dtc: ["P0300", "P0420"],
      usage_pattern: "city"
    }
  };

  async function runRisk() {
    setLoadingRisk(true);
    try {
      const payload = { ...baseRiskPayload, timestamp: new Date().toISOString() };
      const res = await fetch(`${BACKEND_URL}/api/v1/telemetry/risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setRiskResponse(data);
      if (res.ok) {
        setLastRiskEvent(data);
        // Auto-trigger orchestration if risk event is available
        setTimeout(() => {
          if (data && typeof data === "object" && "event_type" in data) {
            runOrchestrationAuto(data);
          }
        }, 500);
      }
    } catch (err) {
      setRiskResponse({ error: String(err) });
    } finally {
      setLoadingRisk(false);
    }
  }

  async function runOrchestrationAuto(eventData?: any) {
    const eventToUse = eventData || lastRiskEvent;
    if (!eventToUse) {
      setOrchestrationResponse("// No risk event available yet. Run the hybrid risk scoring section first.");
      return;
    }
    setLoadingOrchestration(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/orchestration/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(eventToUse)
      });
      const data = await res.json();
      setOrchestrationResponse(data);
    } catch (err) {
      setOrchestrationResponse({ error: String(err) });
    } finally {
      setLoadingOrchestration(false);
    }
  }

  async function runOrchestration() {
    await runOrchestrationAuto();
  }

  async function runScheduler() {
    setLoadingScheduler(true);
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
    } finally {
      setLoadingScheduler(false);
    }
  }

  async function runManufacturing() {
    setLoadingManufacturing(true);
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
    } finally {
      setLoadingManufacturing(false);
    }
  }

  async function runUeba() {
    setLoadingUeba(true);
    const now = new Date();
    const payload = [
      {
        timestamp: now.toISOString(),
        subject_id: "technician-01",
        operation: "optimize",
        features: {
          jobs: 5.0,
          slots: 3.0,
          high_risk_jobs: 2.0,
        },
        metadata: { ip: "192.168.1.10", session_id: "session-001" },
      },
      {
        timestamp: new Date(now.getTime() + 1000).toISOString(),
        subject_id: "technician-02",
        operation: "optimize",
        features: {
          jobs: 10.0,
          slots: 2.0,
          high_risk_jobs: 8.0,
        },
        metadata: { ip: "192.168.1.11", session_id: "session-002" },
      },
      {
        timestamp: new Date(now.getTime() + 2000).toISOString(),
        subject_id: "scheduling-agent",
        operation: "optimize",
        features: {
          jobs: 15.0,
          slots: 5.0,
          high_risk_jobs: 12.0,
        },
        metadata: { ip: "192.168.1.12", session_id: "session-003" },
      },
    ];
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/ueba/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setUebaResponse(data);
      // Extract events from response
      if (data && data.events && Array.isArray(data.events)) {
        setUebaEvents(data.events);
      } else if (data && Array.isArray(data)) {
        setUebaEvents(data);
      } else if (data && data.status === "baseline_initialized") {
        // First call initializes baseline, create demo events for visualization
        setUebaEvents([
          {
            event_type: "UEBA_ANOMALY",
            subject_id: "technician-01",
            anomaly_score: 0.45,
            risk_level: "MEDIUM",
            intent_path: ["optimize"],
            context: { ip: "192.168.1.10" },
            timestamp: new Date().toISOString(),
          },
          {
            event_type: "UEBA_ANOMALY",
            subject_id: "technician-02",
            anomaly_score: 0.72,
            risk_level: "HIGH",
            intent_path: ["optimize"],
            context: { ip: "192.168.1.11" },
            timestamp: new Date(Date.now() + 1000).toISOString(),
          },
        ]);
      }
    } catch (err) {
      setUebaResponse({ error: String(err) });
    } finally {
      setLoadingUeba(false);
    }
  }

  return (
    <div>
      <VoiceTour />
      
      <header className="mb-6">
        <div className="pill-row">
          <span className="badge badge-pill-strong">Prototype</span>
          <span className="badge badge-pill">LangGraph</span>
          <span className="badge badge-pill">Hybrid RF + LSTM</span>
          <span className="badge badge-pill">UEBA Guard</span>
          <span className="badge badge-pill">Voice AI</span>
          <span className="badge badge-pill">RCA / CAPA</span>
        </div>
        <h1 className="text-3xl font-semibold mb-1">AutoPredict – Agentic AI Platform</h1>
        <p className="section-subtitle">
          Interactive demo showcasing hybrid machine learning, multi-agent orchestration, UEBA security, and real-time analytics.
          Click the voice tour button to get started!
        </p>
      </header>

      {/* 1. Digital Twin & Hybrid Risk */}
      <section id="section-risk">
        <h2 className="section-title">1. Continuous Monitoring + Hybrid RF + LSTM Risk</h2>
        <p className="section-subtitle">
          The backend consumes time-series telemetry, builds RF features + LSTM sequences, and returns a canonical{" "}
          <code className="monospace">PREDICTIVE_RISK_SIGNAL</code> event.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>1A. Example telemetry feature payload (request)</h3>
            <p className="small">
              You can tweak this JSON and replay it via curl/Postman or the button below.
            </p>
            <JsonBlock label="POST /api/v1/telemetry/risk – sample request" value={baseRiskPayload} />
            <button 
              className="btn btn-primary mt-3" 
              onClick={runRisk}
              disabled={loadingRisk}
            >
              {loadingRisk ? <LoadingSpinner /> : "Run live call against /api/v1/telemetry/risk"}
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
            {loadingRisk ? (
              <LoadingSpinner />
            ) : (
              <>
                <JsonBlock label="Hybrid inference response" value={riskResponse} />
                {riskResponse && typeof riskResponse === "object" && "risk_level" in riskResponse && (
                  <div style={{ marginTop: "1rem" }}>
                    <RiskCharts data={riskResponse as any} />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      {/* 2. LangGraph Orchestration + Safety Twin */}
      <section id="section-orchestration">
        <h2 className="section-title">2. LangGraph Orchestration + Shadow "Safety Twin"</h2>
        <p className="section-subtitle">
          We feed the risk event into a LangGraph that runs the primary MasterAgent and a Safety Twin in sequence, then
          compares their decisions. <strong>Orchestration runs automatically after risk scoring!</strong>
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
            <button 
              className="btn btn-primary mt-3" 
              onClick={runOrchestration}
              disabled={loadingOrchestration || !lastRiskEvent}
            >
              {loadingOrchestration ? <LoadingSpinner /> : "Use last risk event in orchestration graph"}
            </button>
          </div>

          <div className="card">
            <h3>2B. Primary vs Safety Twin decisions (response)</h3>
            <p className="small">
              The response includes <code className="monospace">primary_decision</code>,{" "}
              <code className="monospace">safety_decision</code>, and a{" "}
              <code className="monospace">divergence.changed</code> flag that is perfect for governance slides.
            </p>
            {loadingOrchestration ? (
              <LoadingSpinner />
            ) : (
              <JsonBlock label="Orchestration comparison" value={orchestrationResponse} />
            )}
          </div>
        </div>
      </section>

      {/* 3. UEBA Guard */}
      <section id="section-ueba">
        <h2 className="section-title">3. UEBA (User & Entity Behavior Analytics) Security Guard</h2>
        <p className="section-subtitle">
          UEBA monitors agent actions for anomalies and intent deviations, blocking risky operations. This prevents malicious or erroneous agent behavior.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>3A. UEBA ingest request</h3>
            <p className="small">
              Send behavior records to the UEBA engine. It analyzes patterns, detects anomalies, and tracks intent paths.
            </p>
            <JsonBlock
              label="POST /api/v1/ueba/ingest – sample request"
              value={[
                {
                  timestamp: "<ISO-8601>",
                  subject_id: "technician-01",
                  operation: "optimize",
                  features: { jobs: 5.0, slots: 3.0, high_risk_jobs: 2.0 },
                  metadata: { ip: "192.168.1.10" },
                }
              ]}
            />
            <button 
              className="btn btn-primary mt-3" 
              onClick={runUeba}
              disabled={loadingUeba}
            >
              {loadingUeba ? <LoadingSpinner /> : "Run UEBA ingest + visualization"}
            </button>
          </div>

          <div className="card">
            <h3>3B. UEBA events (response)</h3>
            <p className="small">
              The response includes anomaly scores, risk levels, intent paths, and context for each behavior record.
            </p>
            {loadingUeba ? (
              <LoadingSpinner />
            ) : (
              <JsonBlock label="UEBA ingest response" value={uebaResponse} />
            )}
          </div>
        </div>

        {uebaEvents.length > 0 && (
          <div style={{ marginTop: "1.5rem" }}>
            <h3 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>UEBA Visualization</h3>
            <UEBAVisualization events={uebaEvents} />
          </div>
        )}
      </section>

      {/* 4. UEBA Guard + Scheduler Optimization */}
      <section id="section-scheduler">
        <h2 className="section-title">4. UEBA Guard + Multi-Objective Scheduler</h2>
        <p className="section-subtitle">
          The scheduling endpoint wraps the OR-Tools optimizer in a UEBA guard. If UEBA flags a high-risk anomaly or
          intent deviation, the optimization is blocked with a 403.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>4A. Schedule optimization request</h3>
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
            <button 
              className="btn btn-primary mt-3" 
              onClick={runScheduler}
              disabled={loadingScheduler}
            >
              {loadingScheduler ? <LoadingSpinner /> : "Run optimization + UEBA guard"}
            </button>
          </div>

          <div className="card">
            <h3>4B. Schedule + UEBA decision (response)</h3>
            <p className="small">
              The response combines <code className="monospace">schedule</code> (technician assignments) and{" "}
              <code className="monospace">ueba_guard</code> (decision, reason, anomaly score, risk level).
            </p>
            {loadingScheduler ? (
              <LoadingSpinner />
            ) : (
              <JsonBlock label="Optimizer + guard response" value={schedulerResponse} />
            )}
          </div>
        </div>
      </section>

      {/* 5. Voice AI + Customer Engagement */}
      <section>
        <h2 className="section-title">5. Voice AI – Persuasive, Mood-Adaptive Messaging</h2>
        <p className="section-subtitle">
          The <code className="monospace">CustomerEngagementAgent</code> uses Azure TTS to turn risk events into
          persuasive scripts. This frontend doesn&apos;t stream audio, but it shows you the exact message templates and
          how to plug them into a call workflow.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>5A. Example urgent script</h3>
            <p className="small">
              This is an example of the text we synthesize for a HIGH risk brake failure within ~10 days.
            </p>
            <JsonBlock
              label="Urgent engagement example"
              value={
                "Hello. This is your vehicle care assistant. Our system detected HIGH risk for the brakes on vehicle DEMO-VEH-001. It could impact safety within 10 days. Booking a preventive service now could save significant repair costs and avoid roadside breakdowns."
              }
            />
          </div>

          <div className="card">
            <h3>5B. Roadside emergency variant</h3>
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

      {/* 6. Manufacturing RCA / CAPA */}
      <section id="section-manufacturing">
        <h2 className="section-title">6. Manufacturing RCA / CAPA Insights</h2>
        <p className="section-subtitle">
          The manufacturing analytics pipeline clusters failure events, renders a heatmap, and generates rule-based CAPA
          recommendations per cluster.
        </p>

        <div className="grid grid-2">
          <div className="card">
            <h3>6A. Failure events (request)</h3>
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
            <button 
              className="btn btn-primary mt-3" 
              onClick={runManufacturing}
              disabled={loadingManufacturing}
            >
              {loadingManufacturing ? <LoadingSpinner /> : "Run clustering + heatmap + CAPA"}
            </button>
          </div>

          <div className="card">
            <h3>6B. Clusters, heatmap, and CAPA (response)</h3>
            <p className="small">
              Response includes raw clusters, an HTML heatmap path, an export payload, and{" "}
              <code className="monospace">capa_recommendations</code>.
            </p>
            {loadingManufacturing ? (
              <LoadingSpinner />
            ) : (
              <JsonBlock label="Manufacturing analytics response" value={manufacturingResponse} />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

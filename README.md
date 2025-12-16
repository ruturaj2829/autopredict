## AutoPredict – Agentic Predictive Maintenance Prototype

AutoPredict is a **judge-ready prototype** for an AI-driven predictive maintenance and quality intelligence platform.  
It demonstrates:

- **Hybrid RF + LSTM failure prediction** (time-to-failure, multi-horizon probabilities)
- **Agentic orchestration** (LangGraph master + worker agents)
- **Shadow “Safety Twin” agent** for decision comparison
- **UEBA guard** that can block risky agent actions
- **Voice AI** hooks (Azure TTS + sentiment)
- **Manufacturing RCA / CAPA analytics** with defect heatmaps
- **Digital twin dashboard** and a **Next.js judge UI**

This README is your **0 → 100 guide**: running, testing, demo script, how to impress judges, and deployment pointers.

---

## 1. Repository Layout (High Level)

- `backend/app.py` – FastAPI app (core APIs)
- `models/hybrid_inference_service.py` – Hybrid RF + LSTM inference
- `agents/master_agent.py` – Master agent routing risk events to workers
- `agents/orchestration_graph.py` – LangGraph orchestration + Safety Twin
- `agents/worker_agents/` – Worker agents:
  - `scheduling_agent.py` – maintenance booking logic
  - `voice_agent.py` – customer engagement + Azure TTS
  - `feedback_agent.py` – manufacturing feedback events
  - `data_analysis_agent.py`, `diagnosis_agent.py` – analytics and hypotheses
- `ueba/engine.py` – UEBA engine (IsolationForest + intent graph)
- `ueba/guard.py` – UEBA guard for blocking agent calls
- `manufacturing/analytics.py` – clustering, heatmap, RCA/CAPA
- `simulation/` – telemetry simulator + feature builder
- `dashboard/dashboard.py` – lightweight FastAPI dashboard
- `tests/` – smoke tests and connectivity checks
- `frontend/` – **Next.js frontend** (App Router) with explanation + live calls

---

## 2. One-Time Setup

### 2.1. Prerequisites

- Windows 10/11 (or any OS) with:
  - **Python 3.11**
  - **Node.js 20+**
  - **Git**
  - Optional: Docker Desktop (for container deployment)

### 2.2. Clone and Python Environment

```bash
git clone <your-repo-url> AutoPredict
cd AutoPredict

python -m venv venv
venv\Scripts\activate   # Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3. Environment Variables (`.env`)

Create a `.env` file in the repo root (do **not** commit this file):

```bash
# Azure Speech (required for voice flows)
AZURE_SPEECH_KEY=<your-azure-speech-key>
AZURE_SPEECH_REGION=eastus

# Azure SQL (optional – used by tests, not critical for demo)
AZURE_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=tcp:autopredictsql.database.windows.net,1433;Database=autopredictSql;Uid=sqladmin;Pwd=Ruturaj28&;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;

# Azure PostgreSQL (optional – used by tests)
AZURE_POSTGRES_DSN=postgresql://autopredict:Ruturaj28%26@autopredictpostresql.postgres.database.azure.com:5432/postgres?sslmode=require

# TimescaleDB (optional – can be left unset)
TIMESCALE_DSN=<timescale-dsn-if-available>

# Local services
ELASTICSEARCH_URL=http://localhost:9200
BACKEND_URL=http://localhost:8080

TIMESTAMP_BUCKET=telemetry
ENV=development
```

> For the hackathon prototype, the backend and frontend do **not** require Azure SQL or PostgreSQL to be reachable.  
> The main flows (hybrid model, orchestration, UEBA guard, manufacturing analytics) work fully offline.

---

## 3. Running the Prototype Locally

### 3.1. Start the backend (FastAPI)

```bash
cd C:\Users\Acer\AutoPredict
venv\Scripts\activate

uvicorn backend.app:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080/docs` – you should see the FastAPI docs.

Key endpoints:

- `POST /api/v1/telemetry/risk` – hybrid RF + LSTM risk scoring
- `POST /api/v1/orchestration/run` – LangGraph master + Safety Twin comparison
- `POST /api/v1/scheduler/optimize` – OR-Tools scheduler + UEBA guard
- `POST /api/v1/manufacturing/analytics` – clustering, heatmap, CAPA
- `POST /api/v1/ueba/ingest` – UEBA ingest endpoint

### 3.2. Start the Next.js frontend (judge UI)

```bash
cd frontend
npm install

# Point frontend to backend
set NEXT_PUBLIC_BACKEND_URL=http://localhost:8080   # PowerShell / CMD

npm run dev
```

Open `http://localhost:3000`.

The homepage:

- Explains each feature in plain English.
- Shows **sample JSON** for each endpoint.
- Provides buttons to run live calls against the backend.

### 3.3. (Optional) Telemetry stream + dashboard

1. **Telemetry simulator** – fake telematics on WebSocket:

   ```bash
   venv\Scripts\python.exe simulation\telemetry_simulator.py
   ```

2. **Telemetry consumer** – builds RF + LSTM-ready features:

   ```bash
   venv\Scripts\python.exe simulation\telemetry_consumer.py
   ```

3. **Dashboard service**:

   ```bash
   venv\Scripts\python.exe -m uvicorn dashboard.dashboard:app --host 0.0.0.0 --port 8090
   ```

   - `http://localhost:8090` → Digital twin + IRS/WRS/RDS/CRS per vehicle  
   - `http://localhost:8090/manufacturing` → manufacturing heatmap (after running analytics)

---

## 4. Demo Script (What to Show Judges)

All of this happens from the **Next.js UI** at `http://localhost:3000`.

### 4.1. Hybrid RF + LSTM Risk (Section 1)

- Run the button **“Run live call against /api/v1/telemetry/risk”**.
- Show the JSON:
  - `rf_fault_prob`
  - `lstm_degradation_score`
  - `ensemble_risk_score`
  - `estimated_days_to_failure`
  - `failure_probability_next_7_days`, `next_30_days`
  - `affected_component`, `confidence`, `urgency`

Explain: **RF** gives explainable feature importance, **LSTM** captures temporal degradation; fusion layer produces risk + TTF.

### 4.2. LangGraph Orchestration + Safety Twin (Section 2)

- Click **“Use last risk event in orchestration graph”**.
- Show the JSON:

```json
{
  "primary_decision": { "risk_level": "MEDIUM", "urgency": 0.7, "days_to_failure": 8 },
  "safety_decision": { "risk_level": "HIGH", "urgency": 0.7, "days_to_failure": 8 },
  "divergence": {
    "changed": true,
    "primary": { ... },
    "safety": { ... }
  }
}
```

Explain: **Safety Twin** is more conservative (escalates when TTF is short), and `divergence.changed` is the governance signal.

### 4.3. UEBA Guard + Scheduler (Section 3)

- Click **“Run optimization + UEBA guard”**.
- Show:
  - `schedule` – technician assignment for the vehicle.
  - `ueba_guard` – UEBA decision, reason, anomaly score, risk level.

Explain: every optimization goes through **UEBA guard**; it can block the call (`allowed=false`, HTTP 403) if risk or intent is suspicious.

### 4.4. Voice AI (Section 4)

- Show the **urgent** and **roadside emergency** scripts.
- Explain:
  - `AzureVoiceService` turns these scripts into audio via Azure TTS.
  - Sentiment detection (TextBlob) can adjust tone / prefix.

You can say: “In production this is connected to our call center / IVR; for the hackathon we focus on safe orchestration + scripts.”

### 4.5. Manufacturing RCA / CAPA (Section 5)

- Click **“Run clustering + heatmap + CAPA”**.
- Show JSON with:
  - `clusters` – per-vehicle cluster labels
  - `heatmap` – path to `manufacturing_heatmap.html`
  - `capa_recommendations` – human-readable actions with priorities

Then, in a browser tab, open `http://localhost:8090/manufacturing` (if dashboard is running) to show the **defect heatmap**.

---

## 5. Tests and Health Checks

### 5.1. Hybrid stack smoke test

```bash
venv\Scripts\python.exe tests\hybrid_stack_smoke_test.py --verbose
```

Verifies:

- Hybrid inference artifacts load correctly.
- Returned risk event has all expected fields.
- Event routes through `MasterAgent` without errors.

### 5.2. Service connectivity tests

```bash
venv\Scripts\python.exe tests\service_connectivity_tests.py
```

Outputs JSON for:

- UEBA ingest
- Scheduler optimize
- TimescaleDB
- Azure PostgreSQL
- Azure SQL Database
- Azure Speech Service

For the prototype, it is acceptable if the DB checks fail (due to firewall / driver), as long as:

- UEBA ingest → `PASS`
- Azure Speech Service → `PASS`

### 5.3. Full health check

```bash
venv\Scripts\python.exe tests\system_health_check.py
```

Writes `tests/system_health_report.json` with PASS/FAIL and timing for each subsystem.

---

## 6. Demo Playbook – How to Impress (What to Show vs. Skip)

This section is specifically for the **live demo** – what to emphasize, what to keep in the background, and how to answer questions.

### 6.1. 7–10 minute demo structure

1. **Open the Next.js UI (`http://localhost:3000`)**  
   - One sentence: “This page is a cockpit for the AI maintenance brain – every box is a real API behind the scenes.”

2. **Hybrid Risk (Section 1) – 2 minutes**
   - Click “Run live call” and highlight:
     - RF + LSTM combination.
     - `estimated_days_to_failure` and 7/30-day probabilities.
   - Talking line: “We don’t just say ‘high risk’; we say *what* is about to fail, *when*, and with what confidence.”

3. **LangGraph + Safety Twin (Section 2) – 2 minutes**
   - Run orchestration, show `primary_decision` vs `safety_decision` and `divergence.changed`.
   - Talking line: “The Safety Twin is a parallel agent that challenges the primary decision. Any divergence becomes a governance signal for critical flows.”

4. **UEBA Guard + Scheduler (Section 3) – 2 minutes**
   - Run optimization, show `schedule` and `ueba_guard`.
   - Talking line: “Even if someone tries to abuse the scheduler, UEBA can block the API before data is touched; this is agent safety, not just RBAC.”

5. **Voice AI + RCA/CAPA (Sections 4 & 5) – 3–4 minutes**
   - Show urgent and roadside scripts; mention Azure TTS is plugged in.
   - Run manufacturing analytics, show CAPA JSON and then the heatmap UI at `/manufacturing`.
   - Talking line: “We close the loop by turning field failures into manufacturing actions – supplier audits, design fixes, etc.”

If you have more time, switch briefly to the **digital twin dashboard** at `http://localhost:8090` to show live engine/battery/brake/tire telemetry and the multi-risk scores.

### 6.2. What to highlight as “innovation”

- **Agentic orchestration with a Safety Twin**
  - Emphasize that you explicitly model:
    - A **primary path** (MasterAgent routing to workers).
    - A **safety path** (more conservative thresholds).
  - Mention that divergence is auditable via the orchestration endpoint.

- **UEBA guard as a first-class citizen**
  - It’s not just logging anomalies; it **sits in front of the scheduler** and can block optimization.
  - Show `ueba_guard` JSON and explain how one could attach replay / visualization for blocked calls.

- **Hybrid model design**
  - RF → explainable features (temperatures, brake wear, DTCs).
  - LSTM → temporal degradation.
  - Fusion → multi-horizon risk, days-to-failure.

- **RCA/CAPA integration**
  - The system doesn’t stop at a maintenance booking; it constructs manufacturing insights and recommendations.
  - Show how CAPA recommendations mention “supplier inspection”, “design review”, etc.

### 6.3. What to keep light / skip if time is short

- **Deep DB connectivity (Azure SQL / Azure PostgreSQL)**
  - You can truthfully say:
    - “The code is wired to support Azure SQL/PostgreSQL, but for the prototype we run fully local to avoid network delays.”
  - No need to demo direct DB queries.

- **Low-level infra (Timescale, Elasticsearch, Grafana)**
  - Mention that telemetry can be stored in Timescale and logs in Elastic, but the judges don’t need to see connection strings.

- **Whisper STT internals**
  - It’s enough to mention: “We use Whisper for STT and Azure TTS for output; this demo focuses on the decision layer.”

### 6.4. Handling common judge questions

**Q: What happens if the model is wrong or drifts?**  
**A:** “We separate the model from the orchestration and governance. The Safety Twin and UEBA guard don’t care which model you use – they look at behavior and intent. You can retrain RF/LSTM without touching the safety layer.”

**Q: How is this different from a simple cron job that checks thresholds?**  
**A:** “Cron + thresholds can’t reason about temporal degradation, nor can it decide *how* to talk to the customer, schedule optimally, or feed RCA back to manufacturing. Here you see a coordinated set of agents, with governance, all triggered by a single predictive event.”

**Q: How would this scale to thousands of vehicles?**  
**A:** “The hybrid model is batched and can run on GPU; telemetry aggregation is streaming-based. The orchestration layer is stateless per event, so it can be scaled horizontally behind an API gateway.”

**Q: What about security / data governance?**  
**A:** “UEBA provides behavioral anomaly detection and intent checks on agents; the Safety Twin is an additional guardrail for under‑escalation. Data at rest can live in Azure SQL/Postgres/Timescale with standard RBAC and network isolation.”

**Q: How would you integrate this with an existing OEM system?**  
**A:** “Everything you see is behind clean APIs – telemetry in, risk event out, schedule in/out, manufacturing insights out. We designed it to sit alongside an existing dealer CRM or call center, not replace them.”

---

## 7. Docker and Deployment (High-Level)

### 6.1. Backend image

Dockerfile: `backend/Dockerfile`.

Build:

```bash
docker build -t autopredict-backend -f backend/Dockerfile .
```

Run locally:

```bash
docker run -p 8080:8080 --env-file .env autopredict-backend
```

### 6.2. docker-compose (optional)

`docker-compose.yml` can run:

- Backend
- Timescale
- PostgreSQL
- Elasticsearch
- Grafana

```bash
docker compose up --build
```

### 6.3. Frontend Docker (pattern)

If you want to containerize `frontend/`, add a Dockerfile there and:

```bash
cd frontend
docker build -t autopredict-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_BACKEND_URL=http://host.docker.internal:8080 autopredict-frontend
```

### 6.4. Azure deployment (suggested)

- Push images (`autopredict-backend`, `autopredict-frontend`) to **Azure Container Registry**.
- Deploy as **Azure Container Apps** or **Web App for Containers**.
- Configure environment variables (values from `.env`) in the Portal (not in Git).
- Optionally connect to Azure SQL / PostgreSQL / Speech using managed identities and VNet.

---

## 8. Wow Factors to Emphasize

- **Agentic orchestration** with explicit LangGraph graph and Safety Twin.
- **Hybrid RF + LSTM** – not just a single black-box model.
- **UEBA guard** with anomaly scores and intent monitoring for agent safety.
- **Voice AI** layer ready for call center or roadside workflows.
- **RCA/CAPA loop** that closes the feedback from field failures back to manufacturing.
- Clear, JSON-first **frontend** that lets judges “see and touch” every part of the system in a single page.




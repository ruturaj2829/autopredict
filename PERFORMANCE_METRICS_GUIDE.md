# Performance Metrics & Graphs Guide

## Where to Get Performance Graphs & Charts for AutoPredict AI Agent

This guide explains **where all performance metrics are located** and **how to access/create visualizations**.

---

## 📊 **1. Model Performance Metrics**

### **Location:**
- **File:** `artifacts/model_metadata.json`
- **API Endpoint:** `GET /api/v1/metrics/performance` (NEW - just added)

### **Available Metrics:**
- **Random Forest:**
  - Precision, Recall, F1 Score
  - Support (number of samples)
  - Classification report
- **LSTM:**
  - Precision, Recall, F1 Score
  - Support
  - Classification report
- **Lead Time Metrics:**
  - Average lead minutes (time before failure)
  - Detection rate
  - Evaluated failures count

### **How to Access:**

#### **Option A: Via API (Recommended)**
```bash
# From terminal
curl http://localhost:8080/api/v1/metrics/performance

# Or visit in browser:
http://localhost:8080/api/v1/metrics/performance
```

#### **Option B: Read JSON File Directly**
```bash
# View the file
cat artifacts/model_metadata.json

# Or in Python
import json
with open("artifacts/model_metadata.json", "r") as f:
    metrics = json.load(f)
    print(metrics["evaluation_summary"])
```

---

## 📈 **2. Frontend Performance Dashboard (NEW)**

### **Location:**
- **Component:** `frontend/app/components/PerformanceDashboard.tsx`
- **Page:** Add to your frontend at `/performance` or embed in existing page

### **What It Shows:**
- **KPI Cards:** RF F1 Score, LSTM F1 Score, Detection Rate, UEBA Events
- **Model Comparison Chart:** Bar chart comparing RF vs LSTM (Precision, Recall, F1)
- **F1 Score Distribution:** Pie chart showing model performance
- **Lead Time Metrics:** Bar chart for detection metrics
- **Performance Radar:** Radar chart showing overall performance
- **Detailed Metrics Table:** Full breakdown of all metrics

### **How to Use:**

1. **Add to your frontend page:**
```tsx
import PerformanceDashboard from "@/app/components/PerformanceDashboard";

// In your page component:
<PerformanceDashboard />
```

2. **Or create a dedicated route:**
   - Create `frontend/app/performance/page.tsx`
   - Import and render `<PerformanceDashboard />`

3. **Access at:**
   - `http://localhost:3000/performance` (if you create a route)

---

## 🔍 **3. UEBA Performance Metrics**

### **Location:**
- **Component:** `frontend/app/components/UEBAVisualization.tsx`
- **API:** `POST /api/v1/ueba/ingest` returns UEBA events

### **Available Visualizations:**
- **Anomaly Score Timeline:** Line chart showing anomaly scores over time
- **Risk Level Distribution:** Bar chart (LOW/MEDIUM/HIGH)
- **Anomaly Scores by Event:** Bar chart per event
- **Risk Profile Radar:** Radar chart for selected event
- **Intent Path Visualization:** Step-by-step intent flow
- **Event Details Panel:** Full metadata for selected event

### **How to Access:**
1. **Via Frontend:** Already integrated in your main page (`frontend/app/page.tsx`)
2. **Via API:** Call `/api/v1/ueba/ingest` to get events, then visualize

---

## 📉 **4. Risk Prediction Charts**

### **Location:**
- **Component:** `frontend/app/components/RiskCharts.tsx`
- **API:** `POST /api/v1/telemetry/risk` returns risk data

### **Available Charts:**
- **Model Probabilities:** Bar chart (RF Fault, LSTM Degradation, Ensemble Risk)
- **Failure Probability Over Time:** Line chart (30-day projection)
- **Risk Assessment:** Circular indicator with risk level
- **Failure Probability by Period:** Bar chart (7 days vs 30 days)

### **How to Access:**
- Already integrated in your main page
- Or call API directly: `POST /api/v1/telemetry/risk` with telemetry payload

---

## 🏭 **5. Manufacturing Analytics**

### **Location:**
- **API:** `POST /api/v1/manufacturing/analytics`
- **Output:** Heatmap path, cluster data, CAPA recommendations

### **Available Metrics:**
- **Defect Heatmap:** Component vs Batch visualization
- **Cluster Analysis:** KMeans clustering results
- **RCA/CAPA Suggestions:** Root cause and corrective actions

### **How to Access:**
```bash
# Call the API with manufacturing events
curl -X POST http://localhost:8080/api/v1/manufacturing/analytics \
  -H "Content-Type: application/json" \
  -d @manufacturing_events.json
```

---

## 🎯 **6. Agent Orchestration Metrics**

### **Location:**
- **API:** `POST /api/v1/orchestration/run`
- **Returns:** Primary decision, Safety Twin decision, divergence

### **Available Metrics:**
- **Agent Decision Comparison:** Primary vs Safety Twin
- **Divergence Detection:** When agents disagree
- **Agent Activity Logs:** Tracked in UEBA events

### **How to Access:**
- Call `/api/v1/orchestration/run` with a risk event
- Check UEBA visualization for agent behavior tracking

---

## 📱 **7. Real-Time Dashboard**

### **Location:**
- **Service:** `dashboard/dashboard.py`
- **URL:** `http://localhost:8090`

### **What It Shows:**
- **Vehicle States:** Latest telemetry per vehicle
- **Risk Scores:** IRS, WRS, RDS, CRS (multi-dimensional risk)
- **Real-time Updates:** Auto-refreshes every few seconds

### **How to Access:**
```bash
# Start the dashboard service
python -m uvicorn dashboard.dashboard:app --host 0.0.0.0 --port 8090

# Visit: http://localhost:8090
```

---

## 🛠️ **8. Creating Custom Performance Dashboards**

### **Step 1: Collect All Metrics**
```python
# Example Python script to aggregate metrics
import json
import requests

# Get model metrics
with open("artifacts/model_metadata.json", "r") as f:
    model_metrics = json.load(f)

# Get UEBA stats
ueba_response = requests.get("http://localhost:8080/api/v1/metrics/performance")
ueba_stats = ueba_response.json()["ueba_stats"]

# Combine and visualize
```

### **Step 2: Use Visualization Libraries**
- **Python:** Matplotlib, Plotly, Seaborn
- **JavaScript/React:** Recharts (already used), Chart.js, D3.js
- **Tools:** Grafana, Kibana (if you integrate Elasticsearch)

### **Step 3: Export to Reports**
- Generate PDF reports using libraries like `reportlab` or `weasyprint`
- Export to Excel/CSV for analysis
- Create automated dashboards in tools like Grafana

---

## 📋 **Quick Reference: All Metrics Endpoints**

| Metric Type | Endpoint | Method | Returns |
|------------|----------|--------|---------|
| **Model Performance** | `/api/v1/metrics/performance` | GET | RF/LSTM metrics, UEBA stats |
| **Risk Prediction** | `/api/v1/telemetry/risk` | POST | Risk scores, probabilities |
| **UEBA Events** | `/api/v1/ueba/ingest` | POST | Anomaly scores, risk levels |
| **Manufacturing** | `/api/v1/manufacturing/analytics` | POST | Clusters, heatmap, CAPA |
| **Orchestration** | `/api/v1/orchestration/run` | POST | Agent decisions, divergence |
| **Vehicle States** | `http://localhost:8090/api/vehicles` | GET | Real-time vehicle data |

---

## 🎨 **Visualization Examples**

### **Example 1: Model Performance Comparison**
```python
import matplotlib.pyplot as plt
import json

with open("artifacts/model_metadata.json", "r") as f:
    data = json.load(f)

rf_metrics = data["evaluation_summary"]["random_forest"]
lstm_metrics = data["evaluation_summary"]["lstm"]

metrics = ["Precision", "Recall", "F1 Score"]
rf_values = [rf_metrics["precision"], rf_metrics["recall"], rf_metrics["f1_score"]]
lstm_values = [lstm_metrics["precision"], lstm_metrics["recall"], lstm_metrics["f1_score"]]

x = range(len(metrics))
width = 0.35
plt.bar([i - width/2 for i in x], rf_values, width, label="RF")
plt.bar([i + width/2 for i in x], lstm_values, width, label="LSTM")
plt.xlabel("Metrics")
plt.ylabel("Score")
plt.title("Model Performance Comparison")
plt.xticks(x, metrics)
plt.legend()
plt.show()
```

### **Example 2: UEBA Risk Distribution**
- Already implemented in `UEBAVisualization.tsx`
- Shows risk level distribution as bar chart
- Access via frontend component

---

## 🚀 **Next Steps**

1. **Add Performance Dashboard to Frontend:**
   - Import `PerformanceDashboard` component
   - Add route or embed in existing page
   - Access at `/performance`

2. **Set Up Automated Monitoring:**
   - Schedule periodic API calls to `/api/v1/metrics/performance`
   - Store metrics in time-series DB
   - Create trend charts over time

3. **Integrate with Observability Tools:**
   - Export metrics to Prometheus/Grafana
   - Set up alerts for performance degradation
   - Create executive dashboards

---

## 📞 **Need Help?**

- **Model Metrics:** Check `artifacts/model_metadata.json`
- **API Issues:** Check `backend/app.py` endpoints
- **Frontend Charts:** See `frontend/app/components/` folder
- **Dashboard:** Run `dashboard/dashboard.py` service

All performance graphs are now accessible via:
1. **API:** `GET /api/v1/metrics/performance`
2. **Frontend Component:** `PerformanceDashboard.tsx`
3. **Existing Visualizations:** `RiskCharts.tsx`, `UEBAVisualization.tsx`


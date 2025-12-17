# Screenshot Verification Checklist

## ✅ **Screenshot 2: Risk Prediction with Charts** (Section 1)

### Required Elements:
- [x] **RF fault probability** - ✅ Implemented in `RiskCharts.tsx` (bar chart, "RF Fault")
- [x] **LSTM degradation score** - ✅ Implemented in `RiskCharts.tsx` (bar chart, "LSTM Degradation")
- [x] **Ensemble risk score** - ✅ Implemented in `RiskCharts.tsx` (bar chart, "Ensemble Risk")
- [x] **Time-to-failure estimate** - ✅ Implemented in `RiskCharts.tsx` (shown in Risk Assessment card)
- [x] **Visual charts**:
  - [x] Bar charts - ✅ "Model Probabilities" bar chart
  - [x] Line charts - ✅ "Failure Probability Over Time" line chart
  - [x] Risk indicators - ✅ Circular risk level indicator with color coding

### How to Capture:
1. Go to Section 1: "Continuous Monitoring + Hybrid RF + LSTM Risk"
2. Click "Run live call against /api/v1/telemetry/risk"
3. Wait for response
4. Scroll down to see **RiskCharts** component below the JSON response
5. **Screenshot should show:** 4 cards with charts (Model Probabilities bar chart, Failure Probability line chart, Risk Assessment circle, Failure Probability by Period bar chart)

---

## ✅ **Screenshot 3: UEBA Visualization** (Section 3)

### Required Elements:
- [x] **Anomaly score timeline** - ✅ Implemented in `UEBAVisualization.tsx` (LineChart)
- [x] **Risk level distribution (LOW/MEDIUM/HIGH)** - ✅ Implemented in `UEBAVisualization.tsx` (BarChart)
- [x] **Radar chart for risk profile** - ✅ Implemented in `UEBAVisualization.tsx` (RadarChart)
- [x] **Intent path visualization** - ✅ Implemented in `UEBAVisualization.tsx` (step-by-step display)

### Additional Features Visible:
- [x] Event selector buttons
- [x] Anomaly scores bar chart
- [x] Event details panel (Subject ID, Anomaly Score, Risk Level, Timestamp)

### How to Capture:
1. Go to Section 3: "UEBA (User & Entity Behavior Analytics) Security Guard"
2. Click "Run UEBA ingest + visualization"
3. Wait for response
4. Scroll down to see **UEBA Visualization** section (appears automatically when events are loaded)
5. **Screenshot should show:** Event selector, 3 charts in grid (Anomaly Score Timeline, Risk Level Distribution, Anomaly Scores), plus Radar Chart, Intent Path, and Event Details below

---

## ✅ **Screenshot 4: Performance Metrics Dashboard** (Section 7)

### Required Elements:
- [x] **Model comparison (RF vs LSTM)** - ✅ Implemented in `PerformanceDashboard.tsx` (BarChart comparing Precision, Recall, F1)
- [x] **F1 score distribution** - ✅ Implemented in `PerformanceDashboard.tsx` (PieChart)
- [x] **Lead time metrics** - ✅ Implemented in `PerformanceDashboard.tsx` (BarChart for Avg Lead Time & Detection Rate)
- [x] **Performance radar chart** - ✅ Implemented in `PerformanceDashboard.tsx` (RadarChart)
- [x] **Detailed metrics table** - ✅ Implemented in `PerformanceDashboard.tsx` (Table with Precision, Recall, F1, Support)

### Additional Features Visible:
- [x] KPI cards (RF F1 Score, LSTM F1 Score, Detection Rate, UEBA Events)
- [x] Dashboard title and timestamp

### How to Capture:
1. Go to Section 7: "AI Agent Performance Metrics"
2. Click "Show Performance Metrics" button
3. Wait for dashboard to load
4. **Screenshot should show:** KPI cards row, then 4 charts (Model Comparison bar chart, F1 Score pie chart, Lead Time bar chart, Performance Radar chart), then Detailed Metrics table at bottom

---

## ✅ **Screenshot 5: Manufacturing Analytics** (Section 6)

### Required Elements:
- [x] **Clusters data** - ✅ Implemented (in `manufacturingResponse` JSON, field: `clusters`)
- [x] **CAPA recommendations** - ✅ Implemented (in `manufacturingResponse` JSON, field: `capa_recommendations`)
- [x] **Heatmap path reference** - ✅ Implemented (in `manufacturingResponse` JSON, field: `heatmap`)

### How to Capture:
1. Go to Section 6: "Manufacturing RCA / CAPA Insights"
2. Click "Run clustering + heatmap + CAPA"
3. Wait for response
4. **Screenshot should show:** JSON response in "6B. Clusters, heatmap, and CAPA (response)" card
5. **Key fields to highlight in screenshot:**
   - `clusters` array with cluster data
   - `capa_recommendations` array with corrective/preventive actions
   - `heatmap` path string

---

## ✅ **Screenshot 6: Agent Orchestration** (Section 2)

### Required Elements:
- [x] **Primary decision** - ✅ Implemented (in `orchestrationResponse` JSON, field: `primary_decision`)
- [x] **Safety Twin decision** - ✅ Implemented (in `orchestrationResponse` JSON, field: `safety_decision`)
- [x] **Divergence detection** - ✅ Implemented (in `orchestrationResponse` JSON, field: `divergence`)

### How to Capture:
1. **First:** Run Section 1 (Risk Prediction) to get a risk event
2. Go to Section 2: "LangGraph Orchestration + Shadow 'Safety Twin'"
3. Click "Use last risk event in orchestration graph" (or it may auto-trigger)
4. Wait for response
5. **Screenshot should show:** JSON response in "2B. Primary vs Safety Twin decisions (response)" card
6. **Key fields to highlight in screenshot:**
   - `primary_decision` object
   - `safety_decision` object
   - `divergence` object with `changed` flag

---

## 📋 **Summary: All Features Verified**

| Screenshot | Section | Status | Notes |
|-----------|---------|--------|-------|
| **Screenshot 2: Risk Charts** | Section 1 | ✅ **READY** | All charts implemented, shows after clicking "Run live call" |
| **Screenshot 3: UEBA Visualization** | Section 3 | ✅ **READY** | All visualizations implemented, shows after clicking "Run UEBA ingest" |
| **Screenshot 4: Performance Dashboard** | Section 7 | ✅ **READY** | All charts and table implemented, shows after clicking "Show Performance Metrics" |
| **Screenshot 5: Manufacturing Analytics** | Section 6 | ✅ **READY** | JSON response includes all required fields (clusters, CAPA, heatmap) |
| **Screenshot 6: Agent Orchestration** | Section 2 | ✅ **READY** | JSON response includes all required fields (primary_decision, safety_decision, divergence) |

---

## 🎯 **Quick Screenshot Guide**

### **Step-by-Step Process:**

1. **Open Demo:** `https://autopredict.vercel.app`

2. **Screenshot 2 (Risk Charts):**
   - Scroll to Section 1
   - Click "Run live call against /api/v1/telemetry/risk"
   - Wait for response + charts to appear
   - **Capture:** The entire RiskCharts component (4 chart cards)

3. **Screenshot 3 (UEBA Visualization):**
   - Scroll to Section 3
   - Click "Run UEBA ingest + visualization"
   - Wait for visualization to appear below
   - **Capture:** The entire UEBAVisualization component (all charts and panels)

4. **Screenshot 4 (Performance Dashboard):**
   - Scroll to Section 7
   - Click "Show Performance Metrics"
   - Wait for dashboard to load
   - **Capture:** The entire PerformanceDashboard component (KPI cards + all charts + table)

5. **Screenshot 5 (Manufacturing Analytics):**
   - Scroll to Section 6
   - Click "Run clustering + heatmap + CAPA"
   - Wait for JSON response
   - **Capture:** The JSON response card showing clusters, CAPA, and heatmap fields

6. **Screenshot 6 (Agent Orchestration):**
   - **First:** Run Section 1 to get risk event
   - Scroll to Section 2
   - Click "Use last risk event in orchestration graph" (or wait for auto-trigger)
   - Wait for JSON response
   - **Capture:** The JSON response card showing primary_decision, safety_decision, and divergence

---

## ✅ **All Features Are Implemented and Ready for Screenshots!**

Every element mentioned in `DEMO_SLIDE_CONTENT.md` (lines 33-87) is fully implemented and functional in the demo. You can proceed with taking screenshots.


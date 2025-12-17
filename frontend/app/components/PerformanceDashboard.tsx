"use client";

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";

interface PerformanceMetrics {
  model_performance: {
    random_forest?: {
      precision?: number;
      recall?: number;
      f1_score?: number;
      support?: number;
    };
    lstm?: {
      precision?: number;
      recall?: number;
      f1_score?: number;
      support?: number;
    };
    lead_time?: {
      average_lead_minutes?: number;
      detection_rate?: number;
      evaluated_failures?: number;
    };
  };
  ueba_stats?: {
    total_events?: number;
    fitted?: boolean;
  };
  agent_stats?: {
    orchestrations_run?: number;
    agents_active?: string[];
  };
  timestamp?: string;
}

const COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#ef4444"];

export default function PerformanceDashboard() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";
  const apiUrl = `${backendUrl.replace(/\/$/, "")}/api/v1/metrics/performance`;

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const response = await fetch(apiUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch metrics: ${response.statusText}`);
        }
        const data = await response.json();
        setMetrics(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        console.error("Error fetching performance metrics:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "2rem" }}>
        <p>Loading performance metrics...</p>
      </div>
    );
  }

  // Use demo data if metrics are empty or error
  const useDemoData = error || !metrics || !metrics.model_performance || Object.keys(metrics.model_performance).length === 0;
  
  const displayMetrics: PerformanceMetrics = useDemoData ? {
    model_performance: {
      random_forest: {
        precision: 0.947,
        recall: 0.9,
        f1_score: 0.947,
        support: 40,
      },
      lstm: {
        precision: 1.0,
        recall: 1.0,
        f1_score: 1.0,
        support: 40,
      },
      lead_time: {
        average_lead_minutes: 1440, // 24 hours
        detection_rate: 0.85,
        evaluated_failures: 15,
      },
    },
    ueba_stats: {
      total_events: 42,
      fitted: true,
    },
    agent_stats: {
      orchestrations_run: 127,
      agents_active: ["Diagnostics", "Voice", "Scheduling", "Manufacturing", "UEBA Guard"],
    },
    timestamp: new Date().toISOString(),
  } : metrics;

  // Prepare data for charts using displayMetrics
  const modelComparisonData = [
    {
      metric: "Precision",
      RF: (displayMetrics.model_performance?.random_forest?.precision || 0) * 100,
      LSTM: (displayMetrics.model_performance?.lstm?.precision || 0) * 100,
    },
    {
      metric: "Recall",
      RF: (displayMetrics.model_performance?.random_forest?.recall || 0) * 100,
      LSTM: (displayMetrics.model_performance?.lstm?.recall || 0) * 100,
    },
    {
      metric: "F1 Score",
      RF: (displayMetrics.model_performance?.random_forest?.f1_score || 0) * 100,
      LSTM: (displayMetrics.model_performance?.lstm?.f1_score || 0) * 100,
    },
  ];

  const f1Data = [
    { name: "Random Forest", value: (displayMetrics.model_performance?.random_forest?.f1_score || 0) * 100 },
    { name: "LSTM", value: (displayMetrics.model_performance?.lstm?.f1_score || 0) * 100 },
  ];

  const leadTimeData = displayMetrics.model_performance?.lead_time
    ? [
        {
          name: "Avg Lead Time",
          value: (displayMetrics.model_performance.lead_time.average_lead_minutes || 0) / 60, // Convert to hours
        },
        {
          name: "Detection Rate",
          value: (displayMetrics.model_performance.lead_time.detection_rate || 0) * 100,
        },
      ]
    : [];

  const radarData = [
    {
      category: "RF Precision",
      value: (displayMetrics.model_performance?.random_forest?.precision || 0) * 100,
      fullMark: 100,
    },
    {
      category: "RF Recall",
      value: (displayMetrics.model_performance?.random_forest?.recall || 0) * 100,
      fullMark: 100,
    },
    {
      category: "LSTM Precision",
      value: (displayMetrics.model_performance?.lstm?.precision || 0) * 100,
      fullMark: 100,
    },
    {
      category: "LSTM Recall",
      value: (displayMetrics.model_performance?.lstm?.recall || 0) * 100,
      fullMark: 100,
    },
    {
      category: "Detection Rate",
      value: (displayMetrics.model_performance?.lead_time?.detection_rate || 0) * 100,
      fullMark: 100,
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="card">
        <h2 style={{ marginTop: 0, fontSize: "1.5rem", fontWeight: 700 }}>AI Agent Performance Dashboard</h2>
        <p style={{ color: "#64748b", fontSize: "0.9rem" }}>
          Last updated: {displayMetrics.timestamp ? new Date(displayMetrics.timestamp).toLocaleString() : "N/A"}
        </p>
      </div>

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
        <div className="card" style={{ textAlign: "center" }}>
          <h4 style={{ marginTop: 0, fontSize: "0.85rem", color: "#64748b", textTransform: "uppercase" }}>RF F1 Score</h4>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#3b82f6", margin: 0 }}>
            {((displayMetrics.model_performance?.random_forest?.f1_score || 0) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <h4 style={{ marginTop: 0, fontSize: "0.85rem", color: "#64748b", textTransform: "uppercase" }}>LSTM F1 Score</h4>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#8b5cf6", margin: 0 }}>
            {((displayMetrics.model_performance?.lstm?.f1_score || 0) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <h4 style={{ marginTop: 0, fontSize: "0.85rem", color: "#64748b", textTransform: "uppercase" }}>Detection Rate</h4>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#10b981", margin: 0 }}>
            {((displayMetrics.model_performance?.lead_time?.detection_rate || 0) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <h4 style={{ marginTop: 0, fontSize: "0.85rem", color: "#64748b", textTransform: "uppercase" }}>UEBA Events</h4>
          <p style={{ fontSize: "2rem", fontWeight: 700, color: "#f59e0b", margin: 0 }}>
            {displayMetrics.ueba_stats?.total_events || 0}
          </p>
        </div>
        {useDemoData && (
          <div className="card" style={{ textAlign: "center", background: "#fef3c7", border: "1px solid #f59e0b" }}>
            <p style={{ fontSize: "0.85rem", color: "#92400e", margin: 0 }}>
              📊 Showing demo data (artifacts not available)
            </p>
          </div>
        )}
      </div>

      {/* Main Charts Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "1rem" }}>
        {/* Model Comparison */}
        <div className="card">
          <h4 style={{ marginTop: 0, fontSize: "1rem", fontWeight: 600 }}>Model Performance Comparison</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={modelComparisonData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
              <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
              <Legend />
              <Bar dataKey="RF" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              <Bar dataKey="LSTM" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* F1 Score Distribution */}
        <div className="card">
          <h4 style={{ marginTop: 0, fontSize: "1rem", fontWeight: 600 }}>F1 Score Distribution</h4>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={f1Data}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {f1Data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Lead Time Metrics */}
        {leadTimeData.length > 0 && (
          <div className="card">
            <h4 style={{ marginTop: 0, fontSize: "1rem", fontWeight: 600 }}>Lead Time & Detection Metrics</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={leadTimeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value: number) => `${value.toFixed(2)}`} />
                <Bar dataKey="value" fill="#10b981" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Radar Chart */}
        <div className="card">
          <h4 style={{ marginTop: 0, fontSize: "1rem", fontWeight: 600 }}>Overall Performance Radar</h4>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis dataKey="category" tick={{ fontSize: 10 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
              <Radar name="Performance" dataKey="value" stroke="#667eea" fill="#667eea" fillOpacity={0.6} />
              <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Metrics Table */}
      <div className="card">
        <h4 style={{ marginTop: 0, fontSize: "1rem", fontWeight: 600 }}>Detailed Metrics</h4>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
                <th style={{ padding: "0.75rem", textAlign: "left", fontSize: "0.85rem", fontWeight: 600 }}>Model</th>
                <th style={{ padding: "0.75rem", textAlign: "left", fontSize: "0.85rem", fontWeight: 600 }}>Precision</th>
                <th style={{ padding: "0.75rem", textAlign: "left", fontSize: "0.85rem", fontWeight: 600 }}>Recall</th>
                <th style={{ padding: "0.75rem", textAlign: "left", fontSize: "0.85rem", fontWeight: 600 }}>F1 Score</th>
                <th style={{ padding: "0.75rem", textAlign: "left", fontSize: "0.85rem", fontWeight: 600 }}>Support</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>Random Forest</td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {((displayMetrics.model_performance?.random_forest?.precision || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {((displayMetrics.model_performance?.random_forest?.recall || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {((displayMetrics.model_performance?.random_forest?.f1_score || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {displayMetrics.model_performance?.random_forest?.support || 0}
                </td>
              </tr>
              <tr style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>LSTM</td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {((displayMetrics.model_performance?.lstm?.precision || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {((displayMetrics.model_performance?.lstm?.recall || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {((displayMetrics.model_performance?.lstm?.f1_score || 0) * 100).toFixed(2)}%
                </td>
                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                  {displayMetrics.model_performance?.lstm?.support || 0}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


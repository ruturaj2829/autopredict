"use client";

import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

interface RiskData {
  rf_fault_prob?: number;
  lstm_degradation_score?: number;
  ensemble_risk_score?: number;
  failure_probability_next_7_days?: number;
  failure_probability_next_30_days?: number;
  estimated_days_to_failure?: number;
  risk_level?: string;
  urgency?: string;
}

interface RiskChartsProps {
  data: RiskData;
}

const COLORS = {
  HIGH: "#ef4444",
  MEDIUM: "#f59e0b",
  LOW: "#10b981",
};

export default function RiskCharts({ data }: RiskChartsProps) {
  const probabilityData = [
    { name: "RF Fault", value: (data.rf_fault_prob || 0) * 100, fill: "#3b82f6" },
    { name: "LSTM Degradation", value: (data.lstm_degradation_score || 0) * 100, fill: "#8b5cf6" },
    { name: "Ensemble Risk", value: (data.ensemble_risk_score || 0) * 100, fill: "#ec4899" },
  ];

  const failureProbabilityData = [
    { period: "7 Days", probability: (data.failure_probability_next_7_days || 0) * 100 },
    { period: "30 Days", probability: (data.failure_probability_next_30_days || 0) * 100 },
  ];

  const timelineData = Array.from({ length: 30 }, (_, i) => {
    const days = i + 1;
    const baseProb = data.ensemble_risk_score || 0;
    const decay = Math.max(0, 1 - (days / 30));
    return {
      day: days,
      probability: Math.min(100, baseProb * 100 * (1 + (1 - decay) * 0.5)),
    };
  });

  const riskLevelData = [
    { name: "Risk Level", value: data.risk_level || "UNKNOWN", color: COLORS[data.risk_level as keyof typeof COLORS] || "#6b7280" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
      {/* Probability Comparison */}
      <div className="card">
        <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Model Probabilities</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={probabilityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
            <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
              {probabilityData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Failure Probability Timeline */}
      <div className="card">
        <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Failure Probability Over Time</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={timelineData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="day" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
            <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
            <Line
              type="monotone"
              dataKey="probability"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Risk Level Indicator */}
      <div className="card">
        <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Risk Assessment</h4>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "200px" }}>
          <div
            style={{
              width: "120px",
              height: "120px",
              borderRadius: "50%",
              background: `linear-gradient(135deg, ${COLORS[data.risk_level as keyof typeof COLORS] || "#6b7280"} 0%, ${COLORS[data.risk_level as keyof typeof COLORS] || "#6b7280"}80 100%)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontSize: "1.5rem",
              fontWeight: 700,
              boxShadow: `0 8px 24px ${COLORS[data.risk_level as keyof typeof COLORS] || "#6b7280"}40`,
              animation: "pulse 2s ease-in-out infinite",
            }}
          >
            {data.risk_level || "N/A"}
          </div>
          <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#64748b" }}>
            Days to Failure: {data.estimated_days_to_failure || "N/A"}
          </p>
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>
            Urgency: {data.urgency || "N/A"}
          </p>
        </div>
      </div>

      {/* Failure Probability Comparison */}
      <div className="card">
        <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Failure Probability by Period</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={failureProbabilityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
            <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
            <Bar dataKey="probability" fill="#f59e0b" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
          }
        }
      `}</style>
    </div>
  );
}


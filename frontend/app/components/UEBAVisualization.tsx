"use client";

import { useState, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";

interface UEBAEvent {
  event_type: string;
  subject_id: string;
  anomaly_score: number;
  risk_level: string;
  intent_path: string[];
  context: Record<string, any>;
  timestamp: string;
}

interface UEBAVisualizationProps {
  events: UEBAEvent[];
}

export default function UEBAVisualization({ events }: UEBAVisualizationProps) {
  const [selectedEvent, setSelectedEvent] = useState<UEBAEvent | null>(events[0] || null);

  useEffect(() => {
    if (events.length > 0 && !selectedEvent) {
      setSelectedEvent(events[0]);
    }
  }, [events, selectedEvent]);

  // Timeline data
  const timelineData = events.map((event, index) => ({
    time: index + 1,
    anomaly: event.anomaly_score * 100,
    risk: event.risk_level === "HIGH" ? 100 : event.risk_level === "MEDIUM" ? 50 : 10,
  }));

  // Risk level distribution
  const riskDistribution = events.reduce((acc, event) => {
    acc[event.risk_level] = (acc[event.risk_level] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const riskData = Object.entries(riskDistribution).map(([level, count]) => ({
    level,
    count,
  }));

  // Anomaly score distribution
  const anomalyData = events.map((event, index) => ({
    event: `Event ${index + 1}`,
    score: event.anomaly_score * 100,
    subject: event.subject_id,
  }));

  // Intent path visualization
  const intentData = selectedEvent
    ? selectedEvent.intent_path.map((intent, index) => ({
        intent,
        step: index + 1,
        value: 100 - index * 20,
      }))
    : [];

  const radarData = selectedEvent
    ? [
        {
          category: "Anomaly Score",
          value: selectedEvent.anomaly_score * 100,
          fullMark: 100,
        },
        {
          category: "Risk Level",
          value: selectedEvent.risk_level === "HIGH" ? 100 : selectedEvent.risk_level === "MEDIUM" ? 50 : 10,
          fullMark: 100,
        },
        {
          category: "Intent Compliance",
          value: selectedEvent.intent_path.length > 0 ? 80 : 20,
          fullMark: 100,
        },
        {
          category: "Context Richness",
          value: Object.keys(selectedEvent.context || {}).length * 20,
          fullMark: 100,
        },
      ]
    : [];

  const getRiskColor = (level: string) => {
    switch (level) {
      case "HIGH":
        return "#ef4444";
      case "MEDIUM":
        return "#f59e0b";
      case "LOW":
        return "#10b981";
      default:
        return "#6b7280";
    }
  };

  if (events.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "2rem" }}>
        <p style={{ color: "#64748b" }}>No UEBA events yet. Run the UEBA ingest endpoint to see visualizations.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Event Selector */}
      <div className="card">
        <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Select UEBA Event</h4>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {events.map((event, index) => (
            <button
              key={index}
              onClick={() => setSelectedEvent(event)}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: "0.5rem",
                border: selectedEvent === event ? "2px solid #667eea" : "1px solid #cbd5e1",
                background: selectedEvent === event ? "#eff6ff" : "white",
                cursor: "pointer",
                fontSize: "0.8rem",
              }}
            >
              Event {index + 1} ({event.risk_level})
            </button>
          ))}
        </div>
      </div>

      {/* Main Visualizations Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
        {/* Anomaly Score Timeline */}
        <div className="card">
          <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Anomaly Score Timeline</h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={timelineData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
              <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
              <Line
                type="monotone"
                dataKey="anomaly"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Level Distribution */}
        <div className="card">
          <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Risk Level Distribution</h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={riskData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="level" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                {riskData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getRiskColor(entry.level)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Anomaly Score by Event */}
        <div className="card">
          <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Anomaly Scores</h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={anomalyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="event" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
              <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
              <Bar dataKey="score" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Selected Event Details */}
      {selectedEvent && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
          {/* Radar Chart */}
          <div className="card">
            <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Event Risk Profile</h4>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="category" tick={{ fontSize: 10 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar
                  name="Risk Profile"
                  dataKey="value"
                  stroke="#667eea"
                  fill="#667eea"
                  fillOpacity={0.6}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Intent Path */}
          <div className="card">
            <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Intent Path</h4>
            <div style={{ padding: "1rem 0" }}>
              {selectedEvent.intent_path.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {selectedEvent.intent_path.map((intent, index) => (
                    <div
                      key={index}
                      style={{
                        padding: "0.75rem",
                        background: index === 0 ? "#eff6ff" : "#f8fafc",
                        borderRadius: "0.5rem",
                        border: index === 0 ? "2px solid #667eea" : "1px solid #e2e8f0",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                      }}
                    >
                      <span
                        style={{
                          width: "24px",
                          height: "24px",
                          borderRadius: "50%",
                          background: index === 0 ? "#667eea" : "#cbd5e1",
                          color: "white",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "0.7rem",
                          fontWeight: 600,
                        }}
                      >
                        {index + 1}
                      </span>
                      <span style={{ fontSize: "0.85rem", color: "#334155" }}>{intent}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: "#64748b", fontSize: "0.85rem" }}>No intent path available</p>
              )}
            </div>
          </div>

          {/* Event Details */}
          <div className="card">
            <h4 style={{ marginTop: 0, fontSize: "0.9rem", fontWeight: 600 }}>Event Details</h4>
            <div style={{ padding: "1rem 0" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Subject ID</span>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.9rem", fontWeight: 500 }}>{selectedEvent.subject_id}</p>
                </div>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Anomaly Score</span>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.9rem", fontWeight: 500 }}>
                    {(selectedEvent.anomaly_score * 100).toFixed(2)}%
                  </p>
                </div>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Risk Level</span>
                  <p
                    style={{
                      margin: "0.25rem 0 0",
                      fontSize: "0.9rem",
                      fontWeight: 600,
                      color: getRiskColor(selectedEvent.risk_level),
                    }}
                  >
                    {selectedEvent.risk_level}
                  </p>
                </div>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Timestamp</span>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
                    {new Date(selectedEvent.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


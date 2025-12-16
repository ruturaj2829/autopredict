"use client";

import { useState, useEffect, useRef } from "react";

interface TourStep {
  id: string;
  title: string;
  message: string;
  selector?: string;
  highlight?: boolean;
}

const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    title: "Welcome to AutoPredict",
    message: "Welcome to AutoPredict, an Agentic AI-driven Predictive Maintenance and Quality Intelligence Platform. This interactive demo showcases hybrid machine learning, multi-agent orchestration, and real-time risk analysis. Let's take a guided tour!",
  },
  {
    id: "risk",
    title: "Hybrid Risk Prediction",
    message: "Section 1 demonstrates our hybrid Random Forest and LSTM model. It analyzes vehicle telemetry data to predict failure risks with high accuracy. Click 'Run live call' to see real-time risk scoring with dynamic visualizations.",
    selector: "#section-risk",
  },
  {
    id: "orchestration",
    title: "Multi-Agent Orchestration",
    message: "Section 2 shows our LangGraph-based orchestration system. It runs a primary master agent and a safety twin in parallel, comparing their decisions to ensure safe and optimal actions. This is critical for governance and auditability.",
    selector: "#section-orchestration",
  },
  {
    id: "ueba",
    title: "UEBA Security Guard",
    message: "Section 3 features our User and Entity Behavior Analytics system. It monitors agent actions for anomalies and intent deviations, blocking risky operations. This prevents malicious or erroneous agent behavior.",
    selector: "#section-ueba",
  },
  {
    id: "scheduler",
    title: "Intelligent Scheduling",
    message: "Section 4 demonstrates our multi-objective scheduling optimizer. It uses OR-Tools to assign maintenance jobs to technicians while respecting constraints and optimizing for efficiency and risk mitigation.",
    selector: "#section-scheduler",
  },
  {
    id: "manufacturing",
    title: "Manufacturing Analytics",
    message: "Section 5 shows our manufacturing RCA and CAPA analytics. It clusters failure events, generates heatmaps, and provides corrective action recommendations to improve manufacturing quality.",
    selector: "#section-manufacturing",
  },
  {
    id: "complete",
    title: "Tour Complete",
    message: "You've completed the tour! Feel free to explore each section. All features work in demo mode, so you can interact with the system without any setup. Enjoy exploring AutoPredict!",
  },
];

export default function VoiceTour() {
  const [isActive, setIsActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      synthRef.current = window.speechSynthesis;
    }
  }, []);

  const speak = (text: string, onEnd?: () => void) => {
    if (!synthRef.current) return;

    // Cancel any ongoing speech
    synthRef.current.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    if (onEnd) {
      utterance.onend = onEnd;
    }

    utteranceRef.current = utterance;
    synthRef.current.speak(utterance);
    setIsSpeaking(true);
  };

  const stopSpeaking = () => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  };

  const startTour = () => {
    setIsActive(true);
    setShowOverlay(true);
    setCurrentStep(0);
    playStep(0);
  };

  const playStep = (stepIndex: number) => {
    if (stepIndex >= TOUR_STEPS.length) {
      setIsActive(false);
      setShowOverlay(false);
      return;
    }

    const step = TOUR_STEPS[stepIndex];
    setCurrentStep(stepIndex);

    // Scroll to element if selector exists
    if (step.selector) {
      setTimeout(() => {
        const element = document.querySelector(step.selector!);
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "center" });
          // Add highlight effect
          element.classList.add("tour-highlight");
          setTimeout(() => {
            element.classList.remove("tour-highlight");
          }, 2000);
        }
      }, 500);
    }

    // Speak the message
    speak(step.message, () => {
      setIsSpeaking(false);
      // Auto-advance after a short delay
      setTimeout(() => {
        if (stepIndex < TOUR_STEPS.length - 1) {
          playStep(stepIndex + 1);
        } else {
          setIsActive(false);
          setShowOverlay(false);
        }
      }, 1000);
    });
  };

  const nextStep = () => {
    stopSpeaking();
    if (currentStep < TOUR_STEPS.length - 1) {
      playStep(currentStep + 1);
    } else {
      setIsActive(false);
      setShowOverlay(false);
    }
  };

  const prevStep = () => {
    stopSpeaking();
    if (currentStep > 0) {
      playStep(currentStep - 1);
    }
  };

  const skipTour = () => {
    stopSpeaking();
    setIsActive(false);
    setShowOverlay(false);
  };

  const currentStepData = TOUR_STEPS[currentStep];

  return (
    <>
      {!isActive && (
        <button
          onClick={startTour}
          className="voice-tour-btn"
          style={{
            position: "fixed",
            bottom: "2rem",
            right: "2rem",
            zIndex: 1000,
            padding: "1rem 1.5rem",
            borderRadius: "999px",
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color: "white",
            border: "none",
            cursor: "pointer",
            fontSize: "0.9rem",
            fontWeight: 600,
            boxShadow: "0 4px 20px rgba(102, 126, 234, 0.4)",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            transition: "all 0.3s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.05)";
            e.currentTarget.style.boxShadow = "0 6px 25px rgba(102, 126, 234, 0.6)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
            e.currentTarget.style.boxShadow = "0 4px 20px rgba(102, 126, 234, 0.4)";
          }}
        >
          <span>🎙️</span>
          <span>Start Voice Tour</span>
        </button>
      )}

      {isActive && showOverlay && (
        <div
          className="tour-overlay"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.7)",
            zIndex: 9998,
            pointerEvents: "none",
          }}
        />
      )}

      {isActive && (
        <div
          className="tour-card"
          style={{
            position: "fixed",
            bottom: "2rem",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 9999,
            background: "white",
            borderRadius: "1rem",
            padding: "1.5rem",
            maxWidth: "600px",
            width: "90%",
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.3)",
            animation: "slideUp 0.3s ease",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "1rem" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600, color: "#1e293b" }}>
                {currentStepData.title}
              </h3>
              <p style={{ margin: "0.5rem 0 0", fontSize: "0.85rem", color: "#64748b" }}>
                Step {currentStep + 1} of {TOUR_STEPS.length}
              </p>
            </div>
            <button
              onClick={skipTour}
              style={{
                background: "none",
                border: "none",
                fontSize: "1.5rem",
                cursor: "pointer",
                color: "#64748b",
              }}
            >
              ×
            </button>
          </div>

          <p style={{ margin: "0 0 1.5rem", fontSize: "0.95rem", lineHeight: "1.6", color: "#334155" }}>
            {currentStepData.message}
          </p>

          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "space-between" }}>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={prevStep}
                disabled={currentStep === 0}
                style={{
                  padding: "0.5rem 1rem",
                  borderRadius: "0.5rem",
                  border: "1px solid #cbd5e1",
                  background: currentStep === 0 ? "#f1f5f9" : "white",
                  cursor: currentStep === 0 ? "not-allowed" : "pointer",
                  fontSize: "0.85rem",
                }}
              >
                ← Previous
              </button>
              <button
                onClick={nextStep}
                style={{
                  padding: "0.5rem 1rem",
                  borderRadius: "0.5rem",
                  border: "none",
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  color: "white",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                }}
              >
                {currentStep === TOUR_STEPS.length - 1 ? "Finish" : "Next →"}
              </button>
            </div>
            {isSpeaking && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#667eea" }}>
                <span style={{ fontSize: "1.2rem" }}>🔊</span>
                <span style={{ fontSize: "0.8rem" }}>Speaking...</span>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes slideUp {
          from {
            transform: translateX(-50%) translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
          }
        }

        .tour-highlight {
          animation: pulse 2s ease;
          outline: 3px solid #667eea;
          outline-offset: 4px;
          border-radius: 0.5rem;
        }

        @keyframes pulse {
          0%, 100% {
            outline-color: #667eea;
          }
          50% {
            outline-color: #764ba2;
          }
        }
      `}</style>
    </>
  );
}


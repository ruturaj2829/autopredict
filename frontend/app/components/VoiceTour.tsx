"use client";

import { useState, useEffect, useRef } from "react";

interface TourStep {
  id: string;
  title: string;
  message: string;
  selector?: string;
  highlightSelectors?: string[]; // Multiple elements to highlight
  highlightType?: "card" | "button" | "graph" | "section";
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
    message: "Section 1 demonstrates our hybrid Random Forest and LSTM model. Notice the request card on the left and the response card on the right. Click the 'Run live call' button to see real-time risk scoring with dynamic visualizations and charts.",
    selector: "#section-risk",
    highlightSelectors: ["#section-risk .card", "#section-risk .btn-primary"],
    highlightType: "card",
  },
  {
    id: "orchestration",
    title: "Multi-Agent Orchestration",
    message: "Section 2 shows our LangGraph-based orchestration system. The two cards here display the orchestration input and output. It runs a primary master agent and a safety twin in parallel, comparing their decisions.",
    selector: "#section-orchestration",
    highlightSelectors: ["#section-orchestration .card"],
    highlightType: "card",
  },
  {
    id: "ueba",
    title: "UEBA Security Guard",
    message: "Section 3 features our User and Entity Behavior Analytics system. Click the 'Run UEBA ingest' button to see behavior analysis. The visualization below will show anomaly scores, risk levels, and intent paths in beautiful charts.",
    selector: "#section-ueba",
    highlightSelectors: ["#section-ueba .card", "#section-ueba .btn-primary"],
    highlightType: "graph",
  },
  {
    id: "scheduler",
    title: "Intelligent Scheduling",
    message: "Section 4 demonstrates our multi-objective scheduling optimizer. The cards here show the optimization request and response. Notice how the UEBA guard decision is included in the response.",
    selector: "#section-scheduler",
    highlightSelectors: ["#section-scheduler .card"],
    highlightType: "card",
  },
  {
    id: "manufacturing",
    title: "Manufacturing Analytics",
    message: "Section 5 shows our manufacturing RCA and CAPA analytics. Click the button to see clustering results, heatmaps, and corrective action recommendations.",
    selector: "#section-manufacturing",
    highlightSelectors: ["#section-manufacturing .card", "#section-manufacturing .btn-primary"],
    highlightType: "card",
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
  const [highlightedElements, setHighlightedElements] = useState<HTMLElement[]>([]);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      synthRef.current = window.speechSynthesis;
    }
  }, []);

  const clearHighlights = () => {
    highlightedElements.forEach((el) => {
      el.classList.remove("tour-highlight", "tour-highlight-card", "tour-highlight-button", "tour-highlight-graph");
      el.style.zIndex = "";
    });
    setHighlightedElements([]);
  };

  const highlightElements = (selectors: string[], type: string = "card") => {
    clearHighlights();
    const elements: HTMLElement[] = [];
    
    selectors.forEach((selector) => {
      const found = document.querySelectorAll(selector);
      found.forEach((el) => {
        const htmlEl = el as HTMLElement;
        htmlEl.classList.add("tour-highlight");
        htmlEl.classList.add(`tour-highlight-${type}`);
        htmlEl.style.zIndex = "10000";
        htmlEl.style.position = "relative";
        elements.push(htmlEl);
      });
    });
    
    setHighlightedElements(elements);
  };

  const speak = (text: string, onEnd?: () => void) => {
    if (!synthRef.current) return;

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
      clearHighlights();
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
          
          // Highlight specific elements
          if (step.highlightSelectors && step.highlightSelectors.length > 0) {
            setTimeout(() => {
              highlightElements(step.highlightSelectors!, step.highlightType || "card");
            }, 300);
          } else {
            // Default: highlight the section
            setTimeout(() => {
              element.classList.add("tour-highlight");
              element.classList.add("tour-highlight-section");
              const htmlEl = element as HTMLElement;
              htmlEl.style.zIndex = "10000";
              htmlEl.style.position = "relative";
              setHighlightedElements([htmlEl]);
            }, 300);
          }
        }
      }, 500);
    }

    // Speak the message
    speak(step.message, () => {
      setIsSpeaking(false);
      // Auto-advance after a short delay
      setTimeout(() => {
        if (stepIndex < TOUR_STEPS.length - 1) {
          clearHighlights();
          setTimeout(() => {
            playStep(stepIndex + 1);
          }, 300);
        } else {
          clearHighlights();
          setIsActive(false);
          setShowOverlay(false);
        }
      }, 1000);
    });
  };

  const nextStep = () => {
    stopSpeaking();
    clearHighlights();
    if (currentStep < TOUR_STEPS.length - 1) {
      setTimeout(() => {
        playStep(currentStep + 1);
      }, 300);
    } else {
      setIsActive(false);
      setShowOverlay(false);
    }
  };

  const prevStep = () => {
    stopSpeaking();
    clearHighlights();
    if (currentStep > 0) {
      setTimeout(() => {
        playStep(currentStep - 1);
      }, 300);
    }
  };

  const skipTour = () => {
    stopSpeaking();
    clearHighlights();
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
            padding: "1.2rem 2rem",
            borderRadius: "999px",
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color: "white",
            border: "none",
            cursor: "pointer",
            fontSize: "1rem",
            fontWeight: 600,
            boxShadow: "0 8px 32px rgba(102, 126, 234, 0.5)",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            animation: "float 3s ease-in-out infinite",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.08) translateY(-2px)";
            e.currentTarget.style.boxShadow = "0 12px 40px rgba(102, 126, 234, 0.6)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
            e.currentTarget.style.boxShadow = "0 8px 32px rgba(102, 126, 234, 0.5)";
          }}
        >
          <span style={{ fontSize: "1.3rem" }}>🎙️</span>
          <span>Start Voice Tour</span>
        </button>
      )}

      {isActive && (
        <div
          className="tour-card"
          style={{
            position: "fixed",
            top: "2rem",
            right: "2rem",
            zIndex: 9999,
            background: "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)",
            borderRadius: "1.5rem",
            padding: "2rem",
            maxWidth: "420px",
            width: "calc(100% - 4rem)",
            boxShadow: "0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(102, 126, 234, 0.1), 0 8px 32px rgba(102, 126, 234, 0.2)",
            animation: "slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
            border: "1px solid rgba(102, 126, 234, 0.2)",
            backdropFilter: "blur(10px)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "1.5rem" }}>
            <div>
              <h3 style={{ 
                margin: 0, 
                fontSize: "1.3rem", 
                fontWeight: 700, 
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}>
                {currentStepData.title}
              </h3>
              <div style={{ 
                marginTop: "0.5rem", 
                display: "flex", 
                alignItems: "center", 
                gap: "0.5rem" 
              }}>
                <div style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  animation: "pulse 2s ease-in-out infinite",
                }} />
                <p style={{ margin: 0, fontSize: "0.9rem", color: "#64748b", fontWeight: 500 }}>
                  Step {currentStep + 1} of {TOUR_STEPS.length}
                </p>
              </div>
            </div>
            <button
              onClick={skipTour}
              style={{
                background: "rgba(148, 163, 184, 0.1)",
                border: "none",
                fontSize: "1.8rem",
                cursor: "pointer",
                color: "#64748b",
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)";
                e.currentTarget.style.color = "#ef4444";
                e.currentTarget.style.transform = "rotate(90deg)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(148, 163, 184, 0.1)";
                e.currentTarget.style.color = "#64748b";
                e.currentTarget.style.transform = "rotate(0deg)";
              }}
            >
              ×
            </button>
          </div>

          <p style={{ 
            margin: "0 0 1.5rem", 
            fontSize: "0.95rem", 
            lineHeight: "1.7", 
            color: "#334155",
            fontWeight: 400,
          }}>
            {currentStepData.message}
          </p>

          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button
                onClick={prevStep}
                disabled={currentStep === 0}
                style={{
                  padding: "0.75rem 1.5rem",
                  borderRadius: "0.75rem",
                  border: "2px solid #e2e8f0",
                  background: currentStep === 0 ? "#f1f5f9" : "white",
                  cursor: currentStep === 0 ? "not-allowed" : "pointer",
                  fontSize: "0.95rem",
                  fontWeight: 600,
                  color: currentStep === 0 ? "#94a3b8" : "#475569",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  if (currentStep !== 0) {
                    e.currentTarget.style.borderColor = "#667eea";
                    e.currentTarget.style.color = "#667eea";
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentStep !== 0) {
                    e.currentTarget.style.borderColor = "#e2e8f0";
                    e.currentTarget.style.color = "#475569";
                  }
                }}
              >
                ← Previous
              </button>
              <button
                onClick={nextStep}
                style={{
                  padding: "0.75rem 2rem",
                  borderRadius: "0.75rem",
                  border: "none",
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  color: "white",
                  cursor: "pointer",
                  fontSize: "0.95rem",
                  fontWeight: 600,
                  boxShadow: "0 4px 16px rgba(102, 126, 234, 0.4)",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-2px)";
                  e.currentTarget.style.boxShadow = "0 6px 20px rgba(102, 126, 234, 0.5)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow = "0 4px 16px rgba(102, 126, 234, 0.4)";
                }}
              >
                {currentStep === TOUR_STEPS.length - 1 ? "Finish ✨" : "Next →"}
              </button>
            </div>
            {isSpeaking && (
              <div style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "0.5rem", 
                color: "#667eea",
                animation: "pulse 2s ease-in-out infinite",
              }}>
                <span style={{ fontSize: "1.5rem" }}>🔊</span>
                <span style={{ fontSize: "0.9rem", fontWeight: 500 }}>Speaking...</span>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes slideInRight {
          from {
            transform: translateX(30px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-10px);
          }
        }

        .tour-highlight {
          position: relative;
          animation: highlightPulse 2s ease-in-out infinite;
          transition: all 0.3s ease;
        }

        .tour-highlight-card {
          outline: 4px solid #667eea;
          outline-offset: 8px;
          border-radius: 1rem;
          box-shadow: 0 0 0 8px rgba(102, 126, 234, 0.2), 0 20px 60px rgba(102, 126, 234, 0.4) !important;
          transform: scale(1.02);
          background: linear-gradient(135deg, #ffffff 0%, #f0f4ff 100%) !important;
          z-index: 10001 !important;
          position: relative !important;
        }

        .tour-highlight-button {
          outline: 3px solid #667eea;
          outline-offset: 6px;
          border-radius: 999px;
          box-shadow: 0 0 0 6px rgba(102, 126, 234, 0.2), 0 8px 24px rgba(102, 126, 234, 0.5) !important;
          transform: scale(1.05);
          z-index: 10001 !important;
          position: relative !important;
        }

        .tour-highlight-graph {
          outline: 4px solid #667eea;
          outline-offset: 8px;
          border-radius: 1rem;
          box-shadow: 0 0 0 8px rgba(102, 126, 234, 0.2), 0 20px 60px rgba(102, 126, 234, 0.4) !important;
          transform: scale(1.02);
          z-index: 10001 !important;
          position: relative !important;
        }

        .tour-highlight-section {
          outline: 4px solid #667eea;
          outline-offset: 12px;
          border-radius: 1rem;
          box-shadow: 0 0 0 12px rgba(102, 126, 234, 0.15), 0 25px 80px rgba(102, 126, 234, 0.3) !important;
          z-index: 10001 !important;
          position: relative !important;
        }

        @keyframes highlightPulse {
          0%, 100% {
            outline-color: #667eea;
            box-shadow: 0 0 0 8px rgba(102, 126, 234, 0.2), 0 20px 60px rgba(102, 126, 234, 0.4);
          }
          50% {
            outline-color: #764ba2;
            box-shadow: 0 0 0 12px rgba(118, 75, 162, 0.3), 0 25px 80px rgba(118, 75, 162, 0.5);
          }
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.7;
            transform: scale(1.1);
          }
        }
      `}</style>
    </>
  );
}

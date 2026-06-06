// frontend/src/components/ThresholdEditor.tsx
import React, { useEffect, useState } from "react";
import { configApi } from "../api/client";
import { useConfig } from "../hooks/useMetricTrend";
import { useLatestMetrics } from "../hooks/useMetricTrend";

const METRIC_COLORS: Record<string, string> = {
  answer_relevance: "#818cf8",
  faithfulness: "#34d399",
  semantic_similarity: "#fb923c",
};

interface ThresholdEditorProps {
  onSaved?: () => void;
}

export const ThresholdEditor: React.FC<ThresholdEditorProps> = ({ onSaved }) => {
  const { config, loading: configLoading, refresh: refreshConfig } = useConfig();
  const { data: latestMetrics } = useLatestMetrics();

  const [localThresholds, setLocalThresholds] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<"saved" | "error" | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (config?.thresholds) {
      setLocalThresholds(config.thresholds);
      setDirty(false);
    }
  }, [config]);

  const handleChange = (metric: string, raw: string) => {
    const value = parseFloat(raw);
    if (isNaN(value)) return;
    const clamped = Math.max(0, Math.min(1, value));
    setLocalThresholds((prev) => ({ ...prev, [metric]: clamped }));
    setDirty(true);
    setSaveResult(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveResult(null);
    try {
      await configApi.updateThresholds({ thresholds: localThresholds });
      setSaveResult("saved");
      setDirty(false);
      refreshConfig();
      onSaved?.();
    } catch {
      setSaveResult("error");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (config?.thresholds) {
      setLocalThresholds(config.thresholds);
      setDirty(false);
      setSaveResult(null);
    }
  };

  if (configLoading) {
    return (
      <div style={{ color: "#4b5563", padding: "16px", textAlign: "center" }}>
        Loading configuration…
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ color: "#ef4444", padding: "16px" }}>
        Failed to load configuration.
      </div>
    );
  }

  const metrics = Object.keys(localThresholds);

  return (
    <div>
      <div style={{ marginBottom: "16px" }}>
        <p style={{ color: "#6b7280", fontSize: "13px", margin: 0, lineHeight: 1.6 }}>
          Adjust minimum passing scores per metric. Changes are written to{" "}
          <code
            style={{
              background: "#1f2937",
              color: "#818cf8",
              padding: "1px 6px",
              borderRadius: "3px",
              fontSize: "12px",
            }}
          >
            evalci.yaml
          </code>
          {" "}and take effect on the next evaluation run.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}>
        {metrics.map((metric) => {
          const color = METRIC_COLORS[metric] ?? "#9ca3af";
          const currentScore = latestMetrics?.metrics[metric]?.score;
          const threshold = localThresholds[metric] ?? 0.7;
          const wouldPass = currentScore !== undefined ? currentScore >= threshold : undefined;

          return (
            <div
              key={metric}
              style={{
                background: "#0f172a",
                border: "1px solid #1f2937",
                borderRadius: "8px",
                padding: "16px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "12px",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: color,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      color: "#e5e7eb",
                      fontSize: "13px",
                      fontFamily: "monospace",
                    }}
                  >
                    {metric}
                  </span>
                </div>
                {currentScore !== undefined && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ color: "#6b7280" }}>Latest score:</span>
                    <span
                      style={{
                        fontFamily: "monospace",
                        color: wouldPass ? "#22c55e" : "#ef4444",
                        fontWeight: 700,
                      }}
                    >
                      {currentScore.toFixed(3)}
                    </span>
                    <span
                      style={{
                        fontSize: "11px",
                        color: wouldPass ? "#22c55e" : "#ef4444",
                        background: wouldPass ? "#0d2b1a" : "#2b0d0d",
                        padding: "1px 6px",
                        borderRadius: "3px",
                        border: `1px solid ${wouldPass ? "#22c55e44" : "#ef444444"}`,
                      }}
                    >
                      {wouldPass ? "would PASS" : "would FAIL"}
                    </span>
                  </div>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={threshold}
                  onChange={(e) => handleChange(metric, e.target.value)}
                  style={{
                    flex: 1,
                    accentColor: color,
                    height: "4px",
                    cursor: "pointer",
                  }}
                />
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={threshold.toFixed(2)}
                  onChange={(e) => handleChange(metric, e.target.value)}
                  style={{
                    width: "64px",
                    background: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "4px",
                    color: "#e5e7eb",
                    padding: "4px 8px",
                    fontFamily: "monospace",
                    fontSize: "13px",
                    textAlign: "center",
                  }}
                />
              </div>

              {/* Visual bar showing threshold vs current score */}
              {currentScore !== undefined && (
                <div
                  style={{
                    marginTop: "10px",
                    height: "4px",
                    background: "#1f2937",
                    borderRadius: "2px",
                    position: "relative",
                  }}
                >
                  {/* Threshold marker */}
                  <div
                    style={{
                      position: "absolute",
                      left: `${threshold * 100}%`,
                      top: "-3px",
                      width: "2px",
                      height: "10px",
                      background: "#ef4444",
                      transform: "translateX(-50%)",
                    }}
                  />
                  {/* Current score bar */}
                  <div
                    style={{
                      width: `${currentScore * 100}%`,
                      height: "100%",
                      background: wouldPass ? color : "#ef4444",
                      borderRadius: "2px",
                      opacity: 0.7,
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          style={{
            background: dirty && !saving ? "#4f46e5" : "#1f2937",
            border: `1px solid ${dirty && !saving ? "#6366f1" : "#374151"}`,
            color: dirty && !saving ? "#fff" : "#4b5563",
            borderRadius: "6px",
            padding: "8px 20px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: dirty && !saving ? "pointer" : "not-allowed",
            transition: "all 0.15s",
          }}
        >
          {saving ? "Saving…" : "Save Thresholds"}
        </button>

        {dirty && (
          <button
            onClick={handleReset}
            style={{
              background: "transparent",
              border: "1px solid #374151",
              color: "#6b7280",
              borderRadius: "6px",
              padding: "8px 16px",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Reset
          </button>
        )}

        {saveResult === "saved" && (
          <span style={{ color: "#22c55e", fontSize: "13px" }}>✓ Saved successfully</span>
        )}
        {saveResult === "error" && (
          <span style={{ color: "#ef4444", fontSize: "13px" }}>✗ Failed to save</span>
        )}
        {dirty && saveResult === null && (
          <span style={{ color: "#f59e0b", fontSize: "13px" }}>● Unsaved changes</span>
        )}
      </div>
    </div>
  );
};

export default ThresholdEditor;

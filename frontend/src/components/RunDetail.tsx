// frontend/src/components/RunDetail.tsx
import React, { useState } from "react";
import type { EvalRunDetail, SampleResult } from "../types";
import { StatusBadge } from "./StatusBadge";

interface RunDetailProps {
  run: EvalRunDetail;
  onClose?: () => void;
}

const METRIC_COLORS: Record<string, string> = {
  answer_relevance: "#818cf8",
  faithfulness: "#34d399",
  semantic_similarity: "#fb923c",
};

function ScoreBar({ score, threshold }: { score: number; threshold: number }) {
  const pct = Math.round(score * 100);
  const passed = score >= threshold;
  const color = passed ? "#22c55e" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <div
        style={{
          flex: 1,
          height: "6px",
          background: "#1f2937",
          borderRadius: "3px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: "3px",
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "monospace",
          fontSize: "12px",
          color,
          minWidth: "40px",
          textAlign: "right",
        }}
      >
        {score.toFixed(3)}
      </span>
    </div>
  );
}

interface SampleRowProps {
  result: SampleResult;
  threshold: number;
}

function SampleRow({ result, threshold }: SampleRowProps) {
  const [expanded, setExpanded] = useState(false);
  const color = METRIC_COLORS[result.metric_name] ?? "#9ca3af";

  return (
    <>
      <tr
        onClick={() => setExpanded((e) => !e)}
        style={{
          cursor: "pointer",
          borderBottom: "1px solid #111827",
          background: expanded ? "#0f172a" : "transparent",
          transition: "background 0.1s",
        }}
        onMouseEnter={(e) =>
          !expanded && ((e.currentTarget as HTMLTableRowElement).style.background = "#0a0f1a")
        }
        onMouseLeave={(e) =>
          !expanded && ((e.currentTarget as HTMLTableRowElement).style.background = "transparent")
        }
      >
        <td style={{ padding: "8px 12px", color: "#6b7280", fontFamily: "monospace", fontSize: "12px" }}>
          {result.sample_index}
        </td>
        <td
          style={{
            padding: "8px 12px",
            color: "#d1d5db",
            maxWidth: "220px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontSize: "12px",
          }}
          title={result.query}
        >
          {result.query}
        </td>
        <td style={{ padding: "8px 12px" }}>
          <span
            style={{
              fontSize: "11px",
              color,
              fontFamily: "monospace",
              background: `${color}15`,
              padding: "2px 6px",
              borderRadius: "3px",
            }}
          >
            {result.metric_name}
          </span>
        </td>
        <td style={{ padding: "8px 12px", minWidth: "140px" }}>
          <ScoreBar score={result.score} threshold={threshold} />
        </td>
        <td style={{ padding: "8px 12px" }}>
          <StatusBadge status={result.passed} size="sm" />
        </td>
        <td style={{ padding: "8px 12px", color: "#4b5563", fontSize: "11px", fontFamily: "monospace" }}>
          {result.latency_ms}ms
        </td>
        <td style={{ padding: "8px 12px", color: "#4b5563", fontSize: "12px" }}>
          {expanded ? "▲" : "▼"}
        </td>
      </tr>
      {expanded && (
        <tr style={{ background: "#070d18", borderBottom: "1px solid #111827" }}>
          <td colSpan={7} style={{ padding: "16px 20px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
                fontSize: "12px",
              }}
            >
              <div>
                <div style={{ color: "#6b7280", fontWeight: 600, marginBottom: "6px", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  Expected
                </div>
                <div
                  style={{
                    color: "#d1d5db",
                    background: "#0f172a",
                    border: "1px solid #1f2937",
                    borderRadius: "6px",
                    padding: "10px",
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {result.expected_answer}
                </div>
              </div>
              <div>
                <div style={{ color: "#6b7280", fontWeight: 600, marginBottom: "6px", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  Actual
                </div>
                <div
                  style={{
                    color: "#d1d5db",
                    background: "#0f172a",
                    border: "1px solid #1f2937",
                    borderRadius: "6px",
                    padding: "10px",
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {result.actual_answer}
                </div>
              </div>
            </div>
            {result.reasoning && (
              <div style={{ marginTop: "12px" }}>
                <div style={{ color: "#6b7280", fontWeight: 600, marginBottom: "6px", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  Judge Reasoning
                </div>
                <div
                  style={{
                    color: "#9ca3af",
                    background: "#0a0f1a",
                    border: "1px solid #1a2536",
                    borderRadius: "6px",
                    padding: "10px",
                    fontFamily: "monospace",
                    fontSize: "11px",
                    lineHeight: 1.7,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {result.reasoning}
                </div>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export const RunDetail: React.FC<RunDetailProps> = ({ run, onClose }) => {
  const [metricFilter, setMetricFilter] = useState<string>("all");
  const [passFilter, setPassFilter] = useState<"all" | "pass" | "fail">("all");

  const thresholdMap: Record<string, number> = {};
  run.metric_scores.forEach((ms) => {
    thresholdMap[ms.metric_name] = ms.threshold;
  });

  const filteredResults = run.sample_results.filter((r) => {
    if (metricFilter !== "all" && r.metric_name !== metricFilter) return false;
    if (passFilter === "pass" && !r.passed) return false;
    if (passFilter === "fail" && r.passed) return false;
    return true;
  });

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(run, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evalci-run-${run.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const allMetrics = [...new Set(run.sample_results.map((r) => r.metric_name))];

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <h2
              style={{
                margin: 0,
                color: "#f9fafb",
                fontSize: "18px",
                fontFamily: "monospace",
              }}
            >
              Run #{run.id}
            </h2>
            <StatusBadge status={run.status} size="md" />
            <span
              style={{
                color: "#4b5563",
                fontFamily: "monospace",
                fontSize: "12px",
              }}
            >
              {run.run_uuid.slice(0, 8)}
            </span>
          </div>
          <div style={{ color: "#6b7280", fontSize: "13px", marginTop: "4px" }}>
            {run.prompt_file}
            {run.commit_sha && (
              <span style={{ marginLeft: "12px", color: "#818cf8", fontFamily: "monospace" }}>
                @ {run.commit_sha.slice(0, 7)}
              </span>
            )}
            {run.pr_number && (
              <span style={{ marginLeft: "8px", color: "#6b7280" }}>PR #{run.pr_number}</span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleExport}
            style={{
              background: "#1f2937",
              border: "1px solid #374151",
              color: "#9ca3af",
              borderRadius: "6px",
              padding: "6px 14px",
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            ↓ Export JSON
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "1px solid #374151",
                color: "#6b7280",
                borderRadius: "6px",
                padding: "6px 14px",
                fontSize: "12px",
                cursor: "pointer",
              }}
            >
              ✕ Close
            </button>
          )}
        </div>
      </div>

      {/* Aggregate metric scores */}
      {run.metric_scores.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "12px",
            marginBottom: "24px",
          }}
        >
          {run.metric_scores.map((ms) => {
            const color = METRIC_COLORS[ms.metric_name] ?? "#9ca3af";
            return (
              <div
                key={ms.metric_name}
                style={{
                  background: "#0f172a",
                  border: `1px solid ${ms.passed ? color + "44" : "#ef444444"}`,
                  borderRadius: "8px",
                  padding: "14px 16px",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    color: "#6b7280",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: "8px",
                  }}
                >
                  {ms.metric_name.replace(/_/g, " ")}
                </div>
                <div
                  style={{
                    fontSize: "28px",
                    fontFamily: "monospace",
                    fontWeight: 700,
                    color: ms.passed ? color : "#ef4444",
                    lineHeight: 1,
                    marginBottom: "6px",
                  }}
                >
                  {ms.score.toFixed(3)}
                </div>
                <ScoreBar score={ms.score} threshold={ms.threshold} />
                <div style={{ fontSize: "11px", color: "#4b5563", marginTop: "4px" }}>
                  threshold: {ms.threshold.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          marginBottom: "16px",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#6b7280", fontSize: "12px" }}>Filter:</span>
        {["all", ...allMetrics].map((m) => (
          <button
            key={m}
            onClick={() => setMetricFilter(m)}
            style={{
              background: metricFilter === m ? "#1f2937" : "transparent",
              border: `1px solid ${metricFilter === m ? "#374151" : "#1f2937"}`,
              color: metricFilter === m ? "#e5e7eb" : "#6b7280",
              borderRadius: "4px",
              padding: "3px 10px",
              fontSize: "11px",
              fontFamily: "monospace",
              cursor: "pointer",
            }}
          >
            {m}
          </button>
        ))}
        <span style={{ color: "#374151", margin: "0 4px" }}>|</span>
        {(["all", "pass", "fail"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setPassFilter(f)}
            style={{
              background: passFilter === f ? "#1f2937" : "transparent",
              border: `1px solid ${passFilter === f ? "#374151" : "#1f2937"}`,
              color: passFilter === f ? "#e5e7eb" : "#6b7280",
              borderRadius: "4px",
              padding: "3px 10px",
              fontSize: "11px",
              cursor: "pointer",
            }}
          >
            {f}
          </button>
        ))}
        <span style={{ color: "#4b5563", fontSize: "12px", marginLeft: "8px" }}>
          {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Sample results table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr>
              {["#", "Query", "Metric", "Score", "Status", "Latency", ""].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: "8px 12px",
                    color: "#6b7280",
                    fontWeight: 600,
                    fontSize: "11px",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    borderBottom: "1px solid #1f2937",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredResults.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  style={{ padding: "24px", textAlign: "center", color: "#4b5563" }}
                >
                  No results match the current filter.
                </td>
              </tr>
            )}
            {filteredResults.map((r) => (
              <SampleRow
                key={`${r.sample_index}-${r.metric_name}`}
                result={r}
                threshold={thresholdMap[r.metric_name] ?? 0.7}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RunDetail;

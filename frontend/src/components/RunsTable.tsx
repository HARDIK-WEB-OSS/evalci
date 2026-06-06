// frontend/src/components/RunsTable.tsx
import React, { useState } from "react";
import type { EvalRunSummary } from "../types";
import { StatusBadge } from "./StatusBadge";

interface RunsTableProps {
  runs: EvalRunSummary[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  onPageChange: (page: number) => void;
  onSelectRun: (run: EvalRunSummary) => void;
  onDeleteRun: (id: number) => void;
  selectedRunId?: number | null;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortSha(sha: string | null): string {
  if (!sha) return "—";
  return sha.slice(0, 7);
}

const METRIC_COLORS: Record<string, string> = {
  answer_relevance: "#818cf8",
  faithfulness: "#34d399",
  semantic_similarity: "#fb923c",
};

function MetricPills({ scores }: { scores: EvalRunSummary["metric_scores"] }) {
  if (!scores || scores.length === 0) return <span style={{ color: "#4b5563" }}>—</span>;
  return (
    <span style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
      {scores.map((ms) => {
        const color = METRIC_COLORS[ms.metric_name] ?? "#9ca3af";
        return (
          <span
            key={ms.metric_name}
            title={`${ms.metric_name}: ${ms.score.toFixed(3)} (threshold: ${ms.threshold.toFixed(2)})`}
            style={{
              fontSize: "10px",
              fontFamily: "monospace",
              color: ms.passed ? color : "#ef4444",
              background: ms.passed ? `${color}18` : "#ef444418",
              border: `1px solid ${ms.passed ? color : "#ef4444"}44`,
              borderRadius: "3px",
              padding: "1px 6px",
            }}
          >
            {ms.metric_name.split("_").map((w) => w[0]).join("").toUpperCase()}:{" "}
            {ms.score.toFixed(2)}
          </span>
        );
      })}
    </span>
  );
}

export const RunsTable: React.FC<RunsTableProps> = ({
  runs,
  total,
  page,
  pageSize,
  loading,
  onPageChange,
  onSelectRun,
  onDeleteRun,
  selectedRunId,
}) => {
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const totalPages = Math.ceil(total / pageSize);

  const handleDelete = (id: number) => {
    if (confirmDelete === id) {
      onDeleteRun(id);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(id);
      setTimeout(() => setConfirmDelete(null), 3000);
    }
  };

  return (
    <div style={{ fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "13px",
          }}
        >
          <thead>
            <tr>
              {["ID", "Prompt", "Commit", "PR", "Status", "Metrics", "Samples", "Created", ""].map(
                (h) => (
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
                )
              )}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td
                  colSpan={9}
                  style={{ padding: "32px", textAlign: "center", color: "#4b5563" }}
                >
                  Loading…
                </td>
              </tr>
            )}
            {!loading && runs.length === 0 && (
              <tr>
                <td
                  colSpan={9}
                  style={{ padding: "32px", textAlign: "center", color: "#4b5563" }}
                >
                  No evaluation runs yet. Push a PR touching a prompt file to trigger one.
                </td>
              </tr>
            )}
            {runs.map((run) => {
              const isSelected = run.id === selectedRunId;
              return (
                <tr
                  key={run.id}
                  onClick={() => onSelectRun(run)}
                  style={{
                    cursor: "pointer",
                    background: isSelected ? "#111827" : "transparent",
                    borderBottom: "1px solid #111827",
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected)
                      (e.currentTarget as HTMLTableRowElement).style.background = "#0f172a";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected)
                      (e.currentTarget as HTMLTableRowElement).style.background = "transparent";
                  }}
                >
                  <td style={{ padding: "10px 12px", color: "#6b7280", fontFamily: "monospace" }}>
                    #{run.id}
                  </td>
                  <td
                    style={{
                      padding: "10px 12px",
                      color: "#e5e7eb",
                      maxWidth: "180px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={run.prompt_file}
                  >
                    {run.prompt_file.split("/").pop()}
                  </td>
                  <td
                    style={{
                      padding: "10px 12px",
                      fontFamily: "monospace",
                      color: "#818cf8",
                      fontSize: "12px",
                    }}
                  >
                    {shortSha(run.commit_sha)}
                  </td>
                  <td style={{ padding: "10px 12px", color: "#6b7280" }}>
                    {run.pr_number ? `#${run.pr_number}` : "—"}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <StatusBadge status={run.status} size="sm" />
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <MetricPills scores={run.metric_scores} />
                  </td>
                  <td style={{ padding: "10px 12px", color: "#6b7280", textAlign: "center" }}>
                    {run.total_samples}
                  </td>
                  <td
                    style={{ padding: "10px 12px", color: "#6b7280", whiteSpace: "nowrap" }}
                  >
                    {formatDate(run.created_at)}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(run.id);
                      }}
                      style={{
                        background: "transparent",
                        border: `1px solid ${confirmDelete === run.id ? "#ef4444" : "#374151"}`,
                        color: confirmDelete === run.id ? "#ef4444" : "#6b7280",
                        borderRadius: "4px",
                        padding: "2px 8px",
                        fontSize: "11px",
                        cursor: "pointer",
                        transition: "all 0.15s",
                      }}
                      title={confirmDelete === run.id ? "Click again to confirm" : "Delete run"}
                    >
                      {confirmDelete === run.id ? "Confirm?" : "✕"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 16px",
            borderTop: "1px solid #1f2937",
            color: "#6b7280",
            fontSize: "13px",
          }}
        >
          <span>
            {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
          </span>
          <div style={{ display: "flex", gap: "6px" }}>
            <button
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              style={{
                background: "#1f2937",
                border: "1px solid #374151",
                color: page <= 1 ? "#374151" : "#e5e7eb",
                borderRadius: "4px",
                padding: "4px 12px",
                cursor: page <= 1 ? "not-allowed" : "pointer",
                fontSize: "13px",
              }}
            >
              ← Prev
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              style={{
                background: "#1f2937",
                border: "1px solid #374151",
                color: page >= totalPages ? "#374151" : "#e5e7eb",
                borderRadius: "4px",
                padding: "4px 12px",
                cursor: page >= totalPages ? "not-allowed" : "pointer",
                fontSize: "13px",
              }}
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default RunsTable;

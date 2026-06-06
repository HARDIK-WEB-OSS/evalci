// frontend/src/App.tsx
import React, { useState } from "react";
import { MetricTrendChart } from "./components/MetricTrendChart";
import { RunDetail } from "./components/RunDetail";
import { RunsTable } from "./components/RunsTable";
import { StatusBadge } from "./components/StatusBadge";
import { ThresholdEditor } from "./components/ThresholdEditor";
import { useRunDetail, useRuns } from "./hooks/useRuns";
import { useLatestMetrics } from "./hooks/useMetricTrend";
import type { EvalRunSummary } from "./types";

type Tab = "runs" | "trends" | "thresholds";

const METRIC_COLORS: Record<string, string> = {
  answer_relevance: "#818cf8",
  faithfulness: "#34d399",
  semantic_similarity: "#fb923c",
};

function LatestMetricCards() {
  const { data, loading } = useLatestMetrics();

  if (loading) return null;
  if (!data || Object.keys(data.metrics).length === 0) return null;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: "12px",
        marginBottom: "28px",
      }}
    >
      {Object.values(data.metrics).map((ms) => {
        const color = METRIC_COLORS[ms.metric_name] ?? "#9ca3af";
        return (
          <div
            key={ms.metric_name}
            style={{
              background: "#080f1a",
              border: `1px solid ${color}33`,
              borderRadius: "10px",
              padding: "14px 16px",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                color: "#4b5563",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                marginBottom: "6px",
              }}
            >
              {ms.metric_name.replace(/_/g, " ")}
            </div>
            <div
              style={{
                fontSize: "26px",
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontWeight: 700,
                color: ms.passed ? color : "#ef4444",
                lineHeight: 1,
                marginBottom: "6px",
              }}
            >
              {ms.score.toFixed(3)}
            </div>
            <StatusBadge status={ms.passed} size="sm" />
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("runs");
  const [selectedRun, setSelectedRun] = useState<EvalRunSummary | null>(null);
  const [detailRunId, setDetailRunId] = useState<number | null>(null);

  const {
    runs,
    total,
    page,
    pageSize,
    loading,
    error,
    setPage,
    refresh,
    deleteRun,
  } = useRuns();

  const { run: runDetail, loading: detailLoading } = useRunDetail(detailRunId);

  const handleSelectRun = (run: EvalRunSummary) => {
    setSelectedRun(run);
    setDetailRunId(run.id);
  };

  const handleCloseDetail = () => {
    setSelectedRun(null);
    setDetailRunId(null);
  };

  const handleChartClick = (runId: number) => {
    setActiveTab("runs");
    setDetailRunId(runId);
    const found = runs.find((r) => r.id === runId);
    if (found) setSelectedRun(found);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#030712",
        color: "#e5e7eb",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Top bar */}
      <header
        style={{
          borderBottom: "1px solid #0f172a",
          padding: "0 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "56px",
          background: "#030712",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontSize: "18px",
              fontWeight: 800,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              color: "#f9fafb",
              letterSpacing: "-0.03em",
            }}
          >
            eval
            <span style={{ color: "#4f46e5" }}>CI</span>
          </span>
          <span
            style={{
              fontSize: "11px",
              color: "#374151",
              fontFamily: "monospace",
              borderLeft: "1px solid #1f2937",
              paddingLeft: "10px",
              marginLeft: "2px",
            }}
          >
            prompt regression dashboard
          </span>
        </div>
        <button
          onClick={refresh}
          style={{
            background: "transparent",
            border: "1px solid #1f2937",
            color: "#6b7280",
            borderRadius: "6px",
            padding: "5px 12px",
            fontSize: "12px",
            cursor: "pointer",
          }}
          title="Refresh"
        >
          ↻ Refresh
        </button>
      </header>

      <main style={{ maxWidth: "1400px", margin: "0 auto", padding: "28px" }}>
        {/* Latest metric overview */}
        <LatestMetricCards />

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: "0",
            borderBottom: "1px solid #1f2937",
            marginBottom: "24px",
          }}
        >
          {(["runs", "trends", "thresholds"] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: `2px solid ${activeTab === tab ? "#4f46e5" : "transparent"}`,
                color: activeTab === tab ? "#e5e7eb" : "#6b7280",
                padding: "10px 18px",
                fontSize: "13px",
                fontWeight: activeTab === tab ? 600 : 400,
                cursor: "pointer",
                transition: "all 0.15s",
                textTransform: "capitalize",
              }}
            >
              {tab === "runs" ? `Eval Runs${total > 0 ? ` (${total})` : ""}` : tab.replace(/_/g, " ")}
              {tab === "trends" ? " Trends" : ""}
              {tab === "thresholds" ? " Editor" : ""}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "runs" && (
          <div>
            {error && (
              <div
                style={{
                  background: "#2b0d0d",
                  border: "1px solid #ef4444",
                  borderRadius: "8px",
                  padding: "12px 16px",
                  color: "#ef4444",
                  fontSize: "13px",
                  marginBottom: "16px",
                }}
              >
                Error: {error}
              </div>
            )}

            <div
              style={{
                background: "#080f1a",
                border: "1px solid #0f172a",
                borderRadius: "10px",
                overflow: "hidden",
                marginBottom: selectedRun ? "24px" : 0,
              }}
            >
              <RunsTable
                runs={runs}
                total={total}
                page={page}
                pageSize={pageSize}
                loading={loading}
                onPageChange={setPage}
                onSelectRun={handleSelectRun}
                onDeleteRun={deleteRun}
                selectedRunId={selectedRun?.id}
              />
            </div>

            {/* Run detail panel */}
            {detailRunId !== null && (
              <div
                style={{
                  background: "#080f1a",
                  border: "1px solid #0f172a",
                  borderRadius: "10px",
                  padding: "24px",
                }}
              >
                {detailLoading && (
                  <div
                    style={{ color: "#4b5563", textAlign: "center", padding: "32px" }}
                  >
                    Loading run details…
                  </div>
                )}
                {!detailLoading && runDetail && (
                  <RunDetail run={runDetail} onClose={handleCloseDetail} />
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "trends" && (
          <div
            style={{
              background: "#080f1a",
              border: "1px solid #0f172a",
              borderRadius: "10px",
              padding: "24px",
            }}
          >
            <h3
              style={{
                margin: "0 0 20px",
                color: "#f9fafb",
                fontSize: "15px",
                fontWeight: 600,
              }}
            >
              Metric Trends Over Time
            </h3>
            <p style={{ color: "#4b5563", fontSize: "12px", margin: "0 0 20px" }}>
              Click a data point to jump to that run's detail view.
            </p>
            <MetricTrendChart onClickRun={handleChartClick} />
          </div>
        )}

        {activeTab === "thresholds" && (
          <div
            style={{
              background: "#080f1a",
              border: "1px solid #0f172a",
              borderRadius: "10px",
              padding: "24px",
            }}
          >
            <h3
              style={{
                margin: "0 0 6px",
                color: "#f9fafb",
                fontSize: "15px",
                fontWeight: 600,
              }}
            >
              Threshold Configuration
            </h3>
            <ThresholdEditor onSaved={refresh} />
          </div>
        )}
      </main>
    </div>
  );
}

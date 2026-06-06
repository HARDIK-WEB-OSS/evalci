// frontend/src/components/MetricTrendChart.tsx
import React, { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMetricTrend } from "../hooks/useMetricTrend";

const METRIC_COLORS: Record<string, string> = {
  answer_relevance: "#818cf8",
  faithfulness: "#34d399",
  semantic_similarity: "#fb923c",
};

const ALL_METRICS = ["answer_relevance", "faithfulness", "semantic_similarity"];

interface ChartPoint {
  label: string;
  run_id: number;
  run_uuid: string;
  commit_sha: string | null;
  [metric: string]: number | string | null;
}

interface TooltipPayloadItem {
  dataKey: string;
  value: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  // Get metadata from first payload
  const firstItem = payload[0] as TooltipPayloadItem & { payload: ChartPoint };
  const point = (firstItem as unknown as { payload: ChartPoint }).payload;

  return (
    <div
      style={{
        background: "#0f172a",
        border: "1px solid #1f2937",
        borderRadius: "8px",
        padding: "10px 14px",
        fontSize: "12px",
        fontFamily: "monospace",
      }}
    >
      <div style={{ color: "#9ca3af", marginBottom: "6px" }}>{label}</div>
      {point?.run_uuid && (
        <div style={{ color: "#6b7280", marginBottom: "4px" }}>
          Run #{point.run_id} · {point.run_uuid.slice(0, 8)}
        </div>
      )}
      {point?.commit_sha && (
        <div style={{ color: "#818cf8", marginBottom: "6px" }}>
          commit {point.commit_sha.slice(0, 7)}
        </div>
      )}
      {payload.map((item) => (
        <div
          key={item.dataKey}
          style={{ color: item.color, display: "flex", justifyContent: "space-between", gap: "16px" }}
        >
          <span>{item.dataKey.replace(/_/g, " ")}</span>
          <span style={{ fontWeight: 700 }}>{Number(item.value).toFixed(4)}</span>
        </div>
      ))}
    </div>
  );
}

interface SingleMetricChartProps {
  metric: string;
  onClickPoint?: (runId: number) => void;
}

function SingleMetricChart({ metric, onClickPoint }: SingleMetricChartProps) {
  const { data, loading, error } = useMetricTrend(metric, 30);

  if (loading)
    return (
      <div style={{ height: 220, display: "flex", alignItems: "center", justifyContent: "center", color: "#4b5563" }}>
        Loading…
      </div>
    );
  if (error)
    return (
      <div style={{ height: 220, display: "flex", alignItems: "center", justifyContent: "center", color: "#ef4444" }}>
        {error}
      </div>
    );
  if (!data || data.points.length === 0)
    return (
      <div style={{ height: 220, display: "flex", alignItems: "center", justifyContent: "center", color: "#4b5563" }}>
        No data yet
      </div>
    );

  const chartData: ChartPoint[] = data.points.map((p, i) => ({
    label: `#${p.run_id}`,
    run_id: p.run_id,
    run_uuid: p.run_uuid,
    commit_sha: p.commit_sha,
    [metric]: p.score,
  }));

  const threshold = data.points[data.points.length - 1]?.threshold ?? 0;
  const color = METRIC_COLORS[metric] ?? "#9ca3af";

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart
        data={chartData}
        margin={{ top: 8, right: 16, left: -10, bottom: 0 }}
        onClick={(e) => {
          if (e?.activePayload?.[0]) {
            const pt = e.activePayload[0].payload as ChartPoint;
            onClickPoint?.(pt.run_id);
          }
        }}
        style={{ cursor: onClickPoint ? "pointer" : "default" }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="label"
          tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "monospace" }}
          axisLine={{ stroke: "#1f2937" }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "monospace" }}
          axisLine={{ stroke: "#1f2937" }}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={threshold}
          stroke="#ef4444"
          strokeDasharray="4 4"
          strokeWidth={1.5}
          label={{ value: `min ${threshold.toFixed(2)}`, fill: "#ef4444", fontSize: 10, position: "right" }}
        />
        <Line
          type="monotone"
          dataKey={metric}
          stroke={color}
          strokeWidth={2}
          dot={{ r: 4, fill: color, strokeWidth: 0 }}
          activeDot={{ r: 6, fill: color }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface MetricTrendChartProps {
  onClickRun?: (runId: number) => void;
}

export const MetricTrendChart: React.FC<MetricTrendChartProps> = ({ onClickRun }) => {
  const [activeMetric, setActiveMetric] = useState<string>(ALL_METRICS[0]);

  return (
    <div>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        {ALL_METRICS.map((m) => {
          const color = METRIC_COLORS[m] ?? "#9ca3af";
          const isActive = m === activeMetric;
          return (
            <button
              key={m}
              onClick={() => setActiveMetric(m)}
              style={{
                background: isActive ? `${color}22` : "transparent",
                border: `1px solid ${isActive ? color : "#374151"}`,
                color: isActive ? color : "#6b7280",
                borderRadius: "6px",
                padding: "5px 12px",
                fontSize: "12px",
                fontFamily: "monospace",
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {m.replace(/_/g, " ")}
            </button>
          );
        })}
      </div>
      <SingleMetricChart metric={activeMetric} onClickPoint={onClickRun} />
    </div>
  );
};

export default MetricTrendChart;

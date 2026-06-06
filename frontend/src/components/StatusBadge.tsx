// frontend/src/components/StatusBadge.tsx
import React from "react";
import type { RunStatus } from "../types";

interface StatusBadgeProps {
  status: RunStatus | boolean;
  size?: "sm" | "md" | "lg";
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  passed: { label: "PASS", bg: "#0d2b1a", text: "#22c55e", dot: "#22c55e" },
  failed: { label: "FAIL", bg: "#2b0d0d", text: "#ef4444", dot: "#ef4444" },
  regression: { label: "REGRESSION", bg: "#2b1a0d", text: "#f97316", dot: "#f97316" },
  running: { label: "RUNNING", bg: "#0d1a2b", text: "#3b82f6", dot: "#3b82f6" },
  pending: { label: "PENDING", bg: "#1a1a1a", text: "#9ca3af", dot: "#9ca3af" },
  error: { label: "ERROR", bg: "#2b0d1a", text: "#ec4899", dot: "#ec4899" },
  true: { label: "PASS", bg: "#0d2b1a", text: "#22c55e", dot: "#22c55e" },
  false: { label: "FAIL", bg: "#2b0d0d", text: "#ef4444", dot: "#ef4444" },
};

const SIZE_CONFIG = {
  sm: { fontSize: "10px", padding: "2px 7px", dotSize: "5px" },
  md: { fontSize: "11px", padding: "3px 10px", dotSize: "6px" },
  lg: { fontSize: "13px", padding: "4px 13px", dotSize: "7px" },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const key = String(status);
  const cfg = STATUS_CONFIG[key] ?? STATUS_CONFIG.pending;
  const sz = SIZE_CONFIG[size];

  const isPulsing = key === "running";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        background: cfg.bg,
        color: cfg.text,
        fontSize: sz.fontSize,
        fontWeight: 700,
        letterSpacing: "0.08em",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        padding: sz.padding,
        borderRadius: "4px",
        border: `1px solid ${cfg.text}33`,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: sz.dotSize,
          height: sz.dotSize,
          borderRadius: "50%",
          background: cfg.dot,
          flexShrink: 0,
          animation: isPulsing ? "pulse 1.5s ease-in-out infinite" : undefined,
        }}
      />
      {cfg.label}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </span>
  );
};

export default StatusBadge;

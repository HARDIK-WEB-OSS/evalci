# backend/utils/report.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.metrics.regression_guard import RegressionReport
from backend.runner import EvalRunResult


def _status_icon(passed: bool) -> str:
    return "✅" if passed else "❌"


def generate_json_report(
    result: EvalRunResult,
    regression_report: Optional[RegressionReport] = None,
    changed_files: Optional[list[str]] = None,
) -> dict:
    """Generate a machine-readable JSON report."""
    report = {
        "evalci_version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_uuid": result.run_uuid,
        "run_id": result.run_id,
        "status": result.status,
        "prompt_file": result.prompt_file,
        "total_samples": result.total_samples,
        "aggregate_scores": result.aggregate_scores,
        "threshold_results": result.threshold_results,
        "has_regression": regression_report.has_regression if regression_report else False,
        "changed_files": changed_files or [],
        "regression_violations": [],
        "sample_results": [],
    }

    if regression_report and regression_report.violations:
        report["regression_violations"] = [
            {
                "metric": v.metric,
                "baseline": v.baseline,
                "current": v.current,
                "delta": v.delta,
                "threshold": v.threshold,
                "allowed_delta": v.allowed_delta,
                "violation_type": v.violation_type,
                "severity": v.severity,
            }
            for v in regression_report.violations
        ]

    for sr in result.sample_results:
        for metric_name, metric_result in sr.results.items():
            report["sample_results"].append({
                "sample_index": sr.sample_index,
                "query": sr.query[:200],
                "expected_answer": sr.expected_answer[:500],
                "actual_answer": sr.actual_answer[:500],
                "metric": metric_name,
                "score": metric_result.score,
                "passed": metric_result.passed,
                "reasoning": metric_result.reasoning[:500] if metric_result.reasoning else "",
                "latency_ms": metric_result.latency_ms,
            })

    return report


def generate_markdown_report(
    result: EvalRunResult,
    regression_report: Optional[RegressionReport] = None,
    changed_files: Optional[list[str]] = None,
) -> str:
    """Generate a GitHub-flavored markdown report suitable for PR comments."""
    lines: list[str] = []
    overall_pass = result.status in ("passed",) and (
        not regression_report or not regression_report.has_regression
    )
    overall_icon = "✅" if overall_pass else "❌"

    lines.append(f"## {overall_icon} EvalCI Prompt Regression Report")
    lines.append("")

    # Summary table
    lines.append("### Run Summary")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Run UUID | `{result.run_uuid[:8]}...` |")
    lines.append(f"| Prompt | `{result.prompt_file}` |")
    lines.append(f"| Status | `{result.status.upper()}` |")
    lines.append(f"| Samples Evaluated | {result.total_samples} |")
    lines.append(f"| Generated | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} |")
    lines.append("")

    # What changed
    if changed_files:
        lines.append("### 📝 What Changed")
        lines.append("")
        for f in changed_files:
            lines.append(f"- `{f}`")
        lines.append("")

    # Metric scores
    lines.append("### 📊 Metric Scores")
    lines.append("")
    lines.append("| Metric | Score | Threshold | Status |")
    lines.append("|--------|-------|-----------|--------|")
    for metric, score in result.aggregate_scores.items():
        threshold = 0.0
        if regression_report:
            for v in regression_report.violations:
                if v.metric == metric:
                    threshold = v.threshold
                    break
        passed = result.threshold_results.get(metric, False)
        icon = _status_icon(passed)
        lines.append(f"| {metric} | {score:.4f} | {threshold:.2f} | {icon} |")
    lines.append("")

    # Regression violations
    if regression_report and regression_report.violations:
        lines.append("### 🚨 Regression Violations")
        lines.append("")
        lines.append("> The following metrics have regressed beyond allowed thresholds.")
        lines.append("")
        lines.append("| Metric | Baseline | Current | Delta | Type | Severity |")
        lines.append("|--------|----------|---------|-------|------|----------|")
        for v in regression_report.violations:
            delta_str = f"{v.delta:+.4f}"
            lines.append(
                f"| **{v.metric}** | {v.baseline:.4f} | {v.current:.4f} | "
                f"**{delta_str}** | {v.violation_type} | {v.severity.upper()} |"
            )
        lines.append("")
    elif regression_report:
        lines.append("### ✅ No Regression Detected")
        lines.append("")
        lines.append(
            f"All {len(regression_report.passed_metrics)} metrics are within acceptable ranges."
        )
        lines.append("")

    # Per-sample breakdown (truncated to 5 samples for readability)
    lines.append("### 🔍 Sample Breakdown (first 5)")
    lines.append("")
    lines.append("| # | Query | Metric | Score | Pass |")
    lines.append("|---|-------|--------|-------|------|")

    shown = 0
    for sr in result.sample_results[:5]:
        query_preview = sr.query[:60] + ("..." if len(sr.query) > 60 else "")
        for metric_name, mr in sr.results.items():
            icon = _status_icon(mr.passed)
            lines.append(
                f"| {sr.sample_index} | {query_preview} | {metric_name} | "
                f"{mr.score:.4f} | {icon} |"
            )
            shown += 1

    if result.total_samples > 5:
        lines.append(f"")
        lines.append(f"_...and {result.total_samples - 5} more samples. See full report artifact._")
    lines.append("")

    lines.append("---")
    lines.append("_Generated by [EvalCI](https://github.com/your-org/evalci) — Prompt changes are code changes. They deserve the same gates._")

    return "\n".join(lines)


def write_reports(
    result: EvalRunResult,
    output_dir: str = ".",
    regression_report: Optional[RegressionReport] = None,
    changed_files: Optional[list[str]] = None,
) -> tuple[str, str]:
    """
    Write eval_report.json and eval_report.md to output_dir.
    Returns (json_path, md_path).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_data = generate_json_report(result, regression_report, changed_files)
    json_path = out / "eval_report.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    md_content = generate_markdown_report(result, regression_report, changed_files)
    md_path = out / "eval_report.md"
    with open(md_path, "w") as f:
        f.write(md_content)

    return str(json_path), str(md_path)

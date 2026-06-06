# tests/test_regression_guard.py
from __future__ import annotations

import pytest

from backend.metrics.regression_guard import RegressionGuard, RegressionReport, RegressionViolation


class TestRegressionGuard:
    @pytest.fixture
    def guard(self) -> RegressionGuard:
        return RegressionGuard(default_allowed_delta=0.05)

    @pytest.fixture
    def thresholds(self) -> dict[str, float]:
        return {
            "answer_relevance": 0.70,
            "faithfulness": 0.75,
            "semantic_similarity": 0.65,
        }

    def test_all_metrics_pass_no_regression(self, guard, thresholds):
        current = {"answer_relevance": 0.85, "faithfulness": 0.88, "semantic_similarity": 0.78}
        baseline = {"answer_relevance": 0.84, "faithfulness": 0.87, "semantic_similarity": 0.77}

        report = guard.check(current, baseline, thresholds)

        assert isinstance(report, RegressionReport)
        assert report.has_regression is False
        assert len(report.violations) == 0
        assert len(report.passed_metrics) == 3

    def test_absolute_threshold_violation(self, guard, thresholds):
        # Score is below absolute threshold, regardless of baseline
        current = {"answer_relevance": 0.55}
        baseline = {"answer_relevance": 0.56}  # Only tiny drop, but below threshold

        report = guard.check(current, baseline, thresholds)

        assert report.has_regression is True
        assert len(report.violations) == 1
        v = report.violations[0]
        assert v.metric == "answer_relevance"
        assert v.violation_type == "absolute"
        assert v.current == pytest.approx(0.55)

    def test_relative_regression_within_threshold(self, guard, thresholds):
        # Drop of 0.04 is within allowed_delta of 0.05
        current = {"answer_relevance": 0.80}
        baseline = {"answer_relevance": 0.84}

        report = guard.check(current, baseline, thresholds)

        assert report.has_regression is False

    def test_relative_regression_exceeds_allowed_delta(self, guard, thresholds):
        # Drop of 0.08 exceeds allowed_delta of 0.05
        current = {"faithfulness": 0.80}
        baseline = {"faithfulness": 0.88}

        report = guard.check(current, baseline, thresholds)

        assert report.has_regression is True
        v = report.violations[0]
        assert v.metric == "faithfulness"
        assert v.violation_type == "regression"
        assert v.delta == pytest.approx(-0.08, abs=0.001)

    def test_multiple_violations_detected(self, guard, thresholds):
        current = {
            "answer_relevance": 0.50,   # below threshold (0.70)
            "faithfulness": 0.76,       # fine
            "semantic_similarity": 0.40, # below threshold (0.65)
        }
        baseline = {
            "answer_relevance": 0.85,
            "faithfulness": 0.80,
            "semantic_similarity": 0.80,
        }

        report = guard.check(current, baseline, thresholds)

        assert report.has_regression is True
        assert len(report.violations) == 2
        violated_metrics = {v.metric for v in report.violations}
        assert violated_metrics == {"answer_relevance", "semantic_similarity"}
        assert "faithfulness" in report.passed_metrics

    def test_no_baseline_uses_only_absolute_check(self, guard, thresholds):
        # When no baseline is provided, only absolute threshold check applies
        current = {"answer_relevance": 0.75}  # above threshold
        baseline = {}

        report = guard.check(current, baseline, thresholds)

        assert report.has_regression is False

    def test_no_baseline_fails_absolute_threshold(self, guard, thresholds):
        current = {"answer_relevance": 0.60}  # below 0.70 threshold
        baseline = {}

        report = guard.check(current, baseline, thresholds)

        assert report.has_regression is True
        assert report.violations[0].violation_type == "absolute"

    def test_violation_severity_critical(self, guard, thresholds):
        current = {"answer_relevance": 0.30}  # drop of 0.55 from baseline
        baseline = {"answer_relevance": 0.85}

        report = guard.check(current, baseline, thresholds)

        assert report.violations[0].severity == "critical"

    def test_violation_severity_medium(self, guard, thresholds):
        # Drop of 0.06 — just over allowed delta, but not severe
        current = {"faithfulness": 0.77}
        baseline = {"faithfulness": 0.83}

        report = guard.check(current, baseline, thresholds)

        assert len(report.violations) == 1
        assert report.violations[0].severity == "medium"

    def test_summary_string_no_regression(self, guard, thresholds):
        current = {"answer_relevance": 0.85}
        baseline = {"answer_relevance": 0.84}
        report = guard.check(current, baseline, thresholds)
        assert "✅" in report.summary
        assert "passed" in report.summary.lower()

    def test_summary_string_with_regression(self, guard, thresholds):
        current = {"answer_relevance": 0.50}
        baseline = {"answer_relevance": 0.85}
        report = guard.check(current, baseline, thresholds)
        assert "❌" in report.summary
        assert "answer_relevance" in report.summary

    def test_per_metric_allowed_delta(self, guard, thresholds):
        """Custom per-metric delta should override default."""
        current = {"answer_relevance": 0.78}
        baseline = {"answer_relevance": 0.85}
        # Drop of 0.07, which is within 0.10 custom delta
        allowed_deltas = {"answer_relevance": 0.10}

        report = guard.check(current, baseline, thresholds, allowed_deltas=allowed_deltas)

        assert report.has_regression is False

# backend/models.py
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    REGRESSION = "regression"
    ERROR = "error"


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    prompt_file: Mapped[str] = mapped_column(String(512), nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    pr_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pipeline_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_samples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    metric_scores: Mapped[list["MetricScore"]] = relationship(
        "MetricScore", back_populates="run", cascade="all, delete-orphan"
    )
    sample_results: Mapped[list["SampleResult"]] = relationship(
        "SampleResult", back_populates="run", cascade="all, delete-orphan"
    )


class MetricScore(Base):
    __tablename__ = "metric_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Integer, nullable=False)  # SQLite stores bool as int
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="metric_scores")


class SampleResult(Base):
    __tablename__ = "sample_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False)
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    actual_answer: Mapped[str] = mapped_column(Text, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="sample_results")

# backend/routers/runs.py
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings as get_settings
from backend.database import get_session
from backend.models import EvalRun
from backend.runner import EvalRunner, EvalSample, RunMetadata
from backend.schemas import (
    EvalRunDetail,
    EvalRunSummary,
    RunsListResponse,
    TriggerRunRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["runs"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=EvalRunDetail, status_code=201)
async def trigger_run(body: TriggerRunRequest, session: SessionDep):
    cfg = get_settings()
    samples = [
        EvalSample(
            query=s.query,
            context=s.context,
            expected_answer=s.expected_answer,
        )
        for s in body.dataset
    ]
    metadata = RunMetadata(
        prompt_file=body.metadata.prompt_file,
        commit_sha=body.metadata.commit_sha or cfg.commit_sha,
        pr_number=body.metadata.pr_number or cfg.pr_number,
        pipeline_version=body.metadata.pipeline_version or cfg.pipeline_version,
    )
    runner = EvalRunner(settings=cfg, session=session)
    result = await runner.run(
        dataset=samples,
        prompt_template=body.prompt_template,
        run_metadata=metadata,
    )

    # Reload the run with relationships
    db_run = await session.get(
        EvalRun,
        result.run_id,
        options=[
            selectinload(EvalRun.metric_scores),
            selectinload(EvalRun.sample_results),
        ],
    )
    if db_run is None:
        raise HTTPException(status_code=500, detail="Run record not found after creation")
    return EvalRunDetail.model_validate(db_run)


@router.get("", response_model=RunsListResponse)
async def list_runs(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    total_result = await session.execute(select(func.count()).select_from(EvalRun))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    runs_result = await session.execute(
        select(EvalRun)
        .options(selectinload(EvalRun.metric_scores))
        .order_by(EvalRun.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    runs = runs_result.scalars().all()

    return RunsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[EvalRunSummary.model_validate(r) for r in runs],
    )


@router.get("/{run_id}", response_model=EvalRunDetail)
async def get_run(run_id: int, session: SessionDep):
    result = await session.execute(
        select(EvalRun)
        .where(EvalRun.id == run_id)
        .options(
            selectinload(EvalRun.metric_scores),
            selectinload(EvalRun.sample_results),
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return EvalRunDetail.model_validate(run)


@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: int, session: SessionDep):
    result = await session.execute(select(EvalRun).where(EvalRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    await session.delete(run)
    await session.commit()

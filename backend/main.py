# backend/main.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database import init_db
from backend.routers import metrics as metrics_router
from backend.routers import runs as runs_router
from backend.schemas import ThresholdUpdateRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EvalCI backend — initializing database...")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down EvalCI backend.")


app = FastAPI(
    title="EvalCI API",
    description="Prompt Regression CI — pytest for LLM prompts",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router.router)
app.include_router(metrics_router.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "evalci-backend"}


@app.get("/config")
async def get_config():
    cfg = get_settings()
    return {
        "ollama_url": cfg.ollama_url,
        "judge_model": cfg.judge_model,
        "dataset_path": cfg.dataset_path,
        "enabled_metrics": cfg.enabled_metrics,
        "thresholds": cfg.thresholds,
        "max_concurrent_evals": cfg.max_concurrent_evals,
        "judge_timeout_seconds": cfg.judge_timeout_seconds,
        "regression_allowed_delta": cfg.regression_allowed_delta,
        "block_on_regression": cfg.block_on_regression,
    }


@app.put("/config/thresholds")
async def update_thresholds(body: ThresholdUpdateRequest):
    """Update threshold values in the evalci.yaml config file."""
    import os
    config_path = os.environ.get("EVALCI_CONFIG_PATH", "evalci.yaml")

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        config_data = {}

    config_data["thresholds"] = body.thresholds

    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    # Invalidate the settings singleton so next request reloads
    import backend.config as config_module
    config_module._settings = None

    return {"updated": True, "thresholds": body.thresholds}

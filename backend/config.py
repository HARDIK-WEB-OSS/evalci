# backend/config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVALCI_",
        env_file=".env",
        extra="ignore",
    )

    ollama_url: str = "http://localhost:11434"
    judge_model: str = "mistral"
    dataset_path: str = "example/golden_dataset.json"
    db_url: str = "sqlite+aiosqlite:///./evalci.db"
    thresholds: dict[str, float] = {
        "answer_relevance": 0.70,
        "faithfulness": 0.75,
        "semantic_similarity": 0.65,
    }
    enabled_metrics: list[str] = [
        "answer_relevance",
        "faithfulness",
        "semantic_similarity",
    ]
    judge_timeout_seconds: int = 25
    max_concurrent_evals: int = 5
    pr_number: Optional[str] = None
    commit_sha: Optional[str] = None
    pipeline_version: Optional[str] = None
    prompt_dirs: list[str] = ["example/prompts"]
    regression_allowed_delta: float = 0.05
    block_on_regression: bool = True

    def model_post_init(self, __context) -> None:
        """Override individual thresholds from environment variables if set."""
        overrides = {
            "answer_relevance": os.environ.get("EVALCI_THRESHOLD_ANSWER_RELEVANCE"),
            "faithfulness": os.environ.get("EVALCI_THRESHOLD_FAITHFULNESS"),
            "semantic_similarity": os.environ.get("EVALCI_THRESHOLD_SEMANTIC_SIMILARITY"),
        }
        for key, val in overrides.items():
            if val is not None:
                try:
                    self.thresholds[key] = float(val)
                except ValueError:
                    pass

    @classmethod
    def from_yaml(cls, path: Optional[str] = None) -> "Settings":
        config_path = path or os.environ.get("EVALCI_CONFIG_PATH", "evalci.yaml")
        yaml_data: dict = {}
        if Path(config_path).exists():
            with open(config_path, "r") as f:
                raw = yaml.safe_load(f) or {}
            # Flatten regression sub-dict
            if "regression" in raw:
                reg = raw.pop("regression")
                if "allowed_delta" in reg:
                    raw["regression_allowed_delta"] = reg["allowed_delta"]
                if "block_on_regression" in reg:
                    raw["block_on_regression"] = reg["block_on_regression"]
            yaml_data = raw
        return cls(**yaml_data)


def get_settings() -> Settings:
    return Settings.from_yaml()


# Module-level singleton — re-instantiated per process start
_settings: Optional[Settings] = None


def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings

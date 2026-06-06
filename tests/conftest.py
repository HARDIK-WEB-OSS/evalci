# tests/conftest.py
from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import Settings
from backend.database import Base
from backend.judge import OllamaJudge

# ── In-memory SQLite for tests ─────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        from backend import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── Settings fixture ───────────────────────────────────────────────────────

@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        ollama_url="http://localhost:11434",
        judge_model="mistral",
        dataset_path="example/golden_dataset.json",
        db_url=TEST_DB_URL,
        thresholds={
            "answer_relevance": 0.70,
            "faithfulness": 0.75,
            "semantic_similarity": 0.65,
        },
        enabled_metrics=["answer_relevance", "faithfulness", "semantic_similarity"],
        judge_timeout_seconds=10,
        max_concurrent_evals=2,
    )


# ── Mock judge ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_judge_perfect():
    """A judge that always returns a perfect score JSON response."""
    judge = AsyncMock(spec=OllamaJudge)
    judge.judge = AsyncMock(
        return_value='{"score": 0.95, "reasoning": "Excellent answer, directly addresses the question."}'
    )
    return judge


@pytest.fixture
def mock_judge_poor():
    """A judge that always returns a poor score JSON response."""
    judge = AsyncMock(spec=OllamaJudge)
    judge.judge = AsyncMock(
        return_value='{"score": 0.15, "reasoning": "Answer is off-topic and does not address the question."}'
    )
    return judge


@pytest.fixture
def mock_judge_faithfulness_decompose():
    """
    Judge that returns claim list on first call, then verification on subsequent calls.
    Used for faithfulness two-step testing.
    """
    judge = AsyncMock(spec=OllamaJudge)
    call_count = 0

    async def side_effect(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Decomposition step
            return '["The API uses Bearer token authentication.", "Keys expire after 90 days."]'
        else:
            # Verification step
            return '{"supported": true, "reasoning": "This claim is directly stated in the context."}'

    judge.judge = AsyncMock(side_effect=side_effect)
    return judge


@pytest.fixture
def mock_judge_faithfulness_hallucination():
    """Judge for testing low faithfulness when answer hallucinate."""
    judge = AsyncMock(spec=OllamaJudge)
    call_count = 0

    async def side_effect(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["The API uses OAuth2.", "Keys expire after 30 days.", "Rate limiting is 1000 req/min."]'
        else:
            return '{"supported": false, "reasoning": "This claim is not found in the provided context."}'

    judge.judge = AsyncMock(side_effect=side_effect)
    return judge


# ── Sample data ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_query() -> str:
    return "How do I authenticate API requests?"


@pytest.fixture
def sample_context() -> str:
    return (
        "EvalCI uses API key authentication. Include the header "
        "'Authorization: Bearer <your-api-key>' in every request. "
        "Keys can be generated from the Settings page and expire after 90 days."
    )


@pytest.fixture
def sample_expected() -> str:
    return (
        "Authenticate by including 'Authorization: Bearer <your-api-key>' in headers. "
        "Generate keys from Settings. Keys expire after 90 days."
    )


@pytest.fixture
def sample_perfect_answer() -> str:
    return (
        "To authenticate API requests, include the 'Authorization: Bearer <your-api-key>' "
        "header. Generate your API key from the Settings page. Keys expire after 90 days."
    )


@pytest.fixture
def sample_wrong_answer() -> str:
    return "You need to use a username and password with HTTP Basic Auth over HTTPS."


@pytest.fixture
def sample_empty_context() -> str:
    return ""

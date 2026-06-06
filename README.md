# EvalCI

> **Prompt changes are code changes. They deserve the same gates.**

EvalCI is a lightweight, self-hosted, zero-API-cost Prompt Regression CI system. Think of it as `pytest` for LLM prompts. It runs automatically in GitHub Actions on every PR that touches a prompt file, evaluates the changed prompts against a golden dataset using a local Ollama model as judge, and blocks the merge if metrics regress beyond configured thresholds.

---

## The Problem

Modern LLM-powered applications depend on carefully crafted prompts. But unlike code, prompts are typically changed without any automated quality gate. A small tweak to a RAG prompt template — changing "answer based on context" to "be helpful and creative" — can silently destroy faithfulness scores in production. Nobody notices until users complain.

EvalCI treats prompt changes like code changes. Every PR that modifies a `.txt`, `.md`, or `.jinja2` file under your `prompts/` directory automatically triggers a regression evaluation. If any metric drops below its threshold or regresses by more than the configured delta, the PR is blocked. The full breakdown — per-sample scores, judge reasoning, trend charts — is posted directly as a PR comment.

EvalCI runs 100% locally. It requires no paid APIs, no external services, and no data leaves your infrastructure. The only dependency is Ollama running on your CI runner or server.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Actions                          │
│                                                                 │
│  PR touches prompts/**  ──►  scripts/run_eval.sh               │
│                                    │                           │
│                                    ▼                           │
│                          evalci run (CLI)                       │
│                                    │                           │
└────────────────────────────────────┼────────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
     ┌────────────────┐   ┌──────────────────┐   ┌────────────────────┐
     │  EvalRunner    │   │   Ollama Judge   │   │ SemanticSimilarity │
     │  (asyncio,     │   │  (mistral/any    │   │ (sentence-         │
     │   semaphore)   │   │   local model)   │   │  transformers,     │
     └───────┬────────┘   └─────────┬────────┘   │  no API)           │
             │                      │            └────────────────────┘
             │            ┌─────────┴──────────┐
             │            │  Metrics           │
             │            │  ├ AnswerRelevance  │
             │            │  ├ Faithfulness     │
             │            │  │  (2-step: decomp │
             │            │  │   + verify)      │
             │            │  └ SemanticSim      │
             │            └────────────────────┘
             │
     ┌───────▼────────────┐
     │  SQLite (async)    │ ◄── stores run history, metric scores,
     │  EvalRun           │     sample-level results
     │  MetricScore       │
     │  SampleResult      │
     └───────┬────────────┘
             │
     ┌───────▼────────────┐        ┌──────────────────────┐
     │  FastAPI Backend   │◄──────►│  React Dashboard     │
     │  /runs             │        │  ├ RunsTable          │
     │  /metrics/trend    │        │  ├ MetricTrendChart   │
     │  /metrics/latest   │        │  ├ RunDetail          │
     │  /config           │        │  └ ThresholdEditor    │
     └────────────────────┘        └──────────────────────┘
```

---

## Quick Start (5 steps)

### 1. Clone and install

```bash
git clone https://github.com/your-org/evalci
cd evalci
pip install poetry
poetry install
```

### 2. Pull the Ollama judge model

```bash
# Install Ollama: https://ollama.ai
ollama pull mistral
```

### 3. Add EvalCI to your repo

Copy the key files to your target repository:

```bash
# In your target repo:
cp path/to/evalci/evalci.yaml .
cp path/to/evalci/.github/workflows/prompt-regression.yml .github/workflows/
mkdir -p example/prompts
```

Edit `evalci.yaml` to point at your prompt directory and dataset.

### 4. Create your golden dataset

```bash
evalci init
# Edit example/golden_dataset.json with your real queries and expected answers
```

### 5. Push a PR touching a prompt file

```bash
# Edit a prompt template
echo "# improved" >> example/prompts/rag_answer.txt
git add -A && git commit -m "improve RAG prompt clarity"
git push origin feature/better-rag-prompt
# Open a PR — EvalCI fires automatically
```

---

## How to Write a Golden Dataset

The golden dataset is a JSON array of evaluation triples. Each entry tests one (query, context) pair against an expected answer:

```json
[
  {
    "query": "What is the default API timeout?",
    "context": "The API has a configurable timeout defaulting to 30 seconds. Set EVALCI_TIMEOUT to override.",
    "expected_answer": "The default API timeout is 30 seconds, configurable via EVALCI_TIMEOUT."
  }
]
```

**Tips for high-quality golden datasets:**

- Include **edge cases**: queries where the context is partially irrelevant, where synthesis across multiple sentences is required, and where the model is tempted to hallucinate beyond the context.
- Aim for **10–50 samples** minimum. More samples reduce noise from judge variability.
- The `expected_answer` should reflect what a *correct, grounded* answer looks like — not necessarily a verbatim extraction.
- Update the dataset when your product knowledge changes.

---

## Configuration Reference (`evalci.yaml`)

```yaml
ollama_url: http://localhost:11434   # Ollama endpoint
judge_model: mistral                 # Any model available in Ollama
dataset_path: example/golden_dataset.json
prompt_dirs:
  - example/prompts                  # Directories to watch for prompt changes
enabled_metrics:
  - answer_relevance
  - faithfulness
  - semantic_similarity
thresholds:
  answer_relevance: 0.70             # Minimum passing score (0.0–1.0)
  faithfulness: 0.75
  semantic_similarity: 0.65
regression:
  allowed_delta: 0.05                # Max score drop from baseline before blocking
  block_on_regression: true
max_concurrent_evals: 5              # Parallel sample evaluations
judge_timeout_seconds: 25
```

---

## CLI Reference

```bash
# Run evaluation locally
evalci run --config evalci.yaml --dataset example/golden_dataset.json

# Run against a specific prompt
evalci run --prompt example/prompts/rag_answer.txt

# Start the API + dashboard
evalci serve

# Print a report for a specific run
evalci report --run-id 42

# Compare two runs side-by-side
evalci compare --run-a 41 --run-b 42

# Scaffold evalci.yaml and example dataset in the current repo
evalci init
```

---

## GitHub Actions Setup

The workflow at `.github/workflows/prompt-regression.yml` requires no manual setup beyond:

1. Ensure your repo has the `evalci.yaml` and `example/golden_dataset.json` files.
2. The workflow starts an Ollama Docker container automatically and pulls `mistral`.
3. GitHub's `GITHUB_TOKEN` is used automatically to post PR comments — no secrets needed.

**Optional environment variables** (set in repo Settings → Secrets and variables → Actions):

| Variable | Default | Purpose |
|---|---|---|
| `EVALCI_OLLAMA_URL` | `http://localhost:11434` | Override Ollama endpoint |
| `EVALCI_CONFIG_PATH` | `evalci.yaml` | Override config location |
| `EVALCI_DATASET_PATH` | `example/golden_dataset.json` | Override dataset location |

---

## How It Works Internally

### Judge Prompts

Each metric sends a carefully crafted prompt to the Ollama judge requesting a **JSON-only response** with a score (0.0–1.0) and reasoning string. The `answer_relevance` prompt asks: *"Given this question, how relevant is this answer?"* The parser uses JSON extraction with a regex fallback to handle noisy model outputs.

### Two-Step Faithfulness

Faithfulness uses two sequential judge calls:
1. **Decomposition**: *"Break this answer into atomic factual claims."* → `["claim 1", "claim 2", ...]`
2. **Verification**: For each claim: *"Is this claim supported by the context?"* → `{"supported": true/false}`

Score = verified claims / total claims. This two-step approach is significantly more reliable than asking the model to score faithfulness in a single pass, because it forces explicit grounding reasoning per claim.

### Semaphore Concurrency

The runner uses `asyncio.Semaphore(max_concurrent_evals)` to evaluate samples in parallel while respecting rate limits. With `max_concurrent_evals: 5`, up to 5 sample evaluations run simultaneously, each running all metrics concurrently via `asyncio.gather`.

### Regression Detection

`RegressionGuard.check()` applies two independent tests:
1. **Absolute threshold**: `current_score < threshold` → hard floor, always enforced
2. **Relative regression**: `current_score < baseline_score - allowed_delta` → catches silent degradation even above the threshold floor

---

## Roadmap

- [ ] Support for custom metric plugins via Python entry points
- [ ] Baseline pinning (snapshot a specific run as the reference baseline)
- [ ] OpenAI / Anthropic judge backends (optional, paid)
- [ ] Slack/Discord webhook notifications
- [ ] Multi-prompt comparison within a single run
- [ ] Dataset versioning and drift detection
- [ ] RAGAS metric compatibility layer

---

## Contributing

1. Fork the repo and create a feature branch
2. Install dev dependencies: `poetry install`
3. Run tests: `pytest tests/ -v`
4. Ensure `mypy` passes: `mypy backend/ cli/`
5. Open a PR — EvalCI will evaluate itself

All contributions welcome. Please open an issue before implementing large changes.

---

## License

MIT. Use freely, self-host anywhere.

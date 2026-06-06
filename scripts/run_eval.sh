set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

CONFIG_PATH="${EVALCI_CONFIG_PATH:-evalci.yaml}"
DATASET_PATH="${EVALCI_DATASET_PATH:-example/golden_dataset.json}"
OUTPUT_DIR="${EVALCI_OUTPUT_DIR:-.}"

echo "=============================================="
echo " EvalCI — Prompt Regression Evaluation"
echo "=============================================="
echo "Config:  ${CONFIG_PATH}"
echo "Dataset: ${DATASET_PATH}"
echo "Output:  ${OUTPUT_DIR}"
echo ""

mkdir -p "${OUTPUT_DIR}"

CHANGED_FILES=$(git diff --name-only "origin/main...HEAD" -- "*.txt" "*.md" "*.jinja2" 2>/dev/null || echo "")

if [ -n "${CHANGED_FILES}" ]; then
    echo "Changed prompt files detected:"
    echo "${CHANGED_FILES}"
    PROMPT_ARG="${CHANGED_FILES// /,}"
else
    echo "No specific prompt files changed. Running full evaluation."
    PROMPT_ARG=""
fi

poetry run python3 - << PYEOF
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "${REPO_ROOT}")

from backend.config import Settings
from backend.runner import EvalRunner, EvalSample, RunMetadata
from backend.metrics.regression_guard import RegressionGuard
from backend.utils.report import write_reports
from backend.database import init_db, AsyncSessionLocal

async def main():
    cfg = Settings.from_yaml("${CONFIG_PATH}")
    
    with open("${DATASET_PATH}") as f:
        samples_data = json.load(f)
    
    samples = [
        EvalSample(
            query=s["query"],
            context=s["context"],
            expected_answer=s["expected_answer"],
        )
        for s in samples_data
    ]

    prompt_arg = "${PROMPT_ARG}".strip()
    if prompt_arg:
        prompt_files = [p for p in prompt_arg.split(",") if Path(p).exists()]
    else:
        from backend.utils.diff_detector import get_all_prompt_files
        prompt_files = get_all_prompt_files(cfg.prompt_dirs)

    if not prompt_files:
        print("No prompt files found. Exiting.")
        sys.exit(1)

    await init_db()
    exit_code = 0

    for prompt_file in prompt_files:
        print(f"Evaluating: {prompt_file}")
        prompt_template = Path(prompt_file).read_text()

        metadata = RunMetadata(
            prompt_file=prompt_file,
            commit_sha=os.environ.get("GITHUB_SHA"),
            pr_number=os.environ.get("GITHUB_PR_NUMBER"),
        )

        async with AsyncSessionLocal() as session:
            runner = EvalRunner(settings=cfg, session=session)
            result = await runner.run(
                dataset=samples,
                prompt_template=prompt_template,
                run_metadata=metadata,
            )

        print(f"\nResults for {prompt_file}:")
        for metric, score in result.aggregate_scores.items():
            threshold = cfg.thresholds.get(metric, 0.7)
            passed = result.threshold_results.get(metric, False)
            status = "PASS" if passed else "FAIL"
            print(f"  {metric}: {score:.4f} (threshold: {threshold}) [{status}]")

        guard = RegressionGuard(default_allowed_delta=cfg.regression_allowed_delta)
        regression_report = guard.check(
            current_scores=result.aggregate_scores,
            baseline_scores={},
            thresholds=cfg.thresholds,
        )

        write_reports(result, "${OUTPUT_DIR}", regression_report)

        if result.status != "passed":
            exit_code = 1

    sys.exit(exit_code)

asyncio.run(main())
PYEOF

EVAL_EXIT_CODE=$?

echo ""
echo "=============================================="
if [ "${EVAL_EXIT_CODE}" -eq 0 ]; then
    echo " EvalCI PASSED"
else
    echo " EvalCI FAILED"
fi
echo "=============================================="

exit "${EVAL_EXIT_CODE}"

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
echo "Config:   ${CONFIG_PATH}"
echo "Dataset:  ${DATASET_PATH}"
echo "Output:   ${OUTPUT_DIR}"
echo ""

# Detect changed prompt files
CHANGED_FILES=$(git diff --name-only "origin/main...HEAD" -- "*.txt" "*.md" "*.jinja2" 2>/dev/null || echo "")
if [ -z "${CHANGED_FILES}" ]; then
    echo "No prompt files changed. Running full evaluation against all prompts."
fi

# Ensure the database directory exists
mkdir -p "${OUTPUT_DIR}"

# Run the evaluation via the CLI
python -m cli.evalci run \
    --config "${CONFIG_PATH}" \
    --dataset "${DATASET_PATH}" \
    --output "${OUTPUT_DIR}"

EVAL_EXIT_CODE=$?

echo ""
echo "=============================================="
if [ "${EVAL_EXIT_CODE}" -eq 0 ]; then
    echo " ✅ Evaluation PASSED"
else
    echo " ❌ Evaluation FAILED — metrics regressed or thresholds not met"
fi
echo "=============================================="

# Always exit with the evaluation exit code so CI can block the PR
exit "${EVAL_EXIT_CODE}"

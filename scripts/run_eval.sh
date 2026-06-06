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

# Detect changed prompt files and pass them explicitly if found
CHANGED_FILES=$(git diff --name-only "origin/main...HEAD" -- "*.txt" "*.md" "*.jinja2" 2>/dev/null || echo "")

if [ -n "${CHANGED_FILES}" ]; then
    echo "Changed prompt files detected:"
    echo "${CHANGED_FILES}"
    echo ""
    # Run against each changed file individually
    for PROMPT_FILE in ${CHANGED_FILES}; do
        if [ -f "${PROMPT_FILE}" ]; then
            echo "Evaluating: ${PROMPT_FILE}"
            python -m cli.evalci run \
                --config "${CONFIG_PATH}" \
                --dataset "${DATASET_PATH}" \
                --output "${OUTPUT_DIR}" \
                --prompt "${PROMPT_FILE}"
        fi
    done
else
    echo "No specific prompt files changed. Running full evaluation."
    python -m cli.evalci run \
        --config "${CONFIG_PATH}" \
        --dataset "${DATASET_PATH}" \
        --output "${OUTPUT_DIR}"
fi

EVAL_EXIT_CODE=$?

echo ""
echo "=============================================="
if [ "${EVAL_EXIT_CODE}" -eq 0 ]; then
    echo " EvalCI PASSED"
else
    echo " EvalCI FAILED — metrics regressed or thresholds not met"
fi
echo "=============================================="

exit "${EVAL_EXIT_CODE}"

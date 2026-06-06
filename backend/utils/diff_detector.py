# backend/utils/diff_detector.py
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".jinja2", ".jinja", ".j2"}


def get_changed_prompt_files(
    prompt_dirs: list[str],
    base_ref: str = "origin/main",
    head_ref: str = "HEAD",
) -> list[str]:
    """
    Returns a list of changed prompt files in the current PR diff.
    Filters to files under the configured prompt_dirs with supported extensions.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.CalledProcessError as exc:
        logger.error("git diff failed: %s\nstderr: %s", exc, exc.stderr)
        return []
    except FileNotFoundError:
        logger.error("git not found in PATH")
        return []

    prompt_dir_paths = [Path(d) for d in prompt_dirs]
    matched: list[str] = []

    for filepath in changed_files:
        p = Path(filepath)
        if p.suffix not in SUPPORTED_EXTENSIONS:
            continue
        for prompt_dir in prompt_dir_paths:
            try:
                p.relative_to(prompt_dir)
                matched.append(filepath)
                break
            except ValueError:
                # Not under this prompt_dir
                continue

    logger.info(
        "Found %d changed prompt file(s) out of %d total changed files.",
        len(matched),
        len(changed_files),
    )
    return matched


def get_all_prompt_files(prompt_dirs: list[str]) -> list[str]:
    """Returns all prompt files in the configured directories."""
    result: list[str] = []
    for d in prompt_dirs:
        p = Path(d)
        if not p.exists():
            logger.warning("Prompt directory does not exist: %s", d)
            continue
        for ext in SUPPORTED_EXTENSIONS:
            result.extend(str(f) for f in p.rglob(f"*{ext}"))
    return sorted(result)

# cli/evalci.py
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

app = typer.Typer(
    name="evalci",
    help="EvalCI — Prompt Regression CI. pytest for LLM prompts.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def _load_settings(config: str) -> "Settings":
    from backend.config import Settings
    return Settings.from_yaml(config)


def _load_dataset(dataset_path: str) -> list[dict]:
    p = Path(dataset_path)
    if not p.exists():
        console.print(f"[red]Dataset not found: {dataset_path}[/red]")
        raise typer.Exit(1)
    with open(p) as f:
        return json.load(f)


def _load_prompt(prompt_path: str) -> str:
    p = Path(prompt_path)
    if not p.exists():
        console.print(f"[red]Prompt file not found: {prompt_path}[/red]")
        raise typer.Exit(1)
    return p.read_text()


@app.command()
def run(
    config: str = typer.Option("evalci.yaml", "--config", "-c", help="Path to evalci.yaml"),
    dataset: Optional[str] = typer.Option(None, "--dataset", "-d", help="Path to golden dataset JSON"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Path to prompt template file"),
    output_dir: str = typer.Option(".", "--output", "-o", help="Output directory for reports"),
):
    """Run prompt evaluation locally against a golden dataset."""
    console.print(Panel("[bold cyan]EvalCI — Running Prompt Evaluation[/bold cyan]"))

    cfg = _load_settings(config)
    dataset_path = dataset or cfg.dataset_path
    samples_data = _load_dataset(dataset_path)

    if prompt:
        prompt_paths = [prompt]
    else:
        from backend.utils.diff_detector import get_all_prompt_files
        prompt_paths = get_all_prompt_files(cfg.prompt_dirs)
        if not prompt_paths:
            console.print("[yellow]No prompt files found. Specify --prompt or configure prompt_dirs.[/yellow]")
            raise typer.Exit(1)

    console.print(f"[green]Found {len(samples_data)} samples, {len(prompt_paths)} prompt(s)[/green]")

    async def _run_all():
        from backend.database import init_db, AsyncSessionLocal
        from backend.runner import EvalRunner, EvalSample, RunMetadata
        from backend.metrics.regression_guard import RegressionGuard
        from backend.utils.report import write_reports

        await init_db()
        exit_code = 0

        for prompt_file in prompt_paths:
            console.print(f"\n[bold]Evaluating: {prompt_file}[/bold]")
            prompt_template = _load_prompt(prompt_file)
            samples = [
                EvalSample(
                    query=s["query"],
                    context=s["context"],
                    expected_answer=s["expected_answer"],
                )
                for s in samples_data
            ]
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

            table = Table(title=f"Results — {Path(prompt_file).name}")
            table.add_column("Metric", style="cyan")
            table.add_column("Score", style="white")
            table.add_column("Threshold", style="white")
            table.add_column("Status", style="bold")

            for metric, score in result.aggregate_scores.items():
                threshold = cfg.thresholds.get(metric, 0.7)
                passed = result.threshold_results.get(metric, False)
                status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
                table.add_row(metric, f"{score:.4f}", f"{threshold:.2f}", status)

            console.print(table)

            guard = RegressionGuard(default_allowed_delta=cfg.regression_allowed_delta)
            regression_report = guard.check(
                current_scores=result.aggregate_scores,
                baseline_scores={},
                thresholds=cfg.thresholds,
            )

            json_path, md_path = write_reports(result, output_dir, regression_report)
            console.print(f"\n[dim]Reports written: {json_path}, {md_path}[/dim]")

            if result.status != "passed":
                exit_code = 1
                console.print(f"[red]Run FAILED — status: {result.status}[/red]")

        return exit_code

    code = asyncio.run(_run_all())
    raise typer.Exit(code)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Port"),
):
    """Start the EvalCI FastAPI backend server."""
    console.print(Panel(f"[bold cyan]EvalCI API Server — http://{host}:{port}[/bold cyan]"))
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


@app.command()
def report(
    run_id: int = typer.Argument(..., help="Run ID to print report for"),
    config: str = typer.Option("evalci.yaml", "--config", "-c"),
):
    """Print a rich-formatted report for a specific run to the terminal."""
    async def _get_report():
        from backend.database import init_db, AsyncSessionLocal
        from backend.models import EvalRun
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        await init_db()
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(EvalRun)
                .where(EvalRun.id == run_id)
                .options(
                    selectinload(EvalRun.metric_scores),
                    selectinload(EvalRun.sample_results),
                )
            )
            return result.scalar_one_or_none()

    run_obj = asyncio.run(_get_report())
    if run_obj is None:
        console.print(f"[red]Run {run_id} not found.[/red]")
        raise typer.Exit(1)

    console.print(Panel(f"[bold]Run #{run_obj.id} — {run_obj.run_uuid[:8]}[/bold]"))

    info_table = Table(show_header=False)
    info_table.add_row("Prompt", run_obj.prompt_file)
    info_table.add_row("Status", run_obj.status.upper())
    info_table.add_row("Commit", run_obj.commit_sha or "N/A")
    info_table.add_row("PR", run_obj.pr_number or "N/A")
    info_table.add_row("Created", str(run_obj.created_at))
    info_table.add_row("Samples", str(run_obj.total_samples))
    console.print(info_table)

    if run_obj.metric_scores:
        scores_table = Table(title="Metric Scores")
        scores_table.add_column("Metric", style="cyan")
        scores_table.add_column("Score")
        scores_table.add_column("Threshold")
        scores_table.add_column("Pass/Fail", style="bold")
        for ms in run_obj.metric_scores:
            icon = "[green]✅ PASS[/green]" if ms.passed else "[red]❌ FAIL[/red]"
            scores_table.add_row(ms.metric_name, f"{ms.score:.4f}", f"{ms.threshold:.2f}", icon)
        console.print(scores_table)


@app.command()
def compare(
    run_a: int = typer.Option(..., "--run-a", help="First run ID"),
    run_b: int = typer.Option(..., "--run-b", help="Second run ID"),
):
    """Side-by-side metric comparison of two runs."""
    async def _compare():
        from backend.database import init_db, AsyncSessionLocal
        from backend.models import EvalRun
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        await init_db()
        async with AsyncSessionLocal() as session:
            async def load(rid):
                r = await session.execute(
                    select(EvalRun).where(EvalRun.id == rid)
                    .options(selectinload(EvalRun.metric_scores))
                )
                return r.scalar_one_or_none()

            return await load(run_a), await load(run_b)

    a, b = asyncio.run(_compare())
    if a is None:
        console.print(f"[red]Run {run_a} not found[/red]")
        raise typer.Exit(1)
    if b is None:
        console.print(f"[red]Run {run_b} not found[/red]")
        raise typer.Exit(1)

    scores_a = {ms.metric_name: ms.score for ms in a.metric_scores}
    scores_b = {ms.metric_name: ms.score for ms in b.metric_scores}

    table = Table(title=f"Comparison: Run #{run_a} vs Run #{run_b}")
    table.add_column("Metric", style="cyan")
    table.add_column(f"Run #{run_a}", style="yellow")
    table.add_column(f"Run #{run_b}", style="yellow")
    table.add_column("Delta", style="bold")

    for metric in sorted(set(scores_a) | set(scores_b)):
        a_val = scores_a.get(metric, 0.0)
        b_val = scores_b.get(metric, 0.0)
        delta = b_val - a_val
        delta_str = f"{delta:+.4f}"
        delta_colored = f"[green]{delta_str}[/green]" if delta >= 0 else f"[red]{delta_str}[/red]"
        table.add_row(metric, f"{a_val:.4f}", f"{b_val:.4f}", delta_colored)

    console.print(table)


@app.command()
def init(
    output_dir: str = typer.Argument(".", help="Directory to scaffold evalci files in"),
):
    """Scaffold a new evalci.yaml and example golden dataset in the current repo."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    yaml_path = out / "evalci.yaml"
    if not yaml_path.exists():
        yaml_content = """\
ollama_url: http://localhost:11434
judge_model: mistral
dataset_path: example/golden_dataset.json
prompt_dirs:
  - example/prompts
enabled_metrics:
  - answer_relevance
  - faithfulness
  - semantic_similarity
thresholds:
  answer_relevance: 0.70
  faithfulness: 0.75
  semantic_similarity: 0.65
regression:
  allowed_delta: 0.05
  block_on_regression: true
max_concurrent_evals: 5
judge_timeout_seconds: 25
"""
        yaml_path.write_text(yaml_content)
        console.print(f"[green]Created {yaml_path}[/green]")
    else:
        console.print(f"[yellow]Skipped {yaml_path} (already exists)[/yellow]")

    dataset_path = out / "example" / "golden_dataset.json"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    if not dataset_path.exists():
        example_dataset = [
            {
                "query": "What is the default timeout for API requests?",
                "context": "The EvalCI API has a default request timeout of 30 seconds. This can be configured via the EVALCI_TIMEOUT environment variable.",
                "expected_answer": "The default timeout for API requests is 30 seconds, configurable via EVALCI_TIMEOUT."
            }
        ]
        with open(dataset_path, "w") as f:
            json.dump(example_dataset, f, indent=2)
        console.print(f"[green]Created {dataset_path}[/green]")

    console.print("\n[bold green]✅ EvalCI initialized![/bold green]")
    console.print("Next steps:")
    console.print("  1. Edit [cyan]evalci.yaml[/cyan] to configure your settings")
    console.print("  2. Add your prompt templates to the prompts directory")
    console.print("  3. Build your golden dataset in [cyan]example/golden_dataset.json[/cyan]")
    console.print("  4. Run [cyan]evalci run[/cyan] to evaluate locally")


if __name__ == "__main__":
    app()

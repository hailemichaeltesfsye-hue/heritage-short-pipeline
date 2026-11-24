"""CLI entrypoint for running the heritage-short-pipeline across all stages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from agents.graph import create_pipeline_graph
from pipeline.assemble import assemble_full_dual_aspect_pipeline
from pipeline.keyframes import generate_all_keyframes
from pipeline.logger import get_pipeline_metrics
from pipeline.music import prepare_score
from pipeline.narration import generate_shot_narration
from pipeline.script import validate_storyboard
from pipeline.shots import process_shot_motion

app = typer.Typer(help="AI Filmmaking Pipeline: The Heritage Short")
console = Console()


@app.command()
def run(
    stage: str = typer.Option("all", "--stage", help="Stage to run: all, keyframes, shots, music, assemble, narration"),
    storyboard: Path = typer.Option(Path("storyboard.json"), "--storyboard", "-s", help="Path to storyboard JSON"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in deterministic dry-run mode"),
    hitl: bool = typer.Option(False, "--hitl", help="Enable Human-In-The-Loop approval checkpoints"),
    shot: Optional[str] = typer.Option(None, "--shot", help="Target a single shot_id"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass cache and force regeneration"),
):
    """Execute the multi-agent pipeline to generate keyframes, audio, shots, and final dual-aspect cut."""
    console.print(f"[bold cyan]AI Filmmaking Pipeline: The Heritage Short[/bold cyan]")
    console.print(f"Stage: [bold yellow]{stage}[/bold yellow] | Storyboard: [green]{storyboard}[/green] | Dry-run: {dry_run}")

    if not storyboard.exists():
        console.print(f"[red]Storyboard file {storyboard} does not exist[/red]")
        raise typer.Exit(code=1)

    with open(storyboard, "r", encoding="utf-8") as f:
        storyboard_data = json.load(f)

    if stage in ("all", "graph"):
        graph = create_pipeline_graph()
        initial_state = {
            "storyboard_path": str(storyboard),
            "storyboard_data": storyboard_data,
            "dry_run": dry_run,
            "hitl": hitl,
            "target_shot_id": shot,
            "force": force,
            "stage": stage,
            "trace_id": "cli-run",
            "is_valid_schema": False,
            "safety_passed": False,
            "shot_hashes": {},
            "keyframes": {},
            "audio_files": {},
            "shots_video": {},
            "score_path": None,
            "radio_cut_path": None,
            "final_16x9_path": None,
            "final_9x16_path": None,
            "errors": [],
            "retry_counts": {},
            "step_status": {},
            "hitl_paused": False,
        }

        result = graph.invoke(initial_state)
        if result.get("errors"):
            console.print("[bold red]Pipeline encountered errors:[/bold red]")
            for err in result["errors"]:
                console.print(f" - [red]{err}[/red]")
            raise typer.Exit(code=1)

        console.print("[bold green]Pipeline completed successfully![/bold green]")
        if result.get("final_16x9_path"):
            console.print(f"16:9 Master: [bold yellow]{result['final_16x9_path']}[/bold yellow]")
        if result.get("final_9x16_path"):
            console.print(f"9:16 Vertical: [bold yellow]{result['final_9x16_path']}[/bold yellow]")
        return

    # Granular individual stages
    if stage == "keyframes":
        generate_all_keyframes(storyboard_data, dry_run=dry_run, force=force)
        console.print("[bold green]Keyframes stage complete: outputs/keyframes/[/bold green]")

    elif stage == "narration":
        for s in storyboard_data.get("shots", []):
            if shot and s["shot_id"] != shot:
                continue
            generate_shot_narration(s, dry_run=dry_run)
        console.print("[bold green]Narration stage complete: outputs/narration/[/bold green]")

    elif stage == "music":
        prepare_score(float(storyboard_data.get("total_duration_sec", 74.0)))
        console.print("[bold green]Music stage complete: outputs/music/score_normalized.wav[/bold green]")

    elif stage == "assemble":
        final_16x9, final_9x16 = assemble_full_dual_aspect_pipeline(storyboard_data, dry_run=dry_run)
        console.print(f"[bold green]Assembly complete: {final_16x9} & {final_9x16}[/bold green]")

    else:
        console.print(f"[red]Unknown stage '{stage}'[/red]")
        raise typer.Exit(code=1)


@app.command()
def validate(
    storyboard: Path = typer.Option(Path("storyboard.json"), "--storyboard", "-s"),
    schema: Path = typer.Option(Path("schema/storyboard.schema.json"), "--schema"),
):
    """Validate storyboard against schema and director rules."""
    is_valid, errors, data = validate_storyboard(storyboard, schema)
    if not is_valid:
        console.print("[bold red]Storyboard validation failed:[/bold red]")
        for err in errors:
            console.print(f" - {err}")
        raise typer.Exit(code=1)
    console.print(f"[bold green]Storyboard '{data.get('title')}' is 100% valid![/bold green]")


@app.command()
def metrics(log_path: Path = typer.Option(Path("runs.jsonl"), "--log", "-l")):
    """Display aggregated pipeline metrics and telemetry."""
    m = get_pipeline_metrics(log_path)
    table = Table(title="Pipeline Telemetry & Run Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Runs", str(m["total_runs"]))
    table.add_row("Total Latency (ms)", f"{m['total_latency_ms']:.2f}")
    table.add_row("Total Cost (USD)", f"${m['total_cost_usd']:.6f}")
    table.add_row("Cache Hits", str(m["cache_hits"]))
    table.add_row("Cache Misses", str(m["cache_misses"]))
    table.add_row("Cache Hit Ratio", f"{m['cache_hit_ratio'] * 100:.1f}%")
    table.add_row("Failures Handled", str(m["failures"]))

    console.print(table)


if __name__ == "__main__":
    app()

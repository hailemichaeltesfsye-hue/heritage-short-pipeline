"""Custom MCP Server for heritage-short-pipeline using python mcp SDK.

Exposes tools:
- validate_storyboard: validates storyboard.json against schema and director rules.
- regenerate_shot: invalidates cache for a shot_id and re-runs the pipeline.
- get_pipeline_metrics: returns aggregate latency, cost, and cache hit metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from mcp.server.mcpserver import MCPServer
from pipeline.cache import invalidate_shot
from pipeline.logger import get_pipeline_metrics as read_pipeline_metrics
from pipeline.script import validate_storyboard as run_validate_storyboard
from pipeline.shots import process_shot

server = MCPServer(
    name="heritage-pipeline-mcp",
    instructions="Heritage Short Multi-Agent Filmmaking Pipeline Server",
)


@server.tool()
def validate_storyboard(storyboard_path: str = "storyboard.json") -> Dict[str, Any]:
    """Validate storyboard against strict schema and Director rules.

    Args:
        storyboard_path: Relative or absolute path to the storyboard JSON file.
    """
    sb_path = Path(storyboard_path)
    schema_path = Path("schema/storyboard.schema.json")
    is_valid, errors, data = run_validate_storyboard(sb_path, schema_path)
    return {
        "is_valid": is_valid,
        "errors": errors,
        "title": data.get("title", ""),
        "total_shots": len(data.get("shots", [])),
        "total_duration_sec": data.get("total_duration_sec", 0.0),
    }


@server.tool()
def regenerate_shot(shot_id: str, storyboard_path: str = "storyboard.json", dry_run: bool = True) -> Dict[str, Any]:
    """Invalidate cache for a single shot and regenerate its narration artifact.

    Args:
        shot_id: The shot identifier (e.g., 'shot_01', 'shot_04').
        storyboard_path: Path to storyboard file.
        dry_run: Whether to run in deterministic offline reference mode.
    """
    sb_path = Path(storyboard_path)
    if not sb_path.exists():
        return {"success": False, "error": f"Storyboard not found at {storyboard_path}"}

    with open(sb_path, "r", encoding="utf-8") as f:
        storyboard_data = json.load(f)

    target_shot = None
    for s in storyboard_data.get("shots", []):
        if s.get("shot_id") == shot_id:
            target_shot = s
            break

    if not target_shot:
        return {"success": False, "error": f"Shot {shot_id} not found in {storyboard_path}"}

    # Invalidate cache
    invalidate_shot(shot_id)

    # Re-run shot processing
    style_block = storyboard_data.get("style_block", {})
    success, audio_path, was_cached = process_shot(
        shot=target_shot,
        style_block=style_block,
        dry_run=dry_run,
        force=True,
    )

    return {
        "success": success,
        "shot_id": shot_id,
        "audio_path": str(audio_path),
        "was_cached": was_cached,
        "duration_sec": target_shot.get("duration_sec"),
    }


@server.tool()
def get_pipeline_metrics(log_path: str = "runs.jsonl") -> Dict[str, Any]:
    """Retrieve summarized latency, cost, and cache hit metrics from runs.jsonl.

    Args:
        log_path: Path to the structured runs.jsonl log file.
    """
    return read_pipeline_metrics(Path(log_path))


def main():
    """Run the MCP server over stdio transport."""
    server.run()


if __name__ == "__main__":
    main()

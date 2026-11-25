"""Video Editor Agent for heritage-short-pipeline.

Runs deterministic FFmpeg commands to produce outputs/final_16x9.mp4 and outputs/final_9x16.mp4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from agents.state import PipelineState
from pipeline.assemble import assemble_full_dual_aspect_pipeline
from pipeline.logger import log_run


def video_editor_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node compiling full dual-aspect video with narration, score, and subtitles."""
    data = state.get("storyboard_data", {})
    dry_run = state.get("dry_run", False)
    language = str(state.get("language", "en") or "en").lower()
    trace_id = state.get("trace_id")
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    try:
        final_16x9, final_9x16 = assemble_full_dual_aspect_pipeline(
            storyboard=data,
            dry_run=dry_run,
            trace_id=trace_id,
            language=language,
        )
        step_status["video_editor"] = "passed"
        log_run(
            agent="VideoEditorAgent",
            stage="assembly_dual_aspect",
            provider="ffmpeg",
            model="ffmpeg-dual-aspect-master",
            parameters={"final_16x9": str(final_16x9), "final_9x16": str(final_9x16)},
            status="success",
            trace_id=trace_id,
        )
        return {
            "radio_cut_path": str(final_16x9),
            "final_16x9_path": str(final_16x9),
            "final_9x16_path": str(final_9x16),
            "step_status": step_status,
        }
    except Exception as e:
        errors.append(f"VideoEditorAgent failed: {e}")
        step_status["video_editor"] = "failed"
        log_run(
            agent="VideoEditorAgent",
            stage="assembly_dual_aspect",
            provider="ffmpeg",
            model="ffmpeg-dual-aspect-master",
            status="failed",
            error=str(e),
            trace_id=trace_id,
        )
        return {
            "errors": errors,
            "step_status": step_status,
        }

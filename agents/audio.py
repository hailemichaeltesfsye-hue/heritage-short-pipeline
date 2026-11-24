"""Audio Voice Agent for heritage-short-pipeline.

Invokes Gemini 3.8 Flash native AUDIO narration with Edge-TTS Amharic neural fallback.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.state import PipelineState
from pipeline.shots import process_shot


def audio_voice_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node generating or retrieving cached voice narration files."""
    data = state.get("storyboard_data", {})
    style_block = data.get("style_block", {})
    shots = data.get("shots", [])
    target_shot = state.get("target_shot_id")
    dry_run = bool(state.get("dry_run", False))
    force = bool(state.get("force", False))
    trace_id = state.get("trace_id")

    audio_files = dict(state.get("audio_files", {}))
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    failed_any = False
    for shot in shots:
        shot_id = shot["shot_id"]
        if target_shot and shot_id != target_shot:
            continue

        success, audio_path, _ = process_shot(
            shot=shot,
            style_block=style_block,
            dry_run=dry_run,
            force=force,
            trace_id=trace_id,
        )

        if success and audio_path.exists() and audio_path.stat().st_size > 0:
            audio_files[shot_id] = str(audio_path)
        else:
            failed_any = True
            audio_files.pop(shot_id, None)

    step_status["audio_voice"] = "completed" if (len(audio_files) > 0 and not failed_any) else "failed"

    return {
        "audio_files": audio_files,
        "errors": errors,
        "step_status": step_status,
    }

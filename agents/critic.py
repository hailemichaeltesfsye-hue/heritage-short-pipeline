"""Quality Critic Agent (Self-Healing Loop) for heritage-short-pipeline.

Validates generated audio files for non-zero duration and integrity,
triggering up to 3 retries on failed shots before clean fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from agents.state import PipelineState
from pipeline.ffmpeg_utils import get_audio_duration
from pipeline.logger import log_run

MAX_RETRIES = 3


def quality_critic_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node evaluating audio artifacts and coordinating retries."""
    data = state.get("storyboard_data", {})
    shots = data.get("shots", [])
    target_shot = state.get("target_shot_id")
    audio_files = state.get("audio_files", {})
    retry_counts = dict(state.get("retry_counts", {}))
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    failed_shots: List[str] = []

    for shot in shots:
        shot_id = shot["shot_id"]
        if target_shot and shot_id != target_shot:
            continue

        audio_str = audio_files.get(shot_id)
        if not audio_str:
            failed_shots.append(shot_id)
            continue

        audio_path = Path(audio_str)
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            failed_shots.append(shot_id)
            continue

        duration = get_audio_duration(audio_path)
        expected_duration = float(shot.get("duration_sec", 6.0))

        # Check for non-zero audio duration
        if duration <= 0.0:
            failed_shots.append(shot_id)

    # Assess retry counts
    can_retry = False
    for shot_id in failed_shots:
        count = retry_counts.get(shot_id, 0)
        if count < MAX_RETRIES:
            retry_counts[shot_id] = count + 1
            can_retry = True
            log_run(
                agent="QualityCriticAgent",
                stage="quality_check",
                shot_id=shot_id,
                provider="local",
                model="quality-critic",
                status="retry_requested",
                error=f"Shot {shot_id} failed quality check (retry {retry_counts[shot_id]}/{MAX_RETRIES})",
                trace_id=state.get("trace_id"),
            )
        else:
            errors.append(f"Shot {shot_id} failed quality critic after {MAX_RETRIES} retries")

    all_passed = len(failed_shots) == 0 or (not can_retry and len(errors) == 0)
    step_status["quality_critic"] = "passed" if all_passed else ("retry" if can_retry else "failed")

    return {
        "retry_counts": retry_counts,
        "errors": errors,
        "step_status": step_status,
    }


def should_retry_audio(state: PipelineState) -> str:
    """Conditional edge decision function: route back to audio or proceed to editor."""
    status = state.get("step_status", {}).get("quality_critic")
    if status == "retry":
        return "audio_voice"
    return "video_editor"

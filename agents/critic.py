"""Quality Critic Agent (Self-Healing Loop) for heritage-short-pipeline.

Validates generated audio files for non-zero duration, file integrity, and
audible WAV RMS amplitude (failing silent narration when dry_run=False),
triggering up to 3 retries on failed shots.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from agents.state import PipelineState
from pipeline.cache import invalidate_shot
from pipeline.ffmpeg_utils import compute_wav_rms, get_audio_duration
from pipeline.logger import log_run

MAX_RETRIES = 3
MIN_WAV_RMS = 0.001


def quality_critic_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node evaluating audio duration and RMS amplitude, coordinating retries."""
    data = state.get("storyboard_data", {})
    shots = data.get("shots", [])
    target_shot = state.get("target_shot_id")
    dry_run = bool(state.get("dry_run", False))
    audio_files = state.get("audio_files", {})
    retry_counts = dict(state.get("retry_counts", {}))
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    failed_shots: List[tuple[str, str]] = []

    for shot in shots:
        shot_id = shot["shot_id"]
        if target_shot and shot_id != target_shot:
            continue

        audio_str = audio_files.get(shot_id)
        if not audio_str:
            failed_shots.append((shot_id, "missing narration file path"))
            continue

        audio_path = Path(audio_str)
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            failed_shots.append((shot_id, "narration WAV missing or empty"))
            continue

        duration = get_audio_duration(audio_path)
        if duration <= 0.1:
            failed_shots.append((shot_id, f"invalid audio duration ({duration:.2f}s)"))
            continue

        if not dry_run:
            rms = compute_wav_rms(audio_path)
            if rms < MIN_WAV_RMS:
                failed_shots.append(
                    (shot_id, f"silent narration detected (RMS={rms:.6f} < {MIN_WAV_RMS})")
                )

    can_retry = False
    exhausted = False
    for shot_id, reason in failed_shots:
        count = retry_counts.get(shot_id, 0)
        if count < MAX_RETRIES:
            retry_counts[shot_id] = count + 1
            invalidate_shot(shot_id)
            can_retry = True
            log_run(
                agent="QualityCriticAgent",
                stage="quality_check",
                shot_id=shot_id,
                provider="local",
                model="quality-critic",
                status="retry_requested",
                error=f"Shot {shot_id} failed quality check: {reason} (retry {retry_counts[shot_id]}/{MAX_RETRIES})",
                trace_id=state.get("trace_id"),
            )
        else:
            exhausted = True
            err_msg = f"Shot {shot_id} failed quality critic after {MAX_RETRIES} retries: {reason}"
            if err_msg not in errors:
                errors.append(err_msg)
            log_run(
                agent="QualityCriticAgent",
                stage="quality_check",
                shot_id=shot_id,
                provider="local",
                model="quality-critic",
                status="failed",
                error=err_msg,
                trace_id=state.get("trace_id"),
            )

    if len(failed_shots) == 0:
        step_status["quality_critic"] = "passed"
    elif can_retry and not exhausted:
        step_status["quality_critic"] = "retry"
    else:
        step_status["quality_critic"] = "failed"

    return {
        "retry_counts": retry_counts,
        "errors": errors,
        "step_status": step_status,
    }


def should_retry_audio(state: PipelineState) -> str:
    """Conditional edge router: retry audio, proceed to video editor, or halt on failure."""
    status = state.get("step_status", {}).get("quality_critic")
    if status == "retry":
        return "audio_voice"
    if status == "failed":
        return "end"
    return "video_editor"

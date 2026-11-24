"""Motion shot processing coordination, Kaggle Wan 2.2 conforming, and FFmpeg Ken Burns generator."""

from __future__ import annotations

import os
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple

from pipeline.cache import compute_shot_hash, is_shot_cached, update_shot_cache
from pipeline.ffmpeg_utils import get_audio_duration, resolve_ffmpeg_path, resolve_ffprobe_path, run_ffmpeg
from pipeline.logger import log_run
from pipeline.narration import generate_shot_narration

OUTPUTS_SHOTS_DIR = Path("outputs/shots")
OUTPUTS_CLIPS_RAW_DIR = Path("outputs/clips_raw")


def generate_ken_burns_shot(
    keyframe_path: Path,
    output_shot_path: Path,
    duration_sec: float,
    shot_index: int = 1,
    fps: int = 24,
) -> Path:
    """Generate a smooth, varied-direction Ken Burns motion video from a keyframe via FFmpeg."""
    output_shot_path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(int(duration_sec * fps), 24)

    # Varied camera motion patterns based on shot index
    mode = shot_index % 5
    if mode == 1:
        # Slow cinematic zoom-in to center
        zoom_expr = "min(zoom+0.0012,1.22)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 2:
        # Slow lateral pan left to right
        zoom_expr = "1.15"
        x_expr = f"(iw-iw/zoom)*(on/{total_frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 3:
        # Slow expansive zoom-out
        zoom_expr = "if(lte(zoom,1.0),1.22,max(1.001,zoom-0.0012))"
        x_expr = "iw/2-(ih/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 4:
        # Slow lateral pan right to left
        zoom_expr = "1.15"
        x_expr = f"(iw-iw/zoom)*(1-on/{total_frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        # Slow upward tilt with subtle zoom
        zoom_expr = "min(zoom+0.0010,1.18)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"(ih-ih/zoom)*(1-on/{total_frames})"

    filter_str = (
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s=1920x1080:fps={fps},"
        f"format=yuv420p"
    )

    cmd = [
        "-loop", "1",
        "-i", str(keyframe_path),
        "-vf", filter_str,
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        str(output_shot_path),
    ]

    ret, stdout, stderr = run_ffmpeg(cmd)
    if ret != 0:
        # Fallback to simple static scale if zoompan is unsupported
        cmd_fallback = [
            "-loop", "1",
            "-i", str(keyframe_path),
            "-t", str(duration_sec),
            "-vf", "scale=1920:1080,fps=24,format=yuv420p",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(output_shot_path),
        ]
        run_ffmpeg(cmd_fallback)

    return output_shot_path


def conform_raw_clip(
    raw_clip_path: Path,
    output_shot_path: Path,
    target_duration_sec: float,
    fps: int = 24,
) -> Path:
    """Conform a Kaggle Wan 2.2 raw clip (trim weak start/end and match 1080p 24fps)."""
    output_shot_path.parent.mkdir(parents=True, exist_ok=True)
    # Trim 0.2s head to eliminate draft artifacts, then scale to 1080p
    cmd = [
        "-ss", "0.2",
        "-i", str(raw_clip_path),
        "-t", str(target_duration_sec),
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={fps}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_shot_path),
    ]
    run_ffmpeg(cmd)
    return output_shot_path


def process_shot_motion(
    shot: Dict[str, Any],
    keyframe_path: Path,
    style_block: Dict[str, Any],
    shot_index: int = 1,
    fallback_ken_burns: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, str]:
    """Generate or conform motion shot video for a single shot.

    Returns:
        (success, video_path, provider_used)
    """
    shot_id = shot["shot_id"]
    output_path = OUTPUTS_SHOTS_DIR / f"{shot_id}.mp4"
    duration_sec = float(shot.get("duration_sec", 6.0))
    shot_hash = compute_shot_hash(shot, style_block)

    # Check cache
    if not force and is_shot_cached(shot_id, shot_hash, [output_path]):
        return True, output_path, "cache"

    raw_clip = OUTPUTS_CLIPS_RAW_DIR / f"{shot_id}.mp4"

    start_time = time.time()
    if raw_clip.exists() and raw_clip.stat().st_size > 0 and not fallback_ken_burns:
        # Conform raw Kaggle Wan 2.2 output
        conform_raw_clip(raw_clip, output_path, duration_sec)
        provider = "kaggle_wan22"
        model_name = "wan2.2-i2v-conformed"
    else:
        # Ken Burns smooth motion shot
        generate_ken_burns_shot(
            keyframe_path=keyframe_path,
            output_shot_path=output_path,
            duration_sec=duration_sec,
            shot_index=shot_index,
        )
        provider = "ffmpeg_ken_burns"
        model_name = "ffmpeg-zoompan"

    latency_ms = (time.time() - start_time) * 1000

    if output_path.exists() and output_path.stat().st_size > 0:
        update_shot_cache(
            shot_id=shot_id,
            shot_hash=shot_hash,
            artifacts={"shot_video": str(output_path)},
        )
        log_run(
            agent="VideoEditorAgent",
            stage="motion_shot",
            shot_id=shot_id,
            provider=provider,
            model=model_name,
            parameters={"duration_sec": duration_sec, "shot_index": shot_index},
            seed=shot.get("seed"),
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
            cache_hit=False,
            status="success",
            error="fallback: ken_burns" if provider == "ffmpeg_ken_burns" else None,
            trace_id=trace_id,
        )
        return True, output_path, provider

    return False, output_path, "failed"


def process_shot(
    shot: Dict[str, Any],
    style_block: Dict[str, Any],
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, bool]:
    """Process narration for a single shot (backward compatible helper)."""
    shot_id = shot["shot_id"]
    shot_hash = compute_shot_hash(shot, style_block)
    expected_audio = Path("outputs/narration") / f"{shot_id}.wav"

    if not force and is_shot_cached(shot_id, shot_hash, [expected_audio]):
        log_run(
            agent="AudioVoiceAgent",
            stage="narration",
            shot_id=shot_id,
            provider="cache",
            model="cache-manifest",
            parameters={"shot_hash": shot_hash},
            seed=shot.get("seed"),
            latency_ms=0.5,
            estimated_cost_usd=0.0,
            cache_hit=True,
            status="success",
            trace_id=trace_id,
        )
        return True, expected_audio, True

    success, audio_path, model_used, latency = generate_shot_narration(
        shot=shot,
        dry_run=dry_run,
        trace_id=trace_id,
    )

    if success and audio_path.exists():
        update_shot_cache(
            shot_id=shot_id,
            shot_hash=shot_hash,
            artifacts={"narration": str(audio_path)},
        )
        return True, audio_path, False

    return False, expected_audio, False

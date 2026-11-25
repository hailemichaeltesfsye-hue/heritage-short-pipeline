"""Motion shot processing coordination, Kaggle Wan 2.2 conforming, and FFmpeg Ken Burns generator."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple

from pipeline.cache import compute_shot_hash, is_shot_cached, update_shot_cache
from pipeline.ffmpeg_utils import compute_wav_rms, get_audio_duration, run_ffmpeg
from pipeline.logger import log_run
import pipeline.narration as narration_mod

OUTPUTS_SHOTS_DIR = Path("outputs/shots")
OUTPUTS_CLIPS_RAW_DIR = Path("outputs/clips_raw")
OUTPUTS_NARRATION_DIR = Path("outputs/narration")
MIN_AUDIO_RMS = 0.001


def generate_ken_burns_shot(
    keyframe_path: Path,
    output_shot_path: Path,
    duration_sec: float,
    shot_index: int = 1,
    fps: int = 24,
) -> Path:
    """Generate a smooth, aspect-correct Ken Burns motion video from a keyframe via FFmpeg."""
    if not keyframe_path.exists() or keyframe_path.stat().st_size == 0:
        raise FileNotFoundError(f"Keyframe image missing or empty: {keyframe_path}")

    output_shot_path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(int(round(duration_sec * fps)), 24)

    mode = shot_index % 5
    if mode == 1:
        zoom_expr = "min(zoom+0.0012,1.22)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 2:
        zoom_expr = "1.15"
        x_expr = f"(iw-iw/zoom)*(on/{total_frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 3:
        zoom_expr = "if(lte(zoom,1.0),1.22,max(1.001,zoom-0.0012))"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 4:
        zoom_expr = "1.15"
        x_expr = f"(iw-iw/zoom)*(1-on/{total_frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        zoom_expr = "min(zoom+0.0010,1.18)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"(ih-ih/zoom)*(1-on/{total_frames})"

    # Center-crop input cleanly to 16:9 before zoompan so square 1024x1024 keyframes are never stretched
    filter_str = (
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s=1920x1080:fps={fps},"
        f"format=yuv420p"
    )

    cmd = [
        "-i", str(keyframe_path),
        "-vf", filter_str,
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-preset", "fast",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        str(output_shot_path),
    ]

    ret, _, stderr = run_ffmpeg(cmd)
    if ret != 0:
        cmd_fallback = [
            "-loop", "1",
            "-i", str(keyframe_path),
            "-t", str(duration_sec),
            "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={fps},format=yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(output_shot_path),
        ]
        ret2, _, stderr2 = run_ffmpeg(cmd_fallback)
        if ret2 != 0:
            raise RuntimeError(f"FFmpeg Ken Burns failed ({stderr}); static fallback failed ({stderr2})")

    if not output_shot_path.exists() or output_shot_path.stat().st_size == 0:
        raise RuntimeError(f"Ken Burns output missing at {output_shot_path}")

    return output_shot_path


def conform_raw_clip(
    raw_clip_path: Path,
    output_shot_path: Path,
    target_duration_sec: float,
    fps: int = 24,
) -> Path:
    """Conform a Kaggle Wan 2.2 raw clip (trim weak start and match 1080p 24fps)."""
    if not raw_clip_path.exists() or raw_clip_path.stat().st_size == 0:
        raise FileNotFoundError(f"Raw video clip missing or empty: {raw_clip_path}")

    output_shot_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "-ss", "0.2",
        "-i", str(raw_clip_path),
        "-t", str(target_duration_sec),
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={fps},format=yuv420p",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_shot_path),
    ]
    ret, _, stderr = run_ffmpeg(cmd)
    if ret != 0 or not output_shot_path.exists() or output_shot_path.stat().st_size == 0:
        raise RuntimeError(f"Failed conforming raw clip {raw_clip_path}: {stderr}")
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
    """Generate or conform motion shot video for a single shot."""
    shot_id = shot["shot_id"]
    output_path = OUTPUTS_SHOTS_DIR / f"{shot_id}.mp4"
    duration_sec = float(shot.get("duration_sec", 6.0))
    shot_hash = compute_shot_hash(shot, style_block)

    if not force and is_shot_cached(shot_id, shot_hash, [output_path]):
        return True, output_path, "cache"

    raw_clip = OUTPUTS_CLIPS_RAW_DIR / f"{shot_id}.mp4"

    start_time = time.time()
    if raw_clip.exists() and raw_clip.stat().st_size > 0 and not fallback_ken_burns:
        conform_raw_clip(raw_clip, output_path, duration_sec)
        provider = "kaggle_wan22"
        model_name = "wan2.2-i2v-conformed"
        status = "success"
        err = None
    else:
        generate_ken_burns_shot(
            keyframe_path=keyframe_path,
            output_shot_path=output_path,
            duration_sec=duration_sec,
            shot_index=shot_index,
        )
        provider = "ffmpeg_ken_burns"
        model_name = "ffmpeg-zoompan"
        status = "fallback"
        err = "fallback: ken_burns (no raw Wan 2.2 clip in outputs/clips_raw/)"

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
            status=status,
            error=err,
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
    language: str = "en",
) -> Tuple[bool, Path, bool]:
    """Process narration for a single shot (cache-aware, language-aware)."""
    lang = language.lower()
    shot_id = shot["shot_id"]
    shot_hash = compute_shot_hash(shot, style_block)
    base_dir = narration_mod.OUTPUTS_NARRATION_DIR
    lang_dir = (
        narration_mod.OUTPUTS_NARRATION_EN_DIR
        if lang == "en"
        else narration_mod.OUTPUTS_NARRATION_AM_DIR
    )
    # If caller patched OUTPUTS_NARRATION_DIR without patching EN/AM dirs, derive under OUTPUTS_NARRATION_DIR
    if str(lang_dir).replace("\\", "/") == f"outputs/narration/{lang}" and str(base_dir).replace("\\", "/") != "outputs/narration":
        lang_dir = base_dir / lang
    expected_audio = lang_dir / f"{shot_id}.wav"

    if not force and is_shot_cached(shot_id, shot_hash, [expected_audio]):
        # In live mode, refuse cached silent WAVs
        if dry_run or compute_wav_rms(expected_audio) >= MIN_AUDIO_RMS:
            log_run(
                agent="AudioVoiceAgent",
                stage="narration",
                shot_id=shot_id,
                provider="cache",
                model="cache-manifest",
                parameters={"shot_hash": shot_hash, "language": lang},
                seed=shot.get("seed"),
                latency_ms=0.5,
                estimated_cost_usd=0.0,
                cache_hit=True,
                status="success",
                trace_id=trace_id,
            )
            return True, expected_audio, True

    success, audio_path, _, _ = narration_mod.generate_shot_narration(
        shot=shot,
        output_dir=base_dir,
        dry_run=dry_run,
        trace_id=trace_id,
        language=lang,
    )

    if success and audio_path.exists() and audio_path.stat().st_size > 0:
        if dry_run or compute_wav_rms(audio_path) >= MIN_AUDIO_RMS:
            update_shot_cache(
                shot_id=shot_id,
                shot_hash=shot_hash,
                artifacts={f"narration_{lang}": str(audio_path)},
            )
            return True, audio_path, False

    return False, expected_audio, False

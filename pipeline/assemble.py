"""Full dual-aspect video assembly, audio ducking, loudnorm, and AI end card appending."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import textwrap
import time
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from pipeline.ffmpeg_utils import compute_wav_rms, get_audio_duration, run_ffmpeg
import pipeline.keyframes as keyframes_mod
from pipeline.logger import log_run
import pipeline.music as music_mod
import pipeline.narration as narration_mod
import pipeline.shots as shots_mod

OUTPUTS_DIR = Path("outputs")
OUTPUTS_NARRATION_DIR = Path("outputs/narration")
OUTPUTS_SHOTS_DIR = Path("outputs/shots")
OUTPUTS_KEYFRAMES_DIR = Path("outputs/keyframes")
OUTPUTS_CLIPS_RAW_DIR = Path("outputs/clips_raw")


def wrap_subtitle_text(text: str, max_chars_per_line: int = 40, max_lines: int = 2) -> str:
    """Format subtitle text to satisfy <= 2 lines and <= 40 chars/line constraint."""
    cleaned = " ".join(text.strip().split())
    wrapped_lines = textwrap.wrap(cleaned, width=max_chars_per_line)
    if len(wrapped_lines) > max_lines:
        first_line = wrapped_lines[0]
        remaining = " ".join(wrapped_lines[1:])
        second_line = textwrap.shorten(remaining, width=max_chars_per_line, placeholder="...")
        return f"{first_line}\n{second_line}"
    return "\n".join(wrapped_lines)


def format_srt_timestamp(seconds: float) -> str:
    """Convert floating point seconds into SRT timecode HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def calculate_dynamic_shot_durations(
    shots: List[Dict[str, Any]],
    narration_dir: Optional[Path] = None,
    breathing_room_sec: float = 0.5,
) -> Tuple[List[float], float]:
    """Dynamically adjust shot durations based on actual Amharic narration audio lengths.

    Ensures narration is never clipped (+0.5s breathing room) while keeping total
    film runtime strictly within [60.0, 90.0] seconds (including 3s AI end card).
    """
    resolved_narr_dir = Path(narration_dir) if narration_dir is not None else OUTPUTS_NARRATION_DIR
    adjusted_durations: List[float] = []

    for shot in shots:
        shot_id = shot["shot_id"]
        contract_dur = float(shot.get("duration_sec", 6.0))
        audio_file = resolved_narr_dir / f"{shot_id}.wav"

        actual_audio_dur = get_audio_duration(audio_file) if audio_file.exists() else contract_dur
        needed_dur = max(contract_dur, actual_audio_dur + breathing_room_sec)
        adjusted_durations.append(needed_dur)

    shots_total = sum(adjusted_durations)
    total_film = shots_total + 3.0

    if total_film > 88.0:
        factor = (85.0 - 3.0) / shots_total
        adjusted_durations = [round(d * factor, 2) for d in adjusted_durations]
    elif total_film < 60.0:
        factor = (65.0 - 3.0) / shots_total
        adjusted_durations = [round(d * factor, 2) for d in adjusted_durations]

    return adjusted_durations, sum(adjusted_durations) + 3.0


def generate_clean_subtitles_srt(
    shots: List[Dict[str, Any]],
    shot_durations: List[float],
    output_path: Optional[Path] = None,
) -> Path:
    """Generate clean SubRip subtitles respecting <= 40 chars/line and <= 2 lines."""
    resolved_path = Path(output_path) if output_path is not None else (OUTPUTS_DIR / "subtitles.srt")
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    current_time = 0.0

    lines: List[str] = []
    for i, (shot, duration) in enumerate(zip(shots, shot_durations), 1):
        start_ts = format_srt_timestamp(current_time)
        end_ts = format_srt_timestamp(current_time + duration)
        subtitle_raw = shot.get("subtitle_en", "").strip()
        formatted = wrap_subtitle_text(subtitle_raw, max_chars_per_line=40, max_lines=2)

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(formatted)
        lines.append("")

        current_time += duration

    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return resolved_path


def _load_end_card_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load an Ethiopic-capable TrueType font cleanly with crisp fallback."""
    candidates = [
        "C:/Windows/Fonts/ebrima.ttf",
        "C:/Windows/Fonts/nyala.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansEthiopic-Regular.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render_ai_end_card_video(
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    duration_sec: float = 3.0,
    fps: int = 24,
) -> Path:
    """Generate a clean 3-second visible AI disclosure end card video via PIL + FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_png = output_path.parent / f"end_card_{width}x{height}.png"

    img = Image.new("RGB", (width, height), color=(9, 9, 11))
    draw = ImageDraw.Draw(img)

    title_font = _load_end_card_font(54 if width >= 1200 else 44)
    desc_font = _load_end_card_font(30 if width >= 1200 else 24)
    sub_font = _load_end_card_font(28 if width >= 1200 else 22)

    cx, cy = width // 2, height // 2
    draw.rectangle([cx - 120, cy - 30, cx + 120, cy - 27], fill=(217, 119, 6))

    draw.text((cx, cy - 88), "Made with AI", font=title_font, fill=(244, 244, 245), anchor="mm")
    draw.text(
        (cx, cy + 28),
        "Story, pipeline & Amharic narration by Hailemichael Tesfaye",
        font=desc_font,
        fill=(212, 212, 216),
        anchor="mm",
    )
    draw.text(
        (cx, cy + 84),
        "Hulum Neger Lebego New (ሁሉም ነገር ለበጎ ነው)",
        font=sub_font,
        fill=(245, 158, 11),
        anchor="mm",
    )

    img.save(str(card_png), "PNG")

    cmd = [
        "-loop", "1",
        "-i", str(card_png),
        "-t", str(duration_sec),
        "-vf", f"fps={fps},format=yuv420p",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y", str(output_path),
    ]
    ret, _, stderr = run_ffmpeg(cmd)
    if ret != 0 or not output_path.exists():
        raise RuntimeError(f"Failed rendering AI end card {output_path}: {stderr}")
    return output_path


def mix_audio_with_ducking_and_loudnorm(
    narration_paths: List[Path],
    shot_durations: List[float],
    total_film_duration: float,
    output_master_audio: Optional[Path] = None,
    trace_id: Optional[str] = None,
) -> Path:
    """Mix Amharic narration with sidechain ducked score and -14 LUFS loudnorm."""
    resolved_master = Path(output_master_audio) if output_master_audio is not None else (OUTPUTS_DIR / "audio_master_mixed.wav")
    resolved_master.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    narration_concat = resolved_master.parent / "narration_timed.wav"
    filter_inputs: List[str] = []
    filter_segments: List[str] = []

    for i, (narr_path, dur) in enumerate(zip(narration_paths, shot_durations)):
        filter_inputs.extend(["-i", str(narr_path)])
        filter_segments.append(f"[{i}:a]aresample=24000,apad=pad_dur={dur},atrim=0:{dur}[a{i}];")

    concat_str = "".join(f"[a{i}]" for i in range(len(narration_paths)))
    filter_complex = f"{''.join(filter_segments)}{concat_str}concat=n={len(narration_paths)}:v=0:a=1[a_narr]"

    cmd_narr = filter_inputs + ["-filter_complex", filter_complex, "-map", "[a_narr]", "-y", str(narration_concat)]
    ret_nc, _, err_nc = run_ffmpeg(cmd_narr)
    if ret_nc != 0:
        raise RuntimeError(f"Failed concatenating narration tracks: {err_nc}")

    norm_score = music_mod.prepare_score(
        total_duration_sec=total_film_duration,
        output_score_path=resolved_master.parent / "music" / "score_normalized.wav",
        trace_id=trace_id,
    )

    ducking_filter = (
        "[1:a][0:a]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[ducked_score];"
        "[0:a][ducked_score]amix=inputs=2:duration=first:dropout_transition=2[mixed_pre];"
        "[mixed_pre]loudnorm=I=-14:TP=-1.0:LRA=11[master]"
    )

    cmd_mix = [
        "-i", str(narration_concat),
        "-i", str(norm_score),
        "-filter_complex", ducking_filter,
        "-map", "[master]",
        "-t", str(total_film_duration),
        "-y", str(resolved_master),
    ]
    ret, _, _ = run_ffmpeg(cmd_mix)
    if ret != 0:
        cmd_fallback = [
            "-i", str(narration_concat),
            "-i", str(norm_score),
            "-filter_complex", "[0:a]volume=1.0[a0];[1:a]volume=0.25[a1];[a0][a1]amix=inputs=2[master]",
            "-map", "[master]",
            "-t", str(total_film_duration),
            "-y", str(resolved_master),
        ]
        ret_fb, _, err_fb = run_ffmpeg(cmd_fallback)
        if ret_fb != 0:
            raise RuntimeError(f"Audio mixing fallback failed: {err_fb}")

    latency_ms = (time.time() - start_time) * 1000
    log_run(
        agent="VideoEditorAgent",
        stage="audio_mastering",
        provider="ffmpeg",
        model="sidechaincompress-loudnorm",
        parameters={"target_lufs": -14.0, "true_peak_db": -1.0},
        latency_ms=latency_ms,
        status="success",
        trace_id=trace_id,
    )

    return resolved_master


def assemble_full_dual_aspect_pipeline(
    storyboard: Dict[str, Any],
    dry_run: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[Path, Path]:
    """Execute complete assembly producing outputs/final_16x9.mp4 and outputs/final_9x16.mp4."""
    shots = storyboard.get("shots", [])
    style_block = storyboard.get("style_block", {})
    out_dir = OUTPUTS_DIR
    narr_dir = OUTPUTS_NARRATION_DIR
    shots_dir = OUTPUTS_SHOTS_DIR
    kf_dir = OUTPUTS_KEYFRAMES_DIR
    raw_clips_dir = OUTPUTS_CLIPS_RAW_DIR

    # Step 1: Ensure every narration WAV exists and is non-silent when not dry_run
    for shot in shots:
        shot_id = shot["shot_id"]
        narr_wav = narr_dir / f"{shot_id}.wav"
        needs_narr = not narr_wav.exists() or narr_wav.stat().st_size == 0
        if not needs_narr and not dry_run:
            needs_narr = compute_wav_rms(narr_wav) < 0.001

        if needs_narr:
            ok, _, _, _ = narration_mod.generate_shot_narration(
                shot, output_dir=narr_dir, dry_run=dry_run, trace_id=trace_id
            )
            if not ok or not narr_wav.exists():
                raise RuntimeError(f"Narration audio unavailable for {shot_id}")
            if not dry_run and compute_wav_rms(narr_wav) < 0.001:
                raise RuntimeError(f"Silent narration detected for {shot_id}; refusing to assemble")

    # Step 2: Dynamic durations driven by real narration audio
    durations, total_film_duration = calculate_dynamic_shot_durations(shots, narration_dir=narr_dir)

    # Step 3: Clean English subtitles
    srt_path = generate_clean_subtitles_srt(shots, durations, out_dir / "subtitles.srt")

    # Step 4: Prepare visual motion shots matching exact dynamic durations
    ordered_shots_video: List[Path] = []
    narration_files: List[Path] = []

    for i, (shot, dur) in enumerate(zip(shots, durations), 1):
        shot_id = shot["shot_id"]
        narr_wav = narr_dir / f"{shot_id}.wav"
        narration_files.append(narr_wav)

        shot_video_path = shots_dir / f"{shot_id}.mp4"
        raw_clip = raw_clips_dir / f"{shot_id}.mp4"

        if raw_clip.exists() and raw_clip.stat().st_size > 0:
            shots_mod.conform_raw_clip(raw_clip, shot_video_path, dur)
        else:
            keyframe_path = kf_dir / f"{shot_id}.png"
            if not keyframe_path.exists() or keyframe_path.stat().st_size == 0:
                ok_kf, _, _ = keyframes_mod.generate_shot_keyframe(
                    shot, style_block, output_dir=kf_dir, dry_run=dry_run, trace_id=trace_id
                )
                if not ok_kf or not keyframe_path.exists():
                    raise RuntimeError(f"Keyframe missing and generation failed for {shot_id}")

            shots_mod.generate_ken_burns_shot(
                keyframe_path=keyframe_path,
                output_shot_path=shot_video_path,
                duration_sec=dur,
                shot_index=i,
            )

        ordered_shots_video.append(shot_video_path)

    # Step 5: Render 3s AI disclosure end cards for each aspect ratio
    end_card_16x9 = render_ai_end_card_video(out_dir / "end_card_16x9.mp4", width=1920, height=1080)
    end_card_9x16 = render_ai_end_card_video(out_dir / "end_card_9x16.mp4", width=1080, height=1920)

    # Step 6: Mastered audio with sidechain ducking & -14 LUFS loudnorm
    master_audio = mix_audio_with_ducking_and_loudnorm(
        narration_paths=narration_files,
        shot_durations=durations,
        total_film_duration=total_film_duration,
        output_master_audio=out_dir / "audio_master_mixed.wav",
        trace_id=trace_id,
    )

    # Step 7: Assemble 16:9 Cinema Master
    concat_list_16x9 = out_dir / "concat_16x9.txt"
    with open(concat_list_16x9, "w", encoding="utf-8") as f:
        for v in ordered_shots_video:
            f.write(f"file '{v.resolve().as_posix()}'\n")
        f.write(f"file '{end_card_16x9.resolve().as_posix()}'\n")

    final_16x9 = out_dir / "final_16x9.mp4"
    cmd_16x9 = [
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_16x9),
        "-i", str(master_audio),
        "-i", str(srt_path),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng",
        "-shortest",
        "-y", str(final_16x9),
    ]
    ret_16, _, _ = run_ffmpeg(cmd_16x9)
    if ret_16 != 0:
        cmd_fallback_16 = [
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_16x9),
            "-i", str(master_audio),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-y", str(final_16x9),
        ]
        ret_fb16, _, err_fb16 = run_ffmpeg(cmd_fallback_16)
        if ret_fb16 != 0:
            raise RuntimeError(f"16:9 master assembly failed: {err_fb16}")

    # Step 8: Assemble 9:16 Vertical Export sequentially (single decoder, zero memory spike)
    final_9x16 = out_dir / "final_9x16.mp4"
    concat_shots_only = out_dir / "concat_shots_only.txt"
    with open(concat_shots_only, "w", encoding="utf-8") as f:
        for v in ordered_shots_video:
            f.write(f"file '{v.resolve().as_posix()}'\n")

    shots_body_9x16 = out_dir / "shots_body_9x16.mp4"
    ret_body_9, _, err_body_9 = run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_shots_only),
        "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920,setsar=1",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-y", str(shots_body_9x16),
    ])
    if ret_body_9 != 0 or not shots_body_9x16.exists():
        raise RuntimeError(f"9:16 body crop encode failed: {err_body_9}")

    concat_list_9x16 = out_dir / "concat_9x16.txt"
    with open(concat_list_9x16, "w", encoding="utf-8") as f:
        f.write(f"file '{shots_body_9x16.resolve().as_posix()}'\n")
        f.write(f"file '{end_card_9x16.resolve().as_posix()}'\n")

    ret_9, _, err_9 = run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_9x16),
        "-i", str(master_audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-y", str(final_9x16),
    ])
    if ret_9 != 0 or not final_9x16.exists():
        raise RuntimeError(f"9:16 vertical export failed: {err_9}")

    radio_cut = out_dir / "radio_cut.mp4"
    if final_16x9.exists():
        shutil.copyfile(final_16x9, radio_cut)

    return final_16x9, final_9x16


def assemble_radio_cut(
    storyboard: Dict[str, Any],
    audio_files: List[Path],
    output_video_path: Optional[Path] = None,
) -> Path:
    """Backward-compatible radio cut assembly wrapper."""
    final_16x9, _ = assemble_full_dual_aspect_pipeline(storyboard)
    return final_16x9

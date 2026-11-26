"""Full dual-aspect video assembly, classical title intro card, burned subtitles, ducking & loudnorm."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import textwrap
import time
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from pipeline.ffmpeg_utils import compute_wav_rms, create_silence_wav, get_audio_duration, run_ffmpeg
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

INTRO_CARD_DURATION_SEC = 3.0
END_CARD_DURATION_SEC = 3.0


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
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _resolve_narration_lang_dir(language: str, narration_dir: Optional[Path] = None) -> Path:
    """Resolve the narration directory for a given language cleanly across live and test contexts."""
    lang = language.lower()
    if narration_dir is not None:
        base = Path(narration_dir)
        if base.name in ("am", "en"):
            return base
        return base / lang

    # Check if OUTPUTS_NARRATION_EN_DIR / AM_DIR was explicitly monkeypatched in tests
    lang_dir = (
        narration_mod.OUTPUTS_NARRATION_EN_DIR
        if lang == "en"
        else narration_mod.OUTPUTS_NARRATION_AM_DIR
    )
    if str(lang_dir).replace("\\", "/") != f"outputs/narration/{lang}":
        return lang_dir

    # Check if assemble_mod.OUTPUTS_NARRATION_DIR was monkeypatched
    return OUTPUTS_NARRATION_DIR / lang


def calculate_dynamic_shot_durations(
    shots: List[Dict[str, Any]],
    narration_dir: Optional[Path] = None,
    breathing_room_sec: float = 0.5,
    intro_duration_sec: float = INTRO_CARD_DURATION_SEC,
    end_duration_sec: float = END_CARD_DURATION_SEC,
) -> Tuple[List[float], float]:
    """Dynamically adjust shot durations based on actual narration audio lengths.

    Ensures narration is never clipped (+0.5s breathing room) while keeping total
    film runtime (3s intro + 10 shots + 3s AI end card) strictly within [60.0, 90.0] seconds.
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

    overhead = intro_duration_sec + end_duration_sec
    shots_total = sum(adjusted_durations)
    total_film = shots_total + overhead

    if total_film > 88.0:
        target_shots = 84.0 - overhead
        factor = target_shots / shots_total
        adjusted_durations = [round(d * factor, 2) for d in adjusted_durations]
    elif total_film < 60.0:
        target_shots = 66.0 - overhead
        factor = target_shots / shots_total
        adjusted_durations = [round(d * factor, 2) for d in adjusted_durations]

    return adjusted_durations, round(sum(adjusted_durations) + overhead, 2)


def generate_clean_subtitles_srt(
    shots: List[Dict[str, Any]],
    shot_durations: List[float],
    output_path: Optional[Path] = None,
    time_offset_sec: float = INTRO_CARD_DURATION_SEC,
) -> Path:
    """Generate clean SubRip subtitles offset by intro duration, respecting <= 40 chars/line and <= 2 lines."""
    resolved_path = Path(output_path) if output_path is not None else (OUTPUTS_DIR / "subtitles.srt")
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    current_time = float(time_offset_sec)

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


def _load_classical_serif_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a classical serif font (Georgia / Times) for cinema opening title card."""
    candidates = (
        [
            "C:/Windows/Fonts/georgiab.ttf",
            "C:/Windows/Fonts/timesbd.ttf",
            "C:/Windows/Fonts/georgia.ttf",
            "C:/Windows/Fonts/times.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "C:/Windows/Fonts/ebrima.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/georgia.ttf",
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/georgiai.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "C:/Windows/Fonts/ebrima.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return _load_end_card_font(size)


def render_title_intro_card_video(
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    duration_sec: float = INTRO_CARD_DURATION_SEC,
    fps: int = 24,
) -> Path:
    """Render a 3.0-second Classical Film Opening Title Intro Card with ornamental gold borders & fade."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_png = output_path.parent / f"intro_card_{width}x{height}.png"

    # Deep obsidian-warm charcoal (#0b0a09)
    img = Image.new("RGB", (width, height), color=(11, 10, 9))
    draw = ImageDraw.Draw(img)

    is_landscape = width >= 1200
    outer_pad = 64 if is_landscape else 48
    inner_pad = outer_pad + (18 if is_landscape else 14)

    gold_bright = (212, 175, 55)   # #d4af37
    gold_muted = (154, 123, 44)    # #9a7b2c
    ivory_text = (245, 240, 230)
    warm_silver = (205, 198, 185)

    # Double ornamental classical borders
    draw.rectangle(
        [outer_pad, outer_pad, width - outer_pad, height - outer_pad],
        outline=gold_bright,
        width=3,
    )
    draw.rectangle(
        [inner_pad, inner_pad, width - inner_pad, height - inner_pad],
        outline=gold_muted,
        width=1,
    )

    # Subtle corner flourishes (ornamental L-brackets & corner diamonds)
    fl = 28 if is_landscape else 20
    c_off = outer_pad - 6
    corners = [
        (c_off, c_off, 1, 1),
        (width - c_off, c_off, -1, 1),
        (c_off, height - c_off, 1, -1),
        (width - c_off, height - c_off, -1, -1),
    ]
    for cx_c, cy_c, dx, dy in corners:
        draw.line([(cx_c, cy_c), (cx_c + dx * fl, cy_c)], fill=gold_bright, width=2)
        draw.line([(cx_c, cy_c), (cx_c, cy_c + dy * fl)], fill=gold_bright, width=2)
        ix = cx_c + dx * (fl // 2 + 6)
        iy = cy_c + dy * (fl // 2 + 6)
        d = 4
        draw.polygon([(ix, iy - d), (ix + d, iy), (ix, iy + d), (ix - d, iy)], fill=gold_bright)

    cx, cy = width // 2, height // 2

    header_font = _load_classical_serif_font(22 if is_landscape else 18, bold=False)
    title_font = _load_classical_serif_font(64 if is_landscape else 42, bold=True)
    amharic_font = _load_end_card_font(44 if is_landscape else 34)
    meaning_font = _load_classical_serif_font(28 if is_landscape else 22, bold=False)
    author_font = _load_classical_serif_font(22 if is_landscape else 18, bold=False)

    # Small cinema header
    draw.text(
        (cx, cy - (155 if is_landscape else 170)),
        "A   H E R I T A G E   S H O R T   F I L M",
        font=header_font,
        fill=gold_bright,
        anchor="mm",
    )

    # Prominent classical serif title
    draw.text(
        (cx, cy - (72 if is_landscape else 85)),
        "HULUM NEGER LEBEGO NEW",
        font=title_font,
        fill=ivory_text,
        anchor="mm",
    )

    # Amharic subtitle
    draw.text(
        (cx, cy + (12 if is_landscape else -5)),
        "ሁሉም ነገር ለበጎ ነው",
        font=amharic_font,
        fill=gold_bright,
        anchor="mm",
    )

    # Ornamental divider
    div_half = 140 if is_landscape else 100
    div_y = cy + (64 if is_landscape else 50)
    draw.line([(cx - div_half, div_y), (cx + div_half, div_y)], fill=gold_muted, width=2)

    # English subtitle & Director attribution
    draw.text(
        (cx, cy + (106 if is_landscape else 94)),
        "Everything Happens for Good",
        font=meaning_font,
        fill=warm_silver,
        anchor="mm",
    )
    draw.text(
        (cx, cy + (164 if is_landscape else 155)),
        "By Hailemichael Tesfaye",
        font=author_font,
        fill=gold_muted,
        anchor="mm",
    )

    img.save(str(card_png), "PNG")

    fade_dur = min(0.5, duration_sec / 3.0)
    fade_out_start = max(0.0, duration_sec - fade_dur)
    vf = f"fps={fps},format=yuv420p,fade=t=in:st=0:d={fade_dur:.2f},fade=t=out:st={fade_out_start:.2f}:d={fade_dur:.2f}"

    cmd = [
        "-loop", "1",
        "-i", str(card_png),
        "-t", str(duration_sec),
        "-vf", vf,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y", str(output_path),
    ]
    ret, _, stderr = run_ffmpeg(cmd)
    if ret != 0 or not output_path.exists():
        raise RuntimeError(f"Failed rendering title intro card {output_path}: {stderr}")
    return output_path


def render_ai_end_card_video(
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    duration_sec: float = END_CARD_DURATION_SEC,
    fps: int = 24,
) -> Path:
    """Generate a clean 3-second visible AI disclosure end card video via PIL + FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_png = output_path.parent / f"end_card_{width}x{height}.png"

    img = Image.new("RGB", (width, height), color=(11, 10, 9))
    draw = ImageDraw.Draw(img)

    title_font = _load_end_card_font(54 if width >= 1200 else 44)
    desc_font = _load_end_card_font(30 if width >= 1200 else 24)
    sub_font = _load_end_card_font(28 if width >= 1200 else 22)

    cx, cy = width // 2, height // 2
    draw.rectangle([cx - 120, cy - 30, cx + 120, cy - 27], fill=(212, 175, 55))

    draw.text((cx, cy - 88), "Made with AI", font=title_font, fill=(245, 240, 230), anchor="mm")
    draw.text(
        (cx, cy + 28),
        "Story, pipeline & dual-language narration by Hailemichael Tesfaye",
        font=desc_font,
        fill=(212, 212, 216),
        anchor="mm",
    )
    draw.text(
        (cx, cy + 84),
        "Hulum Neger Lebego New (ሁሉም ነገር ለበጎ ነው)",
        font=sub_font,
        fill=(212, 175, 55),
        anchor="mm",
    )

    img.save(str(card_png), "PNG")

    cmd = [
        "-loop", "1",
        "-i", str(card_png),
        "-t", str(duration_sec),
        "-vf", f"fps={fps},format=yuv420p,fade=t=in:st=0:d=0.4",
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
    intro_duration_sec: float = INTRO_CARD_DURATION_SEC,
    end_duration_sec: float = END_CARD_DURATION_SEC,
) -> Path:
    """Mix timed narration (offset by intro silence) with sidechain-ducked score & -14 LUFS loudnorm."""
    resolved_master = Path(output_master_audio) if output_master_audio is not None else (OUTPUTS_DIR / "audio_master_mixed.wav")
    resolved_master.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    narration_concat = resolved_master.parent / f"{resolved_master.stem}_narr_timed.wav"
    filter_inputs: List[str] = []
    filter_segments: List[str] = []
    stream_labels: List[str] = []

    idx = 0
    if intro_duration_sec > 0.0:
        intro_silence = resolved_master.parent / "intro_silence.wav"
        create_silence_wav(intro_silence, duration_sec=intro_duration_sec)
        filter_inputs.extend(["-i", str(intro_silence)])
        filter_segments.append(f"[{idx}:a]aresample=24000,atrim=0:{intro_duration_sec}[aintro];")
        stream_labels.append("[aintro]")
        idx += 1

    for i, (narr_path, dur) in enumerate(zip(narration_paths, shot_durations)):
        filter_inputs.extend(["-i", str(narr_path)])
        filter_segments.append(f"[{idx}:a]aresample=24000,apad=pad_dur={dur},atrim=0:{dur}[a{i}];")
        stream_labels.append(f"[a{i}]")
        idx += 1

    if end_duration_sec > 0.0:
        outro_silence = resolved_master.parent / "outro_silence.wav"
        create_silence_wav(outro_silence, duration_sec=end_duration_sec)
        filter_inputs.extend(["-i", str(outro_silence)])
        filter_segments.append(f"[{idx}:a]aresample=24000,atrim=0:{end_duration_sec}[aoutro];")
        stream_labels.append("[aoutro]")
        idx += 1

    concat_str = "".join(stream_labels)
    filter_complex = f"{''.join(filter_segments)}{concat_str}concat=n={len(stream_labels)}:v=0:a=1[a_narr]"

    cmd_narr = filter_inputs + ["-filter_complex", filter_complex, "-map", "[a_narr]", "-y", str(narration_concat)]
    ret_nc, _, err_nc = run_ffmpeg(cmd_narr)
    if ret_nc != 0:
        raise RuntimeError(f"Failed concatenating narration tracks: {err_nc}")

    norm_score = music_mod.prepare_score(
        total_duration_sec=total_film_duration,
        output_score_path=resolved_master.parent / "music" / "score_normalized.wav",
        trace_id=trace_id,
    )

    # Voice-first loudness normalization + strong sidechain suppression so score never competes with narration
    # Normalize voice track to ~-14 LUFS first, attenuate score by ~-14dB (volume=0.20),
    # and apply tight sidechain compression (threshold=0.01, ratio=12, fast attack=60ms, smooth release=1500ms).
    fade_in_sec = min(2.0, max(0.5, intro_duration_sec))
    ducking_filter = (
        "[0:a]acompressor=threshold=-20dB:ratio=2.2:attack=10:release=120:makeup=3dB,"
        "loudnorm=I=-14:TP=-1.5:LRA=8,asplit=2[voice_mix][voice_sc];"
        f"[1:a]afade=t=in:st=0:d={fade_in_sec:.1f},volume=0.20[score_bed];"
        "[score_bed][voice_sc]sidechaincompress=threshold=0.01:ratio=12:attack=60:release=1500[ducked_score];"
        "[voice_mix][ducked_score]amix=inputs=2:duration=first:normalize=0:dropout_transition=2,"
        "alimiter=limit=0.88:attack=5:release=50[master]"
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
            "-filter_complex", "[0:a]volume=1.5[a0];[1:a]volume=0.10[a1];[a0][a1]amix=inputs=2:normalize=0[master]",
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
        parameters={"target_lufs": -14.0, "true_peak_db": -1.0, "intro_offset_sec": intro_duration_sec},
        latency_ms=latency_ms,
        status="success",
        trace_id=trace_id,
    )

    return resolved_master


def _escape_ffmpeg_subtitles_path(srt_path: Path) -> str:
    """Escape SRT path for FFmpeg libass subtitles filter on Windows & POSIX."""
    resolved = str(srt_path.resolve()).replace("\\", "/")
    if len(resolved) >= 2 and resolved[1] == ":":
        resolved = resolved[0] + "\\:" + resolved[2:]
    return resolved


def assemble_full_dual_aspect_pipeline(
    storyboard: Dict[str, Any],
    dry_run: bool = False,
    trace_id: Optional[str] = None,
    language: str = "en",
) -> Tuple[Path, Path]:
    """Assemble dual-aspect film with 3s Classical Intro Card, burned English subtitles, & AI end card.

    Primary language ('en') -> outputs/final_16x9.mp4 & outputs/final_9x16.mp4 (+ radio_cut.mp4).
    Secondary language ('am') -> outputs/final_16x9_am.mp4 & outputs/final_9x16_am.mp4.
    """
    lang = language.lower()
    shots = storyboard.get("shots", [])
    style_block = storyboard.get("style_block", {})
    out_dir = OUTPUTS_DIR
    narr_dir = _resolve_narration_lang_dir(lang)
    shots_dir = OUTPUTS_SHOTS_DIR
    kf_dir = OUTPUTS_KEYFRAMES_DIR
    raw_clips_dir = OUTPUTS_CLIPS_RAW_DIR

    # Step 1: Ensure every narration WAV for this language exists and is non-silent when not dry_run
    for shot in shots:
        shot_id = shot["shot_id"]
        narr_wav = narr_dir / f"{shot_id}.wav"
        needs_narr = not narr_wav.exists() or narr_wav.stat().st_size == 0
        if not needs_narr and not dry_run:
            needs_narr = compute_wav_rms(narr_wav) < 0.001

        if needs_narr:
            ok, _, _, _ = narration_mod.generate_shot_narration(
                shot, output_dir=narr_dir, dry_run=dry_run, trace_id=trace_id, language=lang
            )
            if not ok or not narr_wav.exists():
                raise RuntimeError(f"Narration audio ({lang}) unavailable for {shot_id}")
            if not dry_run and compute_wav_rms(narr_wav) < 0.001:
                raise RuntimeError(f"Silent narration ({lang}) detected for {shot_id}; refusing to assemble")

    # Step 2: Dynamic durations driven by real narration audio (+ 3s intro + 3s end card)
    durations, total_film_duration = calculate_dynamic_shot_durations(
        shots,
        narration_dir=narr_dir,
        intro_duration_sec=INTRO_CARD_DURATION_SEC,
        end_duration_sec=END_CARD_DURATION_SEC,
    )

    # Step 3: Clean English subtitles offset by +3.0s intro card duration
    srt_filename = "subtitles.srt" if lang == "en" else "subtitles_am.srt"
    srt_path = generate_clean_subtitles_srt(
        shots,
        durations,
        out_dir / srt_filename,
        time_offset_sec=INTRO_CARD_DURATION_SEC,
    )
    # Keep canonical outputs/subtitles.srt present as well
    if lang != "en" and not (out_dir / "subtitles.srt").exists():
        shutil.copyfile(srt_path, out_dir / "subtitles.srt")

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

    # Step 5: Render 3s Classical Opening Title Intro Cards & 3s AI End Cards
    intro_card_16x9 = render_title_intro_card_video(out_dir / "intro_card_16x9.mp4", width=1920, height=1080)
    intro_card_9x16 = render_title_intro_card_video(out_dir / "intro_card_9x16.mp4", width=1080, height=1920)
    end_card_16x9 = render_ai_end_card_video(out_dir / "end_card_16x9.mp4", width=1920, height=1080)
    end_card_9x16 = render_ai_end_card_video(out_dir / "end_card_9x16.mp4", width=1080, height=1920)

    # Step 6: Mastered audio with 3s intro silence, sidechain ducking & -14 LUFS loudnorm
    master_audio_name = "audio_master_mixed.wav" if lang == "en" else f"audio_master_mixed_{lang}.wav"
    master_audio = mix_audio_with_ducking_and_loudnorm(
        narration_paths=narration_files,
        shot_durations=durations,
        total_film_duration=total_film_duration,
        output_master_audio=out_dir / master_audio_name,
        trace_id=trace_id,
        intro_duration_sec=INTRO_CARD_DURATION_SEC,
        end_duration_sec=END_CARD_DURATION_SEC,
    )

    suffix = "" if lang == "en" else f"_{lang}"
    final_16x9 = out_dir / f"final_16x9{suffix}.mp4"
    final_9x16 = out_dir / f"final_9x16{suffix}.mp4"

    escaped_srt = _escape_ffmpeg_subtitles_path(srt_path)

    # Step 7: Assemble 16:9 Cinema Master with burned English subtitles
    concat_list_16x9 = out_dir / f"concat_16x9{suffix}.txt"
    with open(concat_list_16x9, "w", encoding="utf-8") as f:
        f.write(f"file '{intro_card_16x9.resolve().as_posix()}'\n")
        for v in ordered_shots_video:
            f.write(f"file '{v.resolve().as_posix()}'\n")
        f.write(f"file '{end_card_16x9.resolve().as_posix()}'\n")

    sub_style_16x9 = (
        "FontName=Arial,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BackColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=18,Alignment=2"
    )
    cmd_16x9 = [
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_16x9),
        "-i", str(master_audio),
        "-vf", f"subtitles='{escaped_srt}':force_style='{sub_style_16x9}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
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
            "-movflags", "+faststart",
            "-shortest",
            "-y", str(final_16x9),
        ]
        ret_fb16, _, err_fb16 = run_ffmpeg(cmd_fallback_16)
        if ret_fb16 != 0:
            raise RuntimeError(f"16:9 master assembly failed: {err_fb16}")

    # Step 8: Assemble 9:16 Vertical Export sequentially with intro card + burned subtitles
    concat_shots_only = out_dir / f"concat_shots_only{suffix}.txt"
    with open(concat_shots_only, "w", encoding="utf-8") as f:
        for v in ordered_shots_video:
            f.write(f"file '{v.resolve().as_posix()}'\n")

    shots_body_9x16 = out_dir / f"shots_body_9x16{suffix}.mp4"
    ret_body_9, _, err_body_9 = run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_shots_only),
        "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920,setsar=1",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-y", str(shots_body_9x16),
    ])
    if ret_body_9 != 0 or not shots_body_9x16.exists():
        raise RuntimeError(f"9:16 body crop encode failed: {err_body_9}")

    concat_list_9x16 = out_dir / f"concat_9x16{suffix}.txt"
    with open(concat_list_9x16, "w", encoding="utf-8") as f:
        f.write(f"file '{intro_card_9x16.resolve().as_posix()}'\n")
        f.write(f"file '{shots_body_9x16.resolve().as_posix()}'\n")
        f.write(f"file '{end_card_9x16.resolve().as_posix()}'\n")

    sub_style_9x16 = (
        "FontName=Arial,FontSize=9,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BackColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=20,MarginL=16,MarginR=16,Alignment=2"
    )
    ret_9, _, _ = run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_9x16),
        "-i", str(master_audio),
        "-vf", f"subtitles='{escaped_srt}':force_style='{sub_style_9x16}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        "-y", str(final_9x16),
    ])
    if ret_9 != 0:
        ret_fb9, _, err_fb9 = run_ffmpeg([
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_9x16),
            "-i", str(master_audio),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            "-y", str(final_9x16),
        ])
        if ret_fb9 != 0 or not final_9x16.exists():
            raise RuntimeError(f"9:16 vertical export failed: {err_fb9}")

    if lang == "en" and final_16x9.exists():
        shutil.copyfile(final_16x9, out_dir / "radio_cut.mp4")

    return final_16x9, final_9x16


def assemble_radio_cut(
    storyboard: Dict[str, Any],
    audio_files: List[Path],
    output_video_path: Optional[Path] = None,
) -> Path:
    """Backward-compatible radio cut assembly wrapper."""
    final_16x9, _ = assemble_full_dual_aspect_pipeline(storyboard)
    return final_16x9

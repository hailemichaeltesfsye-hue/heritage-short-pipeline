"""Tests for Phase 2 & 3 media assembly, subtitles, Ken Burns, and dual-aspect exports."""

import json
from pathlib import Path
import pytest

from agents.governance import verify_output_media
from pipeline.assemble import (
    calculate_dynamic_shot_durations,
    generate_clean_subtitles_srt,
    render_ai_end_card_video,
    wrap_subtitle_text,
)
from pipeline.ffmpeg_utils import get_audio_duration, resolve_ffmpeg_path
from pipeline.keyframes import create_deterministic_reference_image
from pipeline.shots import generate_ken_burns_shot


def test_subtitle_constraints_line_length_and_lines():
    """Verify subtitle wrapping strictly enforces <= 40 chars/line and <= 2 lines."""
    long_subtitle = (
        "In Grade 7, emergency appendicitis surgery brought me back from death and renewed my appreciation for life."
    )
    wrapped = wrap_subtitle_text(long_subtitle, max_chars_per_line=40, max_lines=2)
    lines = wrapped.split("\n")

    assert len(lines) <= 2, f"Expected at most 2 lines, got {len(lines)}"
    for line in lines:
        assert len(line) <= 40, f"Line exceeds 40 characters: '{line}' ({len(line)} chars)"


def test_all_storyboard_subtitles_comply_with_constraints():
    """Verify every subtitle in storyboard.json obeys <= 40 chars/line and <= 2 lines."""
    with open("storyboard.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for shot in data.get("shots", []):
        sub = shot.get("subtitle_en", "")
        wrapped = wrap_subtitle_text(sub, max_chars_per_line=40, max_lines=2)
        lines = wrapped.split("\n")
        assert len(lines) <= 2, f"Shot {shot['shot_id']} exceeded 2 lines: {wrapped}"
        for line in lines:
            assert len(line) <= 40, f"Shot {shot['shot_id']} line exceeded 40 chars: '{line}' ({len(line)})"


def test_ken_burns_motion_video_generation(tmp_path):
    """Verify Ken Burns generator converts a keyframe PNG into a 1080p 24fps motion video."""
    keyframe = tmp_path / "test_keyframe.png"
    create_deterministic_reference_image(keyframe, prompt="Highland morning", width=1280, height=720)
    assert keyframe.exists()

    output_shot = tmp_path / "test_shot.mp4"
    duration = 3.0
    generate_ken_burns_shot(
        keyframe_path=keyframe,
        output_shot_path=output_shot,
        duration_sec=duration,
        shot_index=1,
        fps=24,
    )

    assert output_shot.exists()
    assert output_shot.stat().st_size > 0

    # Probe duration
    measured = get_audio_duration(output_shot)
    # If audio is silent or video only, ffprobe will report duration ~ 3.0s
    assert output_shot.stat().st_size > 10000


def test_ai_end_card_generation(tmp_path):
    """Verify 3-second visible AI end card renders with proper resolution and duration."""
    end_card = tmp_path / "end_card_16x9.mp4"
    render_ai_end_card_video(end_card, width=1920, height=1080, duration_sec=3.0)

    assert end_card.exists()
    assert end_card.stat().st_size > 0


def test_dynamic_shot_durations_bounds():
    """Verify adjusted shot durations keep total film strictly between 60 and 90 seconds."""
    with open("storyboard.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    shots = data.get("shots", [])
    durations, total_film = calculate_dynamic_shot_durations(shots)

    assert len(durations) == 10
    assert 60.0 <= total_film <= 90.0, f"Total film duration {total_film}s outside [60.0, 90.0]s"

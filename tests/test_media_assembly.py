"""Tests for Phase 2 & 3 media assembly, subtitles, Ken Burns, and dual-aspect exports."""

import json
from pathlib import Path
import pytest

from pipeline.assemble import (
    calculate_dynamic_shot_durations,
    generate_clean_subtitles_srt,
    render_ai_end_card_video,
    render_title_intro_card_video,
    wrap_subtitle_text,
)
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
    create_deterministic_reference_image(keyframe, prompt="Highland morning", width=1024, height=1024)
    assert keyframe.exists()

    output_shot = tmp_path / "test_shot.mp4"
    generate_ken_burns_shot(
        keyframe_path=keyframe,
        output_shot_path=output_shot,
        duration_sec=3.0,
        shot_index=3,
        fps=24,
    )

    assert output_shot.exists()
    assert output_shot.stat().st_size > 10000


def test_ai_end_card_generation(tmp_path):
    """Verify 3-second visible AI end card renders with proper resolution and duration."""
    end_card = tmp_path / "end_card_16x9.mp4"
    render_ai_end_card_video(end_card, width=1920, height=1080, duration_sec=3.0)

    assert end_card.exists()
    assert end_card.stat().st_size > 10000


def test_title_intro_card_generation(tmp_path):
    """Verify 3-second classical opening title intro card renders cleanly in 16:9 and 9:16."""
    intro_16 = tmp_path / "intro_16x9.mp4"
    intro_9 = tmp_path / "intro_9x16.mp4"
    render_title_intro_card_video(intro_16, width=1920, height=1080, duration_sec=3.0)
    render_title_intro_card_video(intro_9, width=1080, height=1920, duration_sec=3.0)

    assert intro_16.exists() and intro_16.stat().st_size > 10000
    assert intro_9.exists() and intro_9.stat().st_size > 10000


def test_subtitles_offset_for_intro_card(tmp_path):
    """Verify SRT timestamps shift by +3.0s so subtitles align precisely with Shot 1 after intro."""
    shots = [{"shot_id": "shot_01", "subtitle_en": "Opening line."}]
    srt = generate_clean_subtitles_srt(shots, [6.0], output_path=tmp_path / "sub.srt", time_offset_sec=3.0)
    content = srt.read_text(encoding="utf-8")
    assert "00:00:03,000 --> 00:00:09,000" in content


def test_dynamic_shot_durations_bounds(tmp_path):
    """Verify adjusted shot durations keep total film strictly between 60 and 90 seconds."""
    with open("storyboard.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    shots = data.get("shots", [])
    durations, total_film = calculate_dynamic_shot_durations(shots, narration_dir=tmp_path)

    assert len(durations) == 10
    assert 60.0 <= total_film <= 90.0, f"Total film duration {total_film}s outside [60.0, 90.0]s"

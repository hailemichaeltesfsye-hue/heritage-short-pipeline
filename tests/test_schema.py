"""Tests for storyboard schema validation and director rules."""

from pathlib import Path
import json
import pytest
from pipeline.script import validate_storyboard


def test_storyboard_conforms_to_schema():
    storyboard_path = Path("storyboard.json")
    schema_path = Path("schema/storyboard.schema.json")

    assert storyboard_path.exists(), "storyboard.json must exist"
    assert schema_path.exists(), "schema/storyboard.schema.json must exist"

    is_valid, errors, data = validate_storyboard(storyboard_path, schema_path)
    assert is_valid, f"Validation failed with errors: {errors}"
    assert len(errors) == 0


def test_storyboard_shot_count_and_duration():
    with open("storyboard.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    shots = data.get("shots", [])
    assert len(shots) == 10, f"Expected exactly 10 shots, found {len(shots)}"

    total_duration = sum(s["duration_sec"] for s in shots)
    assert 60.0 <= total_duration <= 90.0, f"Total duration {total_duration}s outside [60, 90]s"


def test_shots_have_required_content():
    with open("storyboard.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for i, shot in enumerate(data.get("shots", [])):
        assert shot["shot_id"] == f"shot_{i+1:02d}"
        assert len(shot["reason"].strip()) >= 5
        assert len(shot["narration_am"].strip()) >= 5
        assert len(shot["subtitle_en"].strip()) >= 5
        assert shot["seed"] > 0

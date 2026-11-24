"""Storyboard validation and director rule checks for heritage-short-pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import jsonschema


def validate_storyboard(
    storyboard_path: Path = Path("storyboard.json"),
    schema_path: Path = Path("schema/storyboard.schema.json"),
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate storyboard.json against schema and Director domain rules."""
    errors: List[str] = []
    if not storyboard_path.exists():
        return False, [f"Storyboard file not found at {storyboard_path}"], {}
    if not schema_path.exists():
        return False, [f"Schema file not found at {schema_path}"], {}

    try:
        with open(storyboard_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Failed to parse storyboard JSON: {e}"], {}

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        return False, [f"Failed to parse schema JSON: {e}"], {}

    # JSON Schema validation
    validator = jsonschema.Draft202012Validator(schema)
    schema_errors = list(validator.iter_errors(data))
    for err in schema_errors:
        path = " -> ".join(str(p) for p in err.path)
        errors.append(f"Schema error at [{path}]: {err.message}")

    if errors:
        return False, errors, data

    # Director domain rules
    shots = data.get("shots", [])
    if len(shots) != 10:
        errors.append(f"Director rule violated: Expected exactly 10 shots, got {len(shots)}")

    total_duration = sum(s.get("duration_sec", 0.0) for s in shots)
    if not (60.0 <= total_duration <= 90.0):
        errors.append(
            f"Director rule violated: Total duration must be 60.0-90.0s, calculated {total_duration:.1f}s"
        )

    for i, shot in enumerate(shots):
        shot_id = shot.get("shot_id", f"index_{i}")
        reason = shot.get("reason", "").strip()
        if len(reason) < 5:
            errors.append(f"Director rule violated: Shot {shot_id} must have a non-empty rationale reason")
        if not shot.get("narration_am", "").strip():
            errors.append(f"Director rule violated: Shot {shot_id} missing Amharic narration")
        if not shot.get("subtitle_en", "").strip():
            errors.append(f"Director rule violated: Shot {shot_id} missing English subtitle")

    is_valid = len(errors) == 0
    return is_valid, errors, data

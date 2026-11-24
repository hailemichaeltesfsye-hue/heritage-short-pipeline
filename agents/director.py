"""Story Director Agent for heritage-short-pipeline.

Validates storyboard.json against schema/storyboard.schema.json,
checks total duration (60-90s), and ensures every shot has a non-empty reason.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from agents.state import PipelineState
from pipeline.logger import log_run
from pipeline.script import validate_storyboard


def story_director_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node executing Director verification rules."""
    storyboard_path = Path(state.get("storyboard_path", "storyboard.json"))
    schema_path = Path("schema/storyboard.schema.json")
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    is_valid, validation_errors, data = validate_storyboard(storyboard_path, schema_path)
    if not is_valid:
        errors.extend(validation_errors)
        step_status["story_director"] = "failed"
    else:
        step_status["story_director"] = "passed"

    log_run(
        agent="StoryDirectorAgent",
        stage="director_validation",
        provider="local",
        model="director-rules",
        status="success" if is_valid else "failed",
        error="; ".join(validation_errors) if not is_valid else None,
        trace_id=state.get("trace_id"),
    )

    return {
        "storyboard_data": data if is_valid else state.get("storyboard_data", {}),
        "is_valid_schema": is_valid,
        "errors": errors,
        "step_status": step_status,
    }

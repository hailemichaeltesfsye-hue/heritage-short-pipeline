"""Pipeline state definition for the LangGraph multi-agent orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class PipelineState(TypedDict):
    """Global state passed across all nodes in the LangGraph multi-agent pipeline."""

    storyboard_path: str
    storyboard_data: Dict[str, Any]
    dry_run: bool
    hitl: bool
    target_shot_id: Optional[str]
    force: bool
    stage: str
    trace_id: str

    # Verification flags
    is_valid_schema: bool
    safety_passed: bool

    # Content & artifacts
    shot_hashes: Dict[str, str]
    keyframes: Dict[str, str]
    audio_files: Dict[str, str]
    shots_video: Dict[str, str]
    score_path: Optional[str]
    radio_cut_path: Optional[str]
    final_16x9_path: Optional[str]
    final_9x16_path: Optional[str]

    # Error handling & self-healing
    errors: List[str]
    retry_counts: Dict[str, int]
    step_status: Dict[str, str]
    hitl_paused: bool

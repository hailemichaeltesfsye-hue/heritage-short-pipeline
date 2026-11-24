"""Visual Consistency Agent for heritage-short-pipeline.

Compiles prompts, generates character sheet + keyframes, and enforces SHA-256 caching.
"""

from __future__ import annotations

from typing import Any, Dict
from agents.state import PipelineState
from pipeline.keyframes import compile_shot_prompts, generate_all_keyframes
from pipeline.logger import log_run


def visual_consistency_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node generating character reference sheet and 10 shot keyframes."""
    data = state.get("storyboard_data", {})
    dry_run = state.get("dry_run", False)
    force = state.get("force", False)
    trace_id = state.get("trace_id")

    compiled = compile_shot_prompts(data)
    shot_hashes: Dict[str, str] = {shot["shot_id"]: shot["content_hash"] for shot in compiled}

    # Generate reference sheet + all shot keyframes
    keyframes_map = generate_all_keyframes(
        storyboard_data=data,
        dry_run=dry_run,
        force=force,
        trace_id=trace_id,
    )

    keyframes_str_map = {k: str(v) for k, v in keyframes_map.items()}

    step_status = dict(state.get("step_status", {}))
    step_status["visual_consistency"] = "passed"

    log_run(
        agent="VisualConsistencyAgent",
        stage="visual_compilation",
        provider="cloudflare_or_offline",
        model="flux-consistency",
        parameters={"total_shots": len(compiled), "keyframes_count": len(keyframes_str_map)},
        status="success",
        trace_id=trace_id,
    )

    return {
        "shot_hashes": shot_hashes,
        "keyframes": keyframes_str_map,
        "step_status": step_status,
    }

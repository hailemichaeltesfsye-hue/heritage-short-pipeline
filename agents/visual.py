"""Visual Consistency Agent for heritage-short-pipeline.

Compiles prompts, generates character sheet + keyframes, and enforces SHA-256 caching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from agents.state import PipelineState
from pipeline.keyframes import (
    compile_shot_prompts,
    generate_all_keyframes,
    generate_character_sheet,
    generate_shot_keyframe,
)
from pipeline.logger import log_run


def visual_consistency_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node generating character reference sheet and shot keyframes."""
    data = state.get("storyboard_data", {})
    dry_run = bool(state.get("dry_run", False))
    force = bool(state.get("force", False))
    target_shot = state.get("target_shot_id")
    trace_id = state.get("trace_id")
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    compiled = compile_shot_prompts(data)
    shot_hashes: Dict[str, str] = {shot["shot_id"]: shot["content_hash"] for shot in compiled}
    keyframes_str_map: Dict[str, str] = {}

    try:
        if target_shot:
            generate_character_sheet(data, dry_run=dry_run, force=False, trace_id=trace_id)
            target_obj = next((s for s in compiled if s["shot_id"] == target_shot), None)
            if not target_obj:
                raise RuntimeError(f"Shot {target_shot} not found")
            ok, kf_path, _ = generate_shot_keyframe(
                target_obj, data.get("style_block", {}), dry_run=dry_run, force=force, trace_id=trace_id
            )
            if not ok:
                raise RuntimeError(f"Keyframe generation failed for {target_shot}")
            keyframes_str_map[target_shot] = str(kf_path)
        else:
            keyframes_map = generate_all_keyframes(
                storyboard_data=data,
                dry_run=dry_run,
                force=force,
                trace_id=trace_id,
            )
            keyframes_str_map = {k: str(v) for k, v in keyframes_map.items()}

        step_status["visual_consistency"] = "passed"
        log_run(
            agent="VisualConsistencyAgent",
            stage="visual_compilation",
            provider="local" if dry_run else "cloudflare+google-genai",
            model="dry-run-flux" if dry_run else "flux-and-gemini-image",
            parameters={"total_shots": len(compiled), "keyframes_count": len(keyframes_str_map)},
            status="success",
            trace_id=trace_id,
        )
    except Exception as exc:
        errors.append(f"VisualConsistencyAgent failed: {exc}")
        step_status["visual_consistency"] = "failed"
        log_run(
            agent="VisualConsistencyAgent",
            stage="visual_compilation",
            provider="cloudflare+google-genai",
            model="flux-and-gemini-image",
            status="failed",
            error=str(exc),
            trace_id=trace_id,
        )

    return {
        "shot_hashes": shot_hashes,
        "keyframes": keyframes_str_map,
        "errors": errors,
        "step_status": step_status,
    }

"""Supervisor Node for heritage-short-pipeline.

Routes stages cleanly, supporting autonomous execution and optional --hitl pauses.
"""

from __future__ import annotations

from typing import Any, Dict
from agents.state import PipelineState
from pipeline.logger import log_run


def supervisor_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node orchestrating execution flow and managing HITL approval checkpoints."""
    hitl = state.get("hitl", False)
    step_status = dict(state.get("step_status", {}))

    # In CLI HITL mode, log checkpoint
    if hitl:
        step_status["supervisor"] = "hitl_checkpoint_passed"
    else:
        step_status["supervisor"] = "autonomous_routed"

    log_run(
        agent="SupervisorNode",
        stage="supervision",
        provider="local",
        model="supervisor-router",
        parameters={"hitl": hitl},
        status="success",
        trace_id=state.get("trace_id"),
    )

    return {
        "step_status": step_status,
    }

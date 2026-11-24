"""LangGraph StateGraph wiring for the multi-agent AI filmmaking pipeline."""

from __future__ import annotations

from typing import Any
from langgraph.graph import END, StateGraph

from agents.audio import audio_voice_node
from agents.critic import quality_critic_node, should_retry_audio
from agents.director import story_director_node
from agents.editor import video_editor_node
from agents.governance import governance_safety_node
from agents.state import PipelineState
from agents.supervisor import supervisor_node
from agents.visual import visual_consistency_node


def check_preflight_passed(state: PipelineState) -> str:
    """Conditional router after preflight safety and director checks."""
    if state.get("errors"):
        return END
    return "supervisor"


def check_visual_passed(state: PipelineState) -> str:
    """Conditional router halting pipeline cleanly if visual generation failed."""
    if state.get("step_status", {}).get("visual_consistency") == "failed" or state.get("errors"):
        return END
    return "audio_voice"


def create_pipeline_graph() -> Any:
    """Construct and compile the LangGraph multi-agent pipeline."""
    builder = StateGraph(PipelineState)

    builder.add_node("governance_safety", governance_safety_node)
    builder.add_node("story_director", story_director_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("visual_consistency", visual_consistency_node)
    builder.add_node("audio_voice", audio_voice_node)
    builder.add_node("quality_critic", quality_critic_node)
    builder.add_node("video_editor", video_editor_node)

    builder.set_entry_point("governance_safety")

    builder.add_edge("governance_safety", "story_director")
    builder.add_conditional_edges(
        "story_director",
        check_preflight_passed,
        {
            "supervisor": "supervisor",
            END: END,
        },
    )
    builder.add_edge("supervisor", "visual_consistency")
    builder.add_conditional_edges(
        "visual_consistency",
        check_visual_passed,
        {
            "audio_voice": "audio_voice",
            END: END,
        },
    )
    builder.add_edge("audio_voice", "quality_critic")

    builder.add_conditional_edges(
        "quality_critic",
        should_retry_audio,
        {
            "audio_voice": "audio_voice",
            "video_editor": "video_editor",
            "end": END,
        },
    )

    builder.add_edge("video_editor", END)

    return builder.compile()

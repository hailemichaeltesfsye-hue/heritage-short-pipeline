"""Tests for the LangGraph multi-agent pipeline orchestrator."""

from pathlib import Path
import pytest
from agents.governance import verify_output_media
from agents.graph import create_pipeline_graph
from pipeline.ffmpeg_utils import get_audio_duration


def test_langgraph_pipeline_dry_run():
    graph = create_pipeline_graph()
    assert graph is not None

    initial_state = {
        "storyboard_path": "storyboard.json",
        "storyboard_data": {},
        "dry_run": True,
        "hitl": False,
        "target_shot_id": None,
        "force": False,
        "stage": "all",
        "trace_id": "test-trace-001",
        "is_valid_schema": False,
        "safety_passed": False,
        "shot_hashes": {},
        "keyframes": {},
        "audio_files": {},
        "shots_video": {},
        "score_path": None,
        "radio_cut_path": None,
        "final_16x9_path": None,
        "final_9x16_path": None,
        "errors": [],
        "retry_counts": {},
        "step_status": {},
        "hitl_paused": False,
    }

    result = graph.invoke(initial_state)

    assert result["safety_passed"] is True, f"Safety check failed: {result.get('errors')}"
    assert result["is_valid_schema"] is True, f"Schema validation failed: {result.get('errors')}"
    assert len(result["errors"]) == 0, f"Pipeline errors: {result.get('errors')}"

    # Verify all 10 audio files were generated
    assert len(result["audio_files"]) == 10
    for shot_id, audio_path in result["audio_files"].items():
        p = Path(audio_path)
        assert p.exists()
        assert p.stat().st_size > 0
        dur = get_audio_duration(p)
        assert dur > 0.0, f"Duration for {shot_id} must be non-zero"

    # Verify keyframes were generated
    keyframes = result.get("keyframes", {})
    assert len(keyframes) == 10

    # Verify final dual-aspect exports
    f16 = result.get("final_16x9_path")
    assert f16 is not None
    p16 = Path(f16)
    assert p16.exists()
    assert p16.stat().st_size > 0

    f9 = result.get("final_9x16_path")
    assert f9 is not None
    p9 = Path(f9)
    assert p9.exists()
    assert p9.stat().st_size > 0

    # Verify media streams & duration bounds (60-90s)
    media_ok, media_errors = verify_output_media(p16)
    assert media_ok, f"Media verification failed: {media_errors}"


def test_mcp_tools():
    from mcp_server.server import get_pipeline_metrics, regenerate_shot, validate_storyboard

    val_res = validate_storyboard("storyboard.json")
    assert val_res["is_valid"] is True
    assert val_res["total_shots"] == 10

    regen_res = regenerate_shot("shot_01", "storyboard.json", dry_run=True)
    assert regen_res["success"] is True
    assert regen_res["shot_id"] == "shot_01"

    metrics_res = get_pipeline_metrics("runs.jsonl")
    assert "total_runs" in metrics_res

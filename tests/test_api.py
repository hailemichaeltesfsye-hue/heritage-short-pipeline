"""Tests for FastAPI backend bridge endpoints (isolated from root repo artifacts)."""

from pathlib import Path
import shutil
from fastapi.testclient import TestClient

import api.server as api_server
from api.server import (
    ShotUpdateRequest,
    app,
    approve_hitl,
    get_docs,
    get_health,
    get_metrics,
    get_outputs_manifest,
    get_storyboard,
    update_shot,
)


def test_api_health_direct():
    data = get_health()
    assert data["status"] == "ok"
    assert data["app"] == "heritage-short-pipeline"
    assert "ffmpeg" in data
    assert data["total_shots"] == 10


def test_api_get_storyboard_direct():
    data = get_storyboard()
    assert data["is_valid"] is True
    assert "storyboard" in data
    assert data["storyboard"]["title"] == "Hulum Neger Lebego New (ሁሉም ነገር ለበጎ ነው)"
    assert len(data["storyboard"]["shots"]) == 10


def test_api_update_shot_validation_direct(tmp_path, monkeypatch):
    # Work on an isolated copy of storyboard.json inside tmp_path
    temp_sb = tmp_path / "storyboard.json"
    shutil.copyfile("storyboard.json", temp_sb)
    monkeypatch.setattr(api_server, "STORYBOARD_PATH", temp_sb)

    req = ShotUpdateRequest(reason="Updated exploratory rationale with sufficient characters")
    data = update_shot("shot_01", req)
    assert data["success"] is True
    assert data["shot_id"] == "shot_01"
    assert data["shot"]["reason"] == req.reason


def test_api_outputs_manifest_direct():
    manifest = get_outputs_manifest()
    assert "files" in manifest
    assert "final_16x9.mp4" in manifest["files"]
    assert "final_9x16.mp4" in manifest["files"]
    assert "keyframes" in manifest


def test_api_metrics_direct():
    data = get_metrics()
    assert "summary" in data
    assert "model_breakdown" in data
    assert "stage_breakdown" in data
    assert "recent_runs" in data


def test_api_docs_direct():
    docs = get_docs()
    assert "DESIGN" in docs
    assert "ARCHITECTURE" in docs
    assert "EXPERIMENTS" in docs
    assert "FAILURES" in docs
    assert "COSTS" in docs
    assert "ETHICS" in docs
    assert "Hailemichael Tesfaye" in docs["ETHICS"]


def test_api_pipeline_approve_direct():
    data = approve_hitl()
    assert data["status"] == "approved"
    assert "approved_at" in data


def test_fastapi_route_registration():
    routes = {r.path: r for r in app.routes if hasattr(r, "path")}
    assert "/api/health" in routes
    assert "/api/storyboard" in routes
    assert "/api/outputs" in routes
    assert "/api/metrics" in routes
    assert "/api/docs" in routes
    assert "/api/pipeline/run" in routes
    assert "/api/pipeline/approve" in routes
    assert "/api/storyboard/shot/{shot_id}" in routes

    # Direct invocation through registered endpoint
    health_res = routes["/api/health"].endpoint()
    assert health_res["status"] == "ok"
    assert health_res["app"] == "heritage-short-pipeline"

"""Tests for FastAPI backend bridge endpoints."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.server import (
    ShotUpdateRequest,
    app,
    approve_hitl,
    get_docs,
    get_health,
    get_metrics,
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


def test_api_update_shot_validation_direct():
    # Read original shot
    with open("storyboard.json", "r", encoding="utf-8") as f:
        orig = json.load(f)
    orig_shot = next(s for s in orig["shots"] if s["shot_id"] == "shot_01")

    # Update shot
    req = ShotUpdateRequest(reason="Updated exploratory rationale with sufficient characters")
    data = update_shot("shot_01", req)
    assert data["success"] is True
    assert data["shot_id"] == "shot_01"
    assert data["shot"]["reason"] == req.reason

    # Restore original shot to keep repo pristine
    restore_req = ShotUpdateRequest(reason=orig_shot["reason"])
    restore_res = update_shot("shot_01", restore_req)
    assert restore_res["success"] is True


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


def test_fastapi_testclient_health():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

"""Tests for governance, consent enforcement, and runs.jsonl logging."""

import json
from pathlib import Path
import pytest
from agents.governance import check_ethics_consent, scan_for_secrets
from pipeline.logger import get_pipeline_metrics, log_run


def test_ethics_consent_checklist():
    ethics_ok, errors = check_ethics_consent()
    assert ethics_ok, f"Ethics check failed: {errors}"
    assert len(errors) == 0


def test_secret_scanner_clean():
    leaks = scan_for_secrets()
    assert len(leaks) == 0, f"Found potential secret leaks: {leaks}"


def test_structured_run_logger_and_metrics(tmp_path):
    test_log = tmp_path / "test_runs.jsonl"

    record1 = log_run(
        agent="AudioVoiceAgent",
        stage="narration",
        shot_id="shot_01",
        provider="google-genai",
        model="gemini-2.5-flash",
        parameters={"duration_sec": 6.0},
        seed=10101,
        latency_ms=120.5,
        estimated_cost_usd=0.0009,
        cache_hit=False,
        status="success",
        log_path=test_log,
    )
    assert record1["agent"] == "AudioVoiceAgent"
    assert record1["shot_id"] == "shot_01"

    record2 = log_run(
        agent="AudioVoiceAgent",
        stage="narration",
        shot_id="shot_02",
        provider="cache",
        model="cache-manifest",
        latency_ms=0.5,
        estimated_cost_usd=0.0,
        cache_hit=True,
        status="success",
        log_path=test_log,
    )

    metrics = get_pipeline_metrics(test_log)
    assert metrics["total_runs"] == 2
    assert metrics["cache_hits"] == 1
    assert metrics["cache_misses"] == 1
    assert metrics["cache_hit_ratio"] == 0.5
    assert metrics["total_cost_usd"] == 0.0009

"""Shared pytest fixtures ensuring tests never mutate root runs.jsonl, storyboard.json, or outputs/."""

from __future__ import annotations

from pathlib import Path
import pytest

import api.server as api_server
import pipeline.assemble as assemble_mod
import pipeline.cache as cache_mod
import pipeline.keyframes as keyframes_mod
import pipeline.logger as logger_mod
import pipeline.music as music_mod
import pipeline.narration as narration_mod
import pipeline.shots as shots_mod


@pytest.fixture(autouse=True)
def isolate_pipeline_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all mutable pipeline log, cache, and media output paths to tmp_path."""
    tmp_runs = tmp_path / "runs.jsonl"
    tmp_outputs = tmp_path / "outputs"
    tmp_narr = tmp_outputs / "narration"
    tmp_narr_am = tmp_narr / "am"
    tmp_narr_en = tmp_narr / "en"
    tmp_narr_rec = tmp_outputs / "narration_recorded"
    tmp_kf = tmp_outputs / "keyframes"
    tmp_ref = tmp_outputs / "reference"
    tmp_shots = tmp_outputs / "shots"
    tmp_clips_raw = tmp_outputs / "clips_raw"
    tmp_music = tmp_outputs / "music"
    tmp_manifest = tmp_outputs / ".cache_manifest.json"

    monkeypatch.setattr(logger_mod, "RUNS_LOG_PATH", tmp_runs)
    monkeypatch.setattr(api_server, "RUNS_LOG_PATH", tmp_runs)
    monkeypatch.setattr(api_server, "OUTPUTS_DIR", tmp_outputs)

    monkeypatch.setattr(cache_mod, "MANIFEST_PATH", tmp_manifest)

    monkeypatch.setattr(narration_mod, "OUTPUTS_NARRATION_DIR", tmp_narr)
    monkeypatch.setattr(narration_mod, "OUTPUTS_NARRATION_AM_DIR", tmp_narr_am)
    monkeypatch.setattr(narration_mod, "OUTPUTS_NARRATION_EN_DIR", tmp_narr_en)
    monkeypatch.setattr(narration_mod, "OUTPUTS_NARRATION_RECORDED_DIR", tmp_narr_rec)

    monkeypatch.setattr(keyframes_mod, "OUTPUTS_KEYFRAMES_DIR", tmp_kf)
    monkeypatch.setattr(keyframes_mod, "OUTPUTS_REFERENCE_DIR", tmp_ref)

    monkeypatch.setattr(shots_mod, "OUTPUTS_SHOTS_DIR", tmp_shots)
    monkeypatch.setattr(shots_mod, "OUTPUTS_CLIPS_RAW_DIR", tmp_clips_raw)
    monkeypatch.setattr(shots_mod, "OUTPUTS_NARRATION_DIR", tmp_narr)

    monkeypatch.setattr(music_mod, "OUTPUTS_MUSIC_DIR", tmp_music)

    monkeypatch.setattr(assemble_mod, "OUTPUTS_DIR", tmp_outputs)
    monkeypatch.setattr(assemble_mod, "OUTPUTS_NARRATION_DIR", tmp_narr)
    monkeypatch.setattr(assemble_mod, "OUTPUTS_SHOTS_DIR", tmp_shots)
    monkeypatch.setattr(assemble_mod, "OUTPUTS_KEYFRAMES_DIR", tmp_kf)
    monkeypatch.setattr(assemble_mod, "OUTPUTS_CLIPS_RAW_DIR", tmp_clips_raw)

    return tmp_path

"""Tests for SHA-256 single-shot cache invalidation across narration, keyframes, and video."""

import json
from pathlib import Path
import pytest
from pipeline.cache import (
    compute_shot_hash,
    invalidate_shot,
    is_shot_cached,
    load_manifest,
    update_shot_cache,
)


def test_shot_hash_determinism():
    shot_a = {
        "shot_id": "shot_01",
        "duration_sec": 6.0,
        "shot_type": "extreme_wide_shot",
        "visual_prompt": "Misty morning in Wegeltena",
        "motion_prompt": "Slow pan",
        "narration_am": "ታሪኬ የሚጀምረው በደላንታ ወረዳ ነው።",
        "subtitle_en": "My story begins in Delanta.",
        "seed": 10101,
    }
    style = {"visual_tone": "Warm golden-hour"}

    hash1 = compute_shot_hash(shot_a, style)
    hash2 = compute_shot_hash(shot_a, style)
    assert hash1 == hash2, "Hash must be deterministic"

    # Modifying narration changes hash
    shot_modified = dict(shot_a)
    shot_modified["narration_am"] = "የተቀየረ ታሪክ።"
    hash_modified = compute_shot_hash(shot_modified, style)
    assert hash1 != hash_modified, "Hash must change when shot narration changes"


def test_single_shot_invalidation_isolation(tmp_path):
    test_manifest_path = tmp_path / ".cache_manifest.json"

    # Simulate caching 10 shots with multi-stage artifacts
    for i in range(1, 11):
        shot_id = f"shot_{i:02d}"
        shot_hash = f"hash_{i:02d}_abc"
        artifacts = {
            "narration": f"outputs/narration/{shot_id}.wav",
            "keyframe": f"outputs/keyframes/{shot_id}.png",
            "shot_video": f"outputs/shots/{shot_id}.mp4",
        }
        update_shot_cache(shot_id, shot_hash, artifacts, test_manifest_path)

    manifest = load_manifest(test_manifest_path)
    assert len(manifest["shots"]) == 10

    # Invalidate only shot_04
    invalidated = invalidate_shot("shot_04", test_manifest_path)
    assert invalidated is True

    manifest_after = load_manifest(test_manifest_path)
    assert len(manifest_after["shots"]) == 9
    assert "shot_04" not in manifest_after["shots"]

    # All other 9 shots remain intact across all artifacts
    for i in (1, 2, 3, 5, 6, 7, 8, 9, 10):
        shot_id = f"shot_{i:02d}"
        assert shot_id in manifest_after["shots"]
        assert manifest_after["shots"][shot_id]["sha256"] == f"hash_{i:02d}_abc"
        assert "keyframe" in manifest_after["shots"][shot_id]["artifacts"]
        assert "shot_video" in manifest_after["shots"][shot_id]["artifacts"]


def test_is_shot_cached_validates_artifacts_exist(tmp_path):
    test_manifest_path = tmp_path / ".cache_manifest.json"
    dummy_wav = tmp_path / "shot_01.wav"
    dummy_wav.write_text("audio")

    update_shot_cache("shot_01", "hash_01", {"narration": str(dummy_wav)}, test_manifest_path)

    # Cache hit when file exists
    assert is_shot_cached("shot_01", "hash_01", [dummy_wav], test_manifest_path) is True

    # Cache miss when required file is deleted
    dummy_wav.unlink()
    assert is_shot_cached("shot_01", "hash_01", [dummy_wav], test_manifest_path) is False

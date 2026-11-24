"""SHA-256 shot caching engine for the heritage-short-pipeline.

Tracks per-shot content hashes in outputs/.cache_manifest.json to avoid
regenerating unchanged shots.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

MANIFEST_PATH = Path("outputs/.cache_manifest.json")


def compute_shot_hash(shot_data: Dict[str, Any], style_block: Optional[Dict[str, Any]] = None) -> str:
    """Compute a deterministic SHA-256 hash of a shot specification."""
    normalized = {
        "shot_id": shot_data.get("shot_id"),
        "duration_sec": shot_data.get("duration_sec"),
        "shot_type": shot_data.get("shot_type"),
        "visual_prompt": shot_data.get("visual_prompt", "").strip(),
        "motion_prompt": shot_data.get("motion_prompt", "").strip(),
        "narration_am": shot_data.get("narration_am", "").strip(),
        "subtitle_en": shot_data.get("subtitle_en", "").strip(),
        "seed": shot_data.get("seed"),
        "style_block": style_block or {},
    }
    encoded = json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_manifest(manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the cache manifest from disk."""
    resolved = Path(manifest_path) if manifest_path is not None else MANIFEST_PATH
    if not resolved.exists():
        return {"version": "1.0", "shots": {}}
    try:
        with open(resolved, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "shots": {}}


def save_manifest(manifest: Dict[str, Any], manifest_path: Optional[Path] = None) -> None:
    """Save the cache manifest to disk."""
    resolved = Path(manifest_path) if manifest_path is not None else MANIFEST_PATH
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def is_shot_cached(
    shot_id: str,
    shot_hash: str,
    required_artifacts: Optional[list[Path]] = None,
    manifest_path: Optional[Path] = None,
) -> bool:
    """Check if a shot is cached and all required artifacts exist on disk."""
    manifest = load_manifest(manifest_path)
    shot_entry = manifest.get("shots", {}).get(shot_id)
    if not shot_entry:
        return False
    if shot_entry.get("sha256") != shot_hash:
        return False
    if required_artifacts:
        for artifact in required_artifacts:
            if not artifact.exists() or artifact.stat().st_size == 0:
                return False
    return True


def update_shot_cache(
    shot_id: str,
    shot_hash: str,
    artifacts: Optional[Dict[str, str]] = None,
    manifest_path: Optional[Path] = None,
) -> None:
    """Update cache manifest entry for a single shot, merging artifacts when hash matches."""
    manifest = load_manifest(manifest_path)
    shots = manifest.setdefault("shots", {})
    existing = shots.get(shot_id, {})
    merged_artifacts: Dict[str, str] = {}
    if existing.get("sha256") == shot_hash and isinstance(existing.get("artifacts"), dict):
        merged_artifacts.update(existing["artifacts"])
    if artifacts:
        merged_artifacts.update(artifacts)

    shots[shot_id] = {
        "sha256": shot_hash,
        "artifacts": merged_artifacts,
    }
    save_manifest(manifest, manifest_path)


def invalidate_shot(shot_id: str, manifest_path: Optional[Path] = None) -> bool:
    """Invalidate a single shot from the cache."""
    manifest = load_manifest(manifest_path)
    shots = manifest.get("shots", {})
    if shot_id in shots:
        del shots[shot_id]
        save_manifest(manifest, manifest_path)
        return True
    return False

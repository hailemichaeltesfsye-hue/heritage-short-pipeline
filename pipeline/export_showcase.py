"""Export showcase data bundle for standalone static frontend deployment.

Packages storyboard.json, metrics, docs, media availability manifest, and real
dual-language media assets into frontend/public/showcase-data/ cleanly.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.server import get_docs, get_metrics
from pipeline.script import validate_storyboard

FRONTEND_PUBLIC_DIR = ROOT_DIR / "frontend" / "public" / "showcase-data"
OUTPUTS_DIR = ROOT_DIR / "outputs"


def export_showcase_bundle() -> Path:
    """Create a clean static showcase bundle synchronized with real disk artifacts."""
    FRONTEND_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    media_dir = FRONTEND_PUBLIC_DIR / "media"
    if media_dir.exists():
        shutil.rmtree(media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)

    # 1. Export Storyboard
    sb_path = ROOT_DIR / "storyboard.json"
    with open(sb_path, "r", encoding="utf-8") as f:
        sb_data = json.load(f)
    is_valid, errors, _ = validate_storyboard(sb_path, ROOT_DIR / "schema" / "storyboard.schema.json")
    with open(FRONTEND_PUBLIC_DIR / "storyboard.json", "w", encoding="utf-8") as f:
        json.dump({"is_valid": is_valid, "errors": errors, "storyboard": sb_data}, f, indent=2, ensure_ascii=False)

    # 2. Export Metrics
    metrics_data = get_metrics()
    with open(FRONTEND_PUBLIC_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2, ensure_ascii=False)

    # 3. Export Docs
    docs_data = get_docs()
    with open(FRONTEND_PUBLIC_DIR / "docs.json", "w", encoding="utf-8") as f:
        json.dump(docs_data, f, indent=2, ensure_ascii=False)

    # 4. Copy Real Available Media Assets & build availability manifest
    media_files_to_copy = [
        "final_16x9.mp4",
        "final_9x16.mp4",
        "final_16x9_am.mp4",
        "final_9x16_am.mp4",
        "radio_cut.mp4",
        "subtitles.srt",
        "subtitles_am.srt",
        "audio_master_mixed.wav",
        "audio_master_mixed_am.wav",
        "music/score_normalized.wav",
        "reference/character_sheet.png",
    ]

    available: dict[str, bool] = {}
    for rel_path in media_files_to_copy:
        src = OUTPUTS_DIR / rel_path
        exists = src.exists() and src.stat().st_size > 0
        available[rel_path] = exists
        if exists:
            dst = media_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    keyframes_available: list[str] = []
    keyframes_src = OUTPUTS_DIR / "keyframes"
    if keyframes_src.exists():
        keyframes_dst = media_dir / "keyframes"
        keyframes_dst.mkdir(parents=True, exist_ok=True)
        for img in sorted(keyframes_src.glob("*.png")):
            if img.stat().st_size > 0:
                shutil.copyfile(img, keyframes_dst / img.name)
                keyframes_available.append(img.stem)

    def _copy_wavs(src_dir: Path, dst_dir: Path) -> list[str]:
        found: list[str] = []
        if src_dir.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)
            for wav in sorted(src_dir.glob("*.wav")):
                if wav.stat().st_size > 0:
                    shutil.copyfile(wav, dst_dir / wav.name)
                    found.append(wav.stem)
        return found

    narration_en = _copy_wavs(OUTPUTS_DIR / "narration" / "en", media_dir / "narration" / "en")
    narration_am = _copy_wavs(OUTPUTS_DIR / "narration" / "am", media_dir / "narration" / "am")
    narration_legacy = _copy_wavs(OUTPUTS_DIR / "narration", media_dir / "narration")

    with open(FRONTEND_PUBLIC_DIR / "outputs.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "files": available,
                "keyframes": keyframes_available,
                "narration": narration_en or narration_am or narration_legacy,
                "narration_en": narration_en,
                "narration_am": narration_am,
            },
            f,
            indent=2,
        )

    print(f"Showcase bundle exported to: {FRONTEND_PUBLIC_DIR}")
    return FRONTEND_PUBLIC_DIR


if __name__ == "__main__":
    export_showcase_bundle()

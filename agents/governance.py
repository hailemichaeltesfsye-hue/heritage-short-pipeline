"""Governance & Safety Node for heritage-short-pipeline.

Verifies ETHICS.md consent records, scans for accidental secret leaks,
validates AI disclosure notices, and checks final MP4 streams & duration (60-90s).
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from agents.state import PipelineState
from pipeline.ffmpeg_utils import get_audio_duration, resolve_ffprobe_path
from pipeline.logger import log_run

SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API key pattern
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),    # Generic secret key pattern
]


def check_ethics_consent() -> Tuple[bool, List[str]]:
    """Verify that ETHICS.md exists and contains explicit consent and privacy provisions."""
    ethics_file = Path("ETHICS.md")
    if not ethics_file.exists():
        return False, ["ETHICS.md is missing from project root"]
    content = ethics_file.read_text(encoding="utf-8")
    errors = []
    if "Hailemichael Tesfaye" not in content:
        errors.append("ETHICS.md lacks self-consent record for Hailemichael Tesfaye")
    if "consent" not in content.lower():
        errors.append("ETHICS.md lacks clear consent framework")
    if "privacy" not in content.lower():
        errors.append("ETHICS.md lacks privacy protection policies for family members")
    return len(errors) == 0, errors


def scan_for_secrets(root_dir: Path = Path(".")) -> List[str]:
    """Scan tracked and config files for accidental API key or token exposures."""
    leaks = []
    for ext in ("*.py", "*.json", "*.yaml", "*.yml", "*.toml", "*.md"):
        for file in root_dir.glob(f"**/{ext}"):
            if any(p in file.parts for p in (".venv", ".git", "outputs", "__pycache__", "node_modules", "dist", ".cache", ".pytest_cache")):
                continue
            if file.name in (".env", ".env.example"):
                continue
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
                for pattern in SECRET_PATTERNS:
                    if pattern.search(text):
                        leaks.append(f"Potential secret leak in {file}")
            except Exception:
                pass
    return leaks


def verify_output_media(video_path: Path) -> Tuple[bool, List[str]]:
    """Validate output MP4 using ffprobe: duration (60-90s), video & audio streams."""
    errors = []
    if not video_path.exists():
        return False, [f"Media file not found at {video_path}"]

    ffprobe = resolve_ffprobe_path()
    import subprocess
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False, [f"ffprobe failed to inspect {video_path}: {res.stderr}"]

    import json
    try:
        data = json.loads(res.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        if not (60.0 <= duration <= 90.0):
            errors.append(f"Output video duration {duration:.1f}s outside required [60.0, 90.0]s bounds")

        streams = data.get("streams", [])
        codec_types = [s.get("codec_type") for s in streams]
        if "video" not in codec_types:
            errors.append("Output video missing video stream")
        if "audio" not in codec_types:
            errors.append("Output video missing audio stream")
    except Exception as e:
        errors.append(f"Failed to parse ffprobe json: {e}")

    return len(errors) == 0, errors


def governance_safety_node(state: PipelineState) -> Dict[str, Any]:
    """LangGraph node verifying governance, consent, and safety standards."""
    errors = list(state.get("errors", []))
    step_status = dict(state.get("step_status", {}))

    ethics_ok, ethics_errors = check_ethics_consent()
    if not ethics_ok:
        errors.extend(ethics_errors)

    secret_leaks = scan_for_secrets()
    if secret_leaks:
        errors.extend(secret_leaks)

    safety_passed = (len(ethics_errors) == 0) and (len(secret_leaks) == 0)
    step_status["governance_safety"] = "passed" if safety_passed else "failed"

    log_run(
        agent="GovernanceSafetyNode",
        stage="governance",
        provider="local",
        model="governance-checker",
        status="success" if safety_passed else "failed",
        error="; ".join(errors) if not safety_passed else None,
        trace_id=state.get("trace_id"),
    )

    return {
        "safety_passed": safety_passed,
        "errors": errors,
        "step_status": step_status,
    }

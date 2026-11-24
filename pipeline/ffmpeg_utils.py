"""FFmpeg binary resolution and execution helpers for heritage-short-pipeline.

Ensures FFmpeg 9.1+ is discoverable and provides deterministic video/audio operations.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional, Tuple

_CACHED_FFMPEG: Optional[str] = None
_CACHED_FFPROBE: Optional[str] = None


def resolve_ffmpeg_path() -> str:
    """Resolve ffmpeg binary path quickly, with direct winget lookup and caching."""
    global _CACHED_FFMPEG
    if _CACHED_FFMPEG:
        return _CACHED_FFMPEG

    found = shutil.which("ffmpeg")
    if found:
        _CACHED_FFMPEG = found
        return found

    # Direct Windows winget Gyan.FFmpeg installation check
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        known_base = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if known_base.exists():
            for p in known_base.glob("*FFmpeg*"):
                candidate = p / "ffmpeg-9.1-full_build" / "bin" / "ffmpeg.exe"
                if candidate.exists():
                    bin_dir = str(candidate.parent)
                    if bin_dir not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                    _CACHED_FFMPEG = str(candidate)
                    return _CACHED_FFMPEG

    _CACHED_FFMPEG = "ffmpeg"
    return _CACHED_FFMPEG


def resolve_ffprobe_path() -> str:
    """Resolve ffprobe binary path quickly, with direct winget lookup and caching."""
    global _CACHED_FFPROBE
    if _CACHED_FFPROBE:
        return _CACHED_FFPROBE

    found = shutil.which("ffprobe")
    if found:
        _CACHED_FFPROBE = found
        return found

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        known_base = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if known_base.exists():
            for p in known_base.glob("*FFmpeg*"):
                candidate = p / "ffmpeg-9.1-full_build" / "bin" / "ffprobe.exe"
                if candidate.exists():
                    _CACHED_FFPROBE = str(candidate)
                    return _CACHED_FFPROBE

    _CACHED_FFPROBE = "ffprobe"
    return _CACHED_FFPROBE


def run_ffmpeg(args: List[str]) -> Tuple[int, str, str]:
    """Run an FFmpeg command deterministically and return (exit_code, stdout, stderr)."""
    ffmpeg_exe = resolve_ffmpeg_path()
    cmd = [ffmpeg_exe, "-y", "-hide_banner", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def get_audio_duration(file_path: Path) -> float:
    """Get the duration in seconds of an audio file using ffprobe or wave fallback."""
    ffprobe_exe = resolve_ffprobe_path()
    if shutil.which(ffprobe_exe) or os.path.exists(ffprobe_exe):
        cmd = [
            ffprobe_exe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            try:
                return float(res.stdout.strip())
            except ValueError:
                pass

    try:
        import wave

        with wave.open(str(file_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        pass
    return 0.0


def create_silence_wav(output_path: Path, duration_sec: float, sample_rate: int = 24000) -> None:
    """Generate a clean uncompressed PCM WAV silence file of specified duration."""
    import math
    import struct
    import wave

    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_frames = int(duration_sec * sample_rate)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        silence_frame = struct.pack("<h", 0)
        wf.writeframes(silence_frame * num_frames)

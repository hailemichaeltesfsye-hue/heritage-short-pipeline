"""FFmpeg binary resolution and execution helpers for heritage-short-pipeline.

Ensures FFmpeg 9.1+ is discoverable and provides deterministic video/audio operations.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
from typing import List, Optional, Tuple
import wave

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
    """Get the duration in seconds of an audio/media file using ffprobe or wave fallback."""
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
        with wave.open(str(file_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        pass
    return 0.0


def compute_wav_rms(file_path: Path) -> float:
    """Compute normalized RMS amplitude in [0.0, 1.0] for an audio file.

    Uses Python wave for 16-bit PCM WAVs and falls back to FFmpeg decoding for other codecs.
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        return 0.0

    raw_frames = b""
    sampwidth = 2

    try:
        with wave.open(str(file_path), "rb") as wf:
            sampwidth = wf.getsampwidth()
            nframes = wf.getnframes()
            if nframes > 0 and sampwidth in (1, 2):
                raw_frames = wf.readframes(nframes)
    except Exception:
        raw_frames = b""

    if not raw_frames:
        ffmpeg_exe = resolve_ffmpeg_path()
        res = subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-i", str(file_path), "-f", "s16le", "-ac", "1", "-"],
            capture_output=True,
        )
        if res.returncode != 0 or not res.stdout:
            return 0.0
        raw_frames = res.stdout
        sampwidth = 2

    if sampwidth == 2:
        sample_count = len(raw_frames) // 2
        if sample_count == 0:
            return 0.0
        samples = struct.unpack(f"<{sample_count}h", raw_frames[: sample_count * 2])
        mean_sq = sum(s * s for s in samples) / float(sample_count)
        return math.sqrt(mean_sq) / 32768.0

    if sampwidth == 1:
        sample_count = len(raw_frames)
        if sample_count == 0:
            return 0.0
        mean_sq = sum((b - 128) * (b - 128) for b in raw_frames) / float(sample_count)
        return math.sqrt(mean_sq) / 128.0

    return 0.0


def pcm_to_wav(
    pcm_bytes: bytes,
    output_path: Path,
    sample_rate: int = 24000,
    channels: int = 1,
    sampwidth: int = 2,
) -> Path:
    """Wrap raw signed little-endian PCM bytes into a valid RIFF WAV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return output_path


def convert_audio_to_wav(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 24000,
    channels: int = 1,
) -> Path:
    """Transcode any audio file into standard 16-bit PCM RIFF WAV via FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ret, _, stderr = run_ffmpeg([
        "-i", str(input_path),
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        "-y", str(output_path),
    ])
    if ret != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg WAV conversion failed for {input_path}: {stderr}")
    return output_path


def create_silence_wav(output_path: Path, duration_sec: float, sample_rate: int = 24000) -> None:
    """Generate a clean uncompressed PCM WAV silence file of specified duration (dry-run only)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_frames = int(duration_sec * sample_rate)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        silence_frame = struct.pack("<h", 0)
        wf.writeframes(silence_frame * num_frames)

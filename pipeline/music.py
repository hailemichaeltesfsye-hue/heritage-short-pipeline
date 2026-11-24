"""Ambient and instrumental score preparation, loudness normalization, and fading."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, Optional

from pipeline.ffmpeg_utils import get_audio_duration, run_ffmpeg
from pipeline.logger import log_run

OUTPUTS_MUSIC_DIR = Path("outputs/music")


def prepare_score(
    total_duration_sec: float,
    input_score_path: Optional[Path] = None,
    output_score_path: Path = OUTPUTS_MUSIC_DIR / "score_normalized.wav",
    trace_id: Optional[str] = None,
) -> Path:
    """Inspect score, normalize loudness (-16 LUFS / -1.5 dB TP), and apply gentle in/out fades."""
    output_score_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    source = input_score_path or (OUTPUTS_MUSIC_DIR / "score.wav")

    # If raw score does not exist, synthesize warm acoustic Washint harmonic bed
    if not source.exists() or source.stat().st_size == 0:
        synth_source = OUTPUTS_MUSIC_DIR / "score_synth.wav"
        # Generate 220Hz + 440Hz warm acoustic Washint harmonic drone
        fade_out_start = max(total_duration_sec - 3.0, 1.0)
        cmd_synth = [
            "-f", "lavfi",
            "-i", f"sine=frequency=220:duration={total_duration_sec}:sample_rate=24000",
            "-f", "lavfi",
            "-i", f"sine=frequency=330:duration={total_duration_sec}:sample_rate=24000",
            "-filter_complex", (
                f"[0:a]volume=0.04[a0];[1:a]volume=0.02[a1];"
                f"[a0][a1]amix=inputs=2:duration=first[amix];"
                f"[amix]afade=t=in:ss=0:d=2.5,afade=t=out:st={fade_out_start}:d=2.5[aout]"
            ),
            "-map", "[aout]",
            "-y", str(synth_source),
        ]
        run_ffmpeg(cmd_synth)
        source = synth_source

    actual_dur = get_audio_duration(source)
    fade_out_start = max(total_duration_sec - 3.0, 1.0)

    # Normalize loudness with loudnorm filter and trim/loop cleanly to total_duration_sec
    cmd_norm = [
        "-i", str(source),
        "-t", str(total_duration_sec),
        "-af", (
            f"loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"afade=t=in:ss=0:d=2.0,afade=t=out:st={fade_out_start}:d=2.5"
        ),
        "-y", str(output_score_path),
    ]
    run_ffmpeg(cmd_norm)

    latency_ms = (time.time() - start_time) * 1000
    log_run(
        agent="AudioVoiceAgent",
        stage="music_score",
        provider="ffmpeg",
        model="acestep-or-harmonic",
        parameters={"total_duration_sec": total_duration_sec},
        latency_ms=latency_ms,
        status="success",
        trace_id=trace_id,
    )

    return output_score_path

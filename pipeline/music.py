"""Ambient and instrumental score preparation, loudness normalization, and fading."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Optional

from pipeline.ffmpeg_utils import get_audio_duration, run_ffmpeg
from pipeline.logger import log_run

OUTPUTS_MUSIC_DIR = Path("outputs/music")


def _find_real_score(music_dir: Path, input_score_path: Optional[Path]) -> Optional[Path]:
    """Prioritize real outputs/music/score.wav or ACE-Step candidate outputs."""
    if input_score_path is not None and input_score_path.exists() and input_score_path.stat().st_size > 0:
        return input_score_path

    candidates = [
        music_dir / "score.wav",
        music_dir / "score_candidate_1.wav",
        *sorted(music_dir.glob("acestep*.wav")),
    ]
    for cand in candidates:
        if cand.exists() and cand.stat().st_size > 0:
            return cand
    return None


def prepare_score(
    total_duration_sec: float,
    input_score_path: Optional[Path] = None,
    output_score_path: Optional[Path] = None,
    trace_id: Optional[str] = None,
) -> Path:
    """Inspect real score (or temporary ambient fallback), normalize (-16 LUFS), and fade in/out."""
    resolved_music_dir = OUTPUTS_MUSIC_DIR
    resolved_music_dir.mkdir(parents=True, exist_ok=True)
    resolved_output = Path(output_score_path) if output_score_path is not None else (resolved_music_dir / "score_normalized.wav")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    real_source = _find_real_score(resolved_music_dir, input_score_path)
    used_fallback = real_source is None
    source: Path

    if real_source is not None:
        source = real_source
    else:
        # Temporary ambient harmonic bed before Kaggle ACE-Step score is generated
        synth_source = resolved_music_dir / "score_synth.wav"
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
        ret_s, _, err_s = run_ffmpeg(cmd_synth)
        if ret_s != 0 or not synth_source.exists():
            raise RuntimeError(f"Failed generating ambient fallback score: {err_s}")
        source = synth_source

    actual_dur = get_audio_duration(source)
    fade_out_start = max(total_duration_sec - 3.0, 1.0)

    input_args = ["-stream_loop", "-1", "-i", str(source)] if actual_dur > 0 and actual_dur < total_duration_sec else ["-i", str(source)]
    cmd_norm = input_args + [
        "-t", str(total_duration_sec),
        "-af", (
            f"loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"afade=t=in:ss=0:d=2.0,afade=t=out:st={fade_out_start}:d=2.5"
        ),
        "-ar", "24000",
        "-ac", "1",
        "-y", str(resolved_output),
    ]
    ret_n, _, err_n = run_ffmpeg(cmd_norm)
    if ret_n != 0 or not resolved_output.exists():
        raise RuntimeError(f"Failed normalizing background score {source}: {err_n}")

    latency_ms = (time.time() - start_time) * 1000
    log_run(
        agent="AudioVoiceAgent",
        stage="music_score",
        provider="ffmpeg" if used_fallback else "kaggle_acestep",
        model="ffmpeg-ambient-fallback" if used_fallback else "ace-step-1.5",
        parameters={"total_duration_sec": total_duration_sec, "source": str(source)},
        latency_ms=latency_ms,
        status="fallback" if used_fallback else "success",
        error="outputs/music/score.wav missing; using temporary ambient harmonic fallback" if used_fallback else None,
        trace_id=trace_id,
    )

    return resolved_output

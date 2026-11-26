"""Motivational classical cinematic instrumental score generation, normalization, and ducking."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import time
from typing import List, Optional, Tuple
import wave

from pipeline.ffmpeg_utils import get_audio_duration, run_ffmpeg
from pipeline.logger import log_run

OUTPUTS_MUSIC_DIR = Path("outputs/music")


def synthesize_motivational_classical_score(
    output_path: Path,
    total_duration_sec: float,
    sample_rate: int = 24000,
) -> Path:
    """Synthesize an uplifting, motivational classical cinematic instrumental.

    Features:
    - Warm expressive piano arpeggios (percussive hammer attack + exponential decay)
    - Sustained warm cello & string pads with gentle vibrato and smooth chord transitions
    - Emotional three-phase progression:
        * 0–30s: Intimate, reflective childhood in Wegeltena/Delanta
        * 30–55s: Expanding harmonic richness during Abinet study & Deaconhood
        * 55–80s: Soaring motivational crescendo building toward Software Engineering & resolve
    - Strictly instrumental with zero vocals.
    """
    total_samples = int(total_duration_sec * sample_rate)
    buffer = [0.0] * total_samples
    inv_sr = 1.0 / sample_rate

    # D Major scale note frequencies (Hz)
    D2, E2, Fs2, G2, A2, B2 = 73.42, 82.41, 92.50, 98.00, 110.00, 123.47
    C3, Cs3, D3, E3, Fs3, G3, A3, B3 = 130.81, 138.59, 146.83, 164.81, 185.00, 196.00, 220.00, 246.94
    Cs4, D4, E4, Fs4, G4, A4, B4 = 277.18, 293.66, 329.63, 369.99, 392.00, 440.00, 493.88
    Cs5, D5, E5, Fs5, G5, A5, B5 = 554.37, 587.33, 659.25, 739.99, 783.99, 880.00, 987.77
    Cs6, D6 = 1108.73, 1174.66

    def add_piano_note(start_sec: float, freq: float, dur: float, velocity: float) -> None:
        start_idx = int(start_sec * sample_rate)
        if start_idx >= total_samples:
            return
        n_samples = min(int(dur * sample_rate), total_samples - start_idx)
        two_pi_f = 2.0 * math.pi * freq

        # Piano harmonic overtone weights
        decay_rate = 1.4 + (freq / 400.0) * 0.8
        for n in range(n_samples):
            t = n * inv_sr
            # Hammer strike percussive attack (12ms) + exponential body decay
            attack = 1.0 - math.exp(-t * 80.0)
            env = attack * math.exp(-t * decay_rate)
            harmonics = (
                math.sin(two_pi_f * t)
                + 0.55 * math.sin(2.0 * two_pi_f * t) * math.exp(-t * 0.8)
                + 0.28 * math.sin(3.0 * two_pi_f * t) * math.exp(-t * 1.5)
                + 0.14 * math.sin(4.0 * two_pi_f * t) * math.exp(-t * 2.5)
                + 0.06 * math.sin(5.0 * two_pi_f * t) * math.exp(-t * 3.5)
            )
            buffer[start_idx + n] += velocity * env * harmonics

    def add_string_pad(start_sec: float, dur_sec: float, notes: List[float], vol: float) -> None:
        start_idx = int(start_sec * sample_rate)
        if start_idx >= total_samples:
            return
        n_samples = min(int(dur_sec * sample_rate), total_samples - start_idx)
        fade_time = min(1.2, dur_sec * 0.3)

        for n in range(n_samples):
            t = n * inv_sr
            # Smooth string bow attack and release envelope
            if t < fade_time:
                env = t / fade_time
            elif t > dur_sec - fade_time:
                env = max(0.0, (dur_sec - t) / fade_time)
            else:
                env = 1.0

            # Subtle expressive string vibrato (5.2 Hz)
            vib = 1.0 + 0.005 * math.sin(2.0 * math.pi * 5.2 * t)

            sample_sum = 0.0
            for f in notes:
                two_pi_f = 2.0 * math.pi * f * vib
                # Bowed string harmonics (warm sawtooth-like balance)
                sample_sum += (
                    math.sin(two_pi_f * t)
                    + 0.45 * math.sin(2.0 * two_pi_f * t)
                    + 0.25 * math.sin(3.0 * two_pi_f * t)
                    + 0.12 * math.sin(4.0 * two_pi_f * t)
                )
            buffer[start_idx + n] += (vol / max(1, len(notes))) * env * sample_sum

    # Harmonic progression chords (each ~4.0 seconds)
    # Root, cello bass, strings triad, piano arpeggio pitch set
    chord_progression: List[Tuple[float, List[float], List[float]]] = [
        # Part 1: Childhood in Delanta & Kombolcha (0–32s)
        (D2, [D3, Fs3, A3], [D4, Fs4, A4, D5, A4, Fs4]),       # 0–4s: Opening card D Major
        (B2, [B2, D3, Fs3], [B3, D4, Fs4, B4, Fs4, D4]),       # 4–8s: Shot 1 Wegeltena Bm
        (G2, [G2, B2, D3], [G3, B3, D4, G4, D4, B3]),          # 8–12s: Shot 2 Mesno Amba G
        (A2, [A2, Cs3, E3], [A3, Cs4, E4, A4, E4, Cs4]),       # 12–16s: Shot 3 Mother A
        (Fs2, [D3, Fs3, A3], [D4, Fs4, A4, D5, A4, Fs4]),      # 16–20s: Shot 4 Hospital D/F#
        (G2, [G2, B2, D3], [G3, B3, D4, G4, D4, B3]),          # 20–24s: G Major
        (E2, [E2, G2, B2], [E3, G3, B3, E4, B3, G3]),          # 24–28s: Em
        (A2, [A2, Cs3, E3], [A3, D4, E4, A4, E4, Cs4]),        # 28–32s: Asus4 -> A

        # Part 2: Abinet study & Deaconhood (32–56s)
        (D2, [D3, Fs3, A3], [Fs4, A4, D5, Fs5, D5, A4]),       # 32–36s: Shot 5 Ge'ez D Major
        (B2, [B2, D3, Fs3], [Fs4, B4, D5, Fs5, D5, B4]),       # 36–40s: Shot 6 Deacon Bm
        (G2, [G2, B2, D3], [G4, B4, D5, G5, D5, B4]),          # 40–44s: G Major
        (A2, [A2, Cs3, E3], [A4, Cs5, E5, A5, E5, Cs5]),       # 44–48s: A Major
        (B2, [B2, D3, Fs3], [B4, D5, Fs5, B5, Fs5, D5]),       # 48–52s: Shot 7 Exams Bm
        (A2, [A2, Cs3, E3], [A4, Cs5, E5, A5, E5, Cs5]),       # 52–56s: A Major

        # Part 3: Engineering, Horizon & Inspiring Climax (56–80s)
        (D2, [D3, Fs3, A3, D4], [D4, Fs4, A4, D5, Fs5, D5]),   # 56–60s: Shot 8 Software Lab
        (B2, [B2, D3, Fs3, B3], [B4, D5, Fs5, B5, Fs5, D5]),   # 60–64s: B Minor
        (G2, [G2, B2, D3, G3], [G4, B4, D5, G5, B5, G5]),      # 64–68s: Shot 9 Horizon Overlook
        (A2, [A2, Cs3, E3, A3], [A4, Cs5, E5, A5, Cs6, A5]),   # 68–72s: A Major
        (D2, [D3, Fs3, A3, D4], [D4, Fs4, A4, D5, Fs5, D5]),   # 72–76s: Shot 10 Direct Address
        (D2, [D2, A2, D3, Fs3, A3, D4], [D4, Fs4, A4, D5]),    # 76–80s: AI Slate Final Resolve
    ]

    chord_dur = 4.0
    for idx, (bass_note, string_chord, arpeggio_notes) in enumerate(chord_progression):
        start_t = idx * chord_dur
        if start_t >= total_duration_sec:
            break

        # Dynamic intensity: gradual build from reflective to soaring motivational climax
        phase_ratio = min(1.0, start_t / max(1.0, total_duration_sec - 8.0))
        string_vol = 0.08 + 0.12 * phase_ratio
        piano_vel = 0.14 + 0.14 * phase_ratio

        # 1. Cello sustained bass note
        add_string_pad(start_t, chord_dur + 0.5, [bass_note], string_vol * 1.2)

        # 2. String ensemble pad (mid register warmth)
        add_string_pad(start_t, chord_dur + 0.4, string_chord, string_vol)

        # 3. Piano arpeggios (8 notes per 4-second bar)
        note_step = chord_dur / len(arpeggio_notes)
        for n_idx, note_f in enumerate(arpeggio_notes):
            n_time = start_t + n_idx * note_step
            # Accent first and fourth note gently
            accent = 1.25 if n_idx in (0, len(arpeggio_notes) // 2) else 0.95
            add_piano_note(n_time, note_f, dur=note_step * 1.8, velocity=piano_vel * accent)

            # In Part 3 (Engineering climax), double the piano octave for classical grandeur
            if phase_ratio > 0.65 and n_idx % 2 == 0:
                add_piano_note(n_time, note_f * 0.5, dur=note_step * 2.2, velocity=piano_vel * 0.7)

    # Normalize peak amplitude to prevent clipping before writing WAV
    max_val = max(abs(s) for s in buffer) or 1.0
    scale = 0.88 / max_val

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Pack 16-bit signed PCM
        raw_bytes = bytearray(total_samples * 2)
        for i, val in enumerate(buffer):
            int_sample = max(-32767, min(32767, int(val * scale * 32767.0)))
            struct.pack_into("<h", raw_bytes, i * 2, int_sample)
        wf.writeframes(raw_bytes)

    return output_path


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
    """Prepare motivational classical cinematic instrumental, normalize (-16 LUFS), and fade in/out."""
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
        # Synthesize uplifting motivational classical instrumental (piano arpeggios + cello/string pads)
        synth_raw = resolved_music_dir / "score_synth_raw.wav"
        synthesize_motivational_classical_score(synth_raw, total_duration_sec=total_duration_sec)

        # Apply concert hall acoustics & warmth via soft reverb and equalization
        synth_reverbed = resolved_music_dir / "score_synth.wav"
        cmd_reverb = [
            "-i", str(synth_raw),
            "-af", (
                "aecho=0.8:0.85:35|60|120|240:0.35|0.28|0.2|0.12,"
                "equalizer=f=300:t=q:w=1:g=2,"
                "equalizer=f=3200:t=q:w=1.5:g=1.5,"
                "lowpass=f=7500,highpass=f=40"
            ),
            "-y", str(synth_reverbed),
        ]
        ret_rev, _, err_rev = run_ffmpeg(cmd_reverb)
        if ret_rev == 0 and synth_reverbed.exists():
            source = synth_reverbed
        else:
            source = synth_raw

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
        provider="classical_synth" if used_fallback else "kaggle_acestep",
        model="motivational-classical-instrumental" if used_fallback else "ace-step-1.5",
        parameters={"total_duration_sec": total_duration_sec, "source": str(source)},
        latency_ms=latency_ms,
        status="fallback" if used_fallback else "success",
        error=None if not used_fallback else "outputs/music/score.wav missing; synthesized motivational classical instrumental",
        trace_id=trace_id,
    )

    return resolved_output


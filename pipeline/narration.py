"""Dynamic Amharic voice narration generation using Gemini 3.8 Flash and Edge-TTS fallback."""

from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import time
from typing import Any, Coroutine, Dict, Optional, Tuple, TypeVar

import edge_tts

from pipeline.ffmpeg_utils import (
    compute_wav_rms,
    convert_audio_to_wav,
    create_silence_wav,
    get_audio_duration,
    pcm_to_wav,
)
from pipeline.logger import log_run

OUTPUTS_NARRATION_DIR = Path("outputs/narration")
TARGET_SAMPLE_RATE = 24000
MIN_AUDIO_RMS = 0.001
PREFERRED_GEMINI_AUDIO_MODELS = [
    "models/gemini-3.8-flash",
    "models/gemini-3.7-flash",
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
]
EDGE_TTS_AMHARIC_VOICES = ("am-ET-AmehaNeural", "am-ET-MekdesNeural")

_T = TypeVar("_T")


def _run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async coroutine safely from either sync code or an active event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def discover_gemini_tts_model(client: Any) -> Tuple[str, str]:
    """Discover live Gemini Flash audio model, prioritizing gemini-3.8-flash (no deprecated 2.5-flash)."""
    try:
        models = list(client.models.list())
        available_names = [getattr(m, "name", "") for m in models if getattr(m, "name", "")]
        for pref in PREFERRED_GEMINI_AUDIO_MODELS:
            short_pref = pref.removeprefix("models/")
            for name in available_names:
                if name == pref or name.endswith(f"/{short_pref}") or short_pref in name:
                    return name, "google-genai"
    except Exception:
        pass
    return "models/gemini-3.8-flash", "google-genai"


def _parse_pcm_sample_rate(mime_type: str) -> int:
    match = re.search(r"rate=(\d+)", mime_type or "", re.IGNORECASE)
    if match:
        return int(match.group(1))
    return TARGET_SAMPLE_RATE


def _write_audio_bytes_as_wav(raw_data: bytes, mime_type: str, output_path: Path) -> None:
    """Convert raw audio/L16 PCM or encoded audio bytes into a 24000 Hz mono RIFF WAV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mime_lower = (mime_type or "").lower()

    if raw_data.startswith(b"RIFF"):
        tmp_wav = output_path.with_suffix(".gemini_tmp.wav")
        tmp_wav.write_bytes(raw_data)
        try:
            convert_audio_to_wav(tmp_wav, output_path, sample_rate=TARGET_SAMPLE_RATE, channels=1)
        finally:
            tmp_wav.unlink(missing_ok=True)
        return

    if "l16" in mime_lower or "pcm" in mime_lower or not mime_lower:
        src_rate = _parse_pcm_sample_rate(mime_lower)
        if src_rate == TARGET_SAMPLE_RATE:
            pcm_to_wav(raw_data, output_path, sample_rate=TARGET_SAMPLE_RATE, channels=1, sampwidth=2)
        else:
            tmp_pcm_wav = output_path.with_suffix(".pcm_tmp.wav")
            pcm_to_wav(raw_data, tmp_pcm_wav, sample_rate=src_rate, channels=1, sampwidth=2)
            try:
                convert_audio_to_wav(tmp_pcm_wav, output_path, sample_rate=TARGET_SAMPLE_RATE, channels=1)
            finally:
                tmp_pcm_wav.unlink(missing_ok=True)
        return

    ext = ".mp3" if "mp3" in mime_lower or "mpeg" in mime_lower else ".audio"
    tmp_audio = output_path.with_suffix(f".gemini_tmp{ext}")
    tmp_audio.write_bytes(raw_data)
    try:
        convert_audio_to_wav(tmp_audio, output_path, sample_rate=TARGET_SAMPLE_RATE, channels=1)
    finally:
        tmp_audio.unlink(missing_ok=True)


def synthesize_edge_tts_amharic(
    text: str,
    output_path: Path,
    voices: Tuple[str, ...] = EDGE_TTS_AMHARIC_VOICES,
) -> str:
    """Synthesize genuine spoken Amharic speech via Edge-TTS and convert to 24kHz mono WAV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp3 = output_path.with_suffix(".edge_tmp.mp3")
    last_error: Optional[Exception] = None

    for voice in voices:
        try:
            async def _save() -> None:
                communicate = edge_tts.Communicate(text=text, voice=voice, rate="-5%")
                await communicate.save(str(tmp_mp3))

            _run_async(_save())
            if not tmp_mp3.exists() or tmp_mp3.stat().st_size == 0:
                raise RuntimeError(f"Edge-TTS produced empty audio for voice {voice}")

            convert_audio_to_wav(tmp_mp3, output_path, sample_rate=TARGET_SAMPLE_RATE, channels=1)
            dur = get_audio_duration(output_path)
            rms = compute_wav_rms(output_path)
            if dur <= 0.1 or rms < MIN_AUDIO_RMS:
                raise RuntimeError(f"Edge-TTS output failed integrity check (dur={dur:.2f}s, rms={rms:.6f})")
            return voice
        except Exception as exc:
            last_error = exc
        finally:
            tmp_mp3.unlink(missing_ok=True)

    raise RuntimeError(f"All Edge-TTS Amharic voices failed: {last_error}")


def _extract_audio_part(response: Any) -> Optional[Tuple[bytes, str]]:
    """Extract raw audio bytes and MIME type from Gemini GenerateContentResponse."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                raw = inline_data.data
                if isinstance(raw, str):
                    raw = base64.b64decode(raw)
                mime_type = getattr(inline_data, "mime_type", "") or ""
                if len(raw) > 0:
                    return bytes(raw), mime_type
    return None


def _attempt_gemini_narration(
    api_key: str,
    narration_am: str,
    output_path: Path,
    max_attempts: int = 3,
) -> Tuple[Optional[str], Optional[str]]:
    """Try Gemini audio generation with backoff on 503 UNAVAILABLE.

    Returns:
        (model_used, None) on verified non-silent audio success, or (None, error_message) on failure.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    primary_model, _ = discover_gemini_tts_model(client)
    candidate_models = [primary_model] + [m for m in PREFERRED_GEMINI_AUDIO_MODELS if m != primary_model]

    prompt = (
        "Speak this Amharic film narration aloud naturally with calm, warm Ethiopian highland "
        f"documentary pacing. Output audio only:\n\n{narration_am}"
    )

    last_error = "Gemini returned no audio"
    for model_name in candidate_models[:2]:
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                    ),
                )
                extracted = _extract_audio_part(response)
                if not extracted:
                    last_error = f"{model_name} returned empty AUDIO payload"
                    break

                raw_bytes, mime_type = extracted
                _write_audio_bytes_as_wav(raw_bytes, mime_type, output_path)

                dur = get_audio_duration(output_path)
                rms = compute_wav_rms(output_path)
                if dur <= 0.1 or rms < MIN_AUDIO_RMS:
                    output_path.unlink(missing_ok=True)
                    last_error = f"{model_name} produced silent audio (dur={dur:.2f}s, rms={rms:.6f})"
                    break

                return model_name, None
            except Exception as exc:
                last_error = f"{model_name} error: {exc}"
                err_str = str(exc).upper()
                is_transient = "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                if is_transient and attempt < max_attempts:
                    time.sleep(min(2 ** (attempt - 1), 4.0))
                    continue
                break

    return None, last_error


def generate_shot_narration(
    shot: Dict[str, Any],
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, str, float]:
    """Generate Amharic narration audio for a single shot.

    In live mode (dry_run=False), never writes silent audio and never logs status='success'
    if synthesis fails. Falls back cleanly to Edge-TTS (am-ET-AmehaNeural) when Gemini fails.
    """
    resolved_dir = Path(output_dir) if output_dir is not None else OUTPUTS_NARRATION_DIR
    resolved_dir.mkdir(parents=True, exist_ok=True)

    shot_id = shot["shot_id"]
    duration_sec = float(shot.get("duration_sec", 6.0))
    narration_am = shot.get("narration_am", "").strip()
    output_path = resolved_dir / f"{shot_id}.wav"

    start_time = time.time()

    # Deterministic silence WAV is allowed ONLY in explicit dry_run mode
    if dry_run:
        create_silence_wav(output_path, duration_sec=duration_sec)
        latency_ms = (time.time() - start_time) * 1000
        log_run(
            agent="AudioVoiceAgent",
            stage="narration",
            shot_id=shot_id,
            provider="local",
            model="dry-run-generator",
            parameters={"duration_sec": duration_sec, "language": "am"},
            seed=shot.get("seed"),
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
            cache_hit=False,
            status="success",
            trace_id=trace_id,
        )
        return True, output_path, "dry-run-generator", latency_ms

    # Live execution: attempt Gemini 3.8 Flash native AUDIO first
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    gemini_error: Optional[str] = None

    if api_key and not api_key.startswith("your_"):
        try:
            model_used, gemini_error = _attempt_gemini_narration(api_key, narration_am, output_path)
            if model_used and output_path.exists():
                latency_ms = (time.time() - start_time) * 1000
                measured_dur = get_audio_duration(output_path)
                log_run(
                    agent="AudioVoiceAgent",
                    stage="narration",
                    shot_id=shot_id,
                    provider="google-genai",
                    model=model_used,
                    parameters={"duration_sec": round(measured_dur, 2), "sample_rate": TARGET_SAMPLE_RATE, "language": "am"},
                    seed=shot.get("seed"),
                    latency_ms=latency_ms,
                    estimated_cost_usd=0.00015,
                    cache_hit=False,
                    status="success",
                    trace_id=trace_id,
                )
                return True, output_path, model_used, latency_ms
        except Exception as exc:
            gemini_error = str(exc)
    else:
        gemini_error = "GEMINI_API_KEY missing or unconfigured"

    # Real spoken Amharic fallback via Edge-TTS (am-ET-AmehaNeural / am-ET-MekdesNeural)
    try:
        voice_used = synthesize_edge_tts_amharic(narration_am, output_path)
        latency_ms = (time.time() - start_time) * 1000
        measured_dur = get_audio_duration(output_path)
        log_run(
            agent="AudioVoiceAgent",
            stage="narration",
            shot_id=shot_id,
            provider="edge-tts",
            model=voice_used,
            parameters={"duration_sec": round(measured_dur, 2), "sample_rate": TARGET_SAMPLE_RATE, "language": "am"},
            seed=shot.get("seed"),
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
            cache_hit=False,
            status="fallback",
            error=gemini_error,
            trace_id=trace_id,
        )
        return True, output_path, voice_used, latency_ms
    except Exception as edge_exc:
        output_path.unlink(missing_ok=True)
        latency_ms = (time.time() - start_time) * 1000
        combined_error = f"Gemini failed ({gemini_error}); Edge-TTS failed ({edge_exc})"
        log_run(
            agent="AudioVoiceAgent",
            stage="narration",
            shot_id=shot_id,
            provider="google-genai+edge-tts",
            model="narration-pipeline",
            parameters={"target_duration_sec": duration_sec, "language": "am"},
            seed=shot.get("seed"),
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
            cache_hit=False,
            status="failed",
            error=combined_error,
            trace_id=trace_id,
        )
        return False, output_path, "failed", latency_ms

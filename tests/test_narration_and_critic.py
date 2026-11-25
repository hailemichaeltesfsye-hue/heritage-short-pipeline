"""Regression tests for real Amharic TTS, L16 PCM conversion, Keyframe fallbacks, and RMS Quality Critic."""

import io
import json
import math
from pathlib import Path
import struct
import wave
from PIL import Image
import pytest

from agents.critic import MAX_RETRIES, quality_critic_node, should_retry_audio
from pipeline.ffmpeg_utils import compute_wav_rms, create_silence_wav, get_audio_duration
import pipeline.keyframes as keyframes_mod
import pipeline.logger as logger_mod
import pipeline.narration as narration_mod


def _make_sine_pcm(duration_sec: float = 1.0, sample_rate: int = 24000, freq: float = 440.0) -> bytes:
    num_samples = int(duration_sec * sample_rate)
    frames = [int(0.25 * 32767 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)]
    return struct.pack(f"<{num_samples}h", *frames)


def _write_tone_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(_make_sine_pcm(duration_sec=duration_sec, sample_rate=sample_rate))


def test_pcm_l16_to_wav_conversion(tmp_path):
    """Verify raw audio/L16 PCM bytes convert cleanly to playable 24kHz mono RIFF WAV."""
    out_wav = tmp_path / "shot_pcm.wav"
    pcm_bytes = _make_sine_pcm(duration_sec=1.0, sample_rate=24000)

    narration_mod._write_audio_bytes_as_wav(pcm_bytes, "audio/L16;rate=24000", out_wav)

    assert out_wav.exists()
    assert out_wav.read_bytes()[:4] == b"RIFF"
    with wave.open(str(out_wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
    assert get_audio_duration(out_wav) == pytest.approx(1.0, abs=0.05)
    assert compute_wav_rms(out_wav) > 0.1


def test_narration_live_falls_back_to_edge_tts_and_logs_fallback(tmp_path, monkeypatch):
    """When Gemini fails in live mode, Edge-TTS runs cleanly and logs status='fallback' with error."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setattr(
        narration_mod,
        "_attempt_gemini_narration",
        lambda *args, **kwargs: (None, "503 UNAVAILABLE from Gemini"),
    )

    def fake_edge(text: str, output_path: Path, voices=narration_mod.EDGE_TTS_AMHARIC_VOICES) -> str:
        _write_tone_wav(output_path, duration_sec=2.0, sample_rate=24000)
        return "am-ET-AmehaNeural"

    monkeypatch.setattr(narration_mod, "synthesize_edge_tts_amharic", fake_edge)

    shot = {"shot_id": "shot_01", "duration_sec": 6.0, "narration_am": "ሰላም", "seed": 10101}
    ok, wav_path, model_used, _ = narration_mod.generate_shot_narration(shot, dry_run=False, language="am")

    assert ok is True
    assert model_used == "am-ET-AmehaNeural"
    assert wav_path.exists()
    assert wav_path.parent.name == "am"
    assert compute_wav_rms(wav_path) > 0.1

    log_lines = (tmp_path / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    last_rec = json.loads(log_lines[-1])
    assert last_rec["status"] == "fallback"
    assert last_rec["provider"] == "edge-tts"
    assert "503 UNAVAILABLE" in last_rec["error"]


def test_narration_live_both_providers_fail_never_writes_silence(tmp_path, monkeypatch):
    """In live mode (dry_run=False), total TTS failure must return False and never write silence WAV."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setattr(
        narration_mod,
        "_attempt_gemini_narration",
        lambda *args, **kwargs: (None, "404 model not found"),
    )
    monkeypatch.setattr(
        narration_mod,
        "synthesize_edge_tts_amharic",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Edge network down")),
    )

    shot = {"shot_id": "shot_01", "duration_sec": 6.0, "narration_am": "ሰላም", "seed": 10101}
    ok, wav_path, model_used, _ = narration_mod.generate_shot_narration(shot, dry_run=False, language="am")

    assert ok is False
    assert model_used == "failed"
    assert not wav_path.exists()

    last_rec = json.loads((tmp_path / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last_rec["status"] == "failed"


def test_english_edge_tts_synthesizes_non_silent_wav(tmp_path, monkeypatch):
    """Primary English narration path writes non-silent 24kHz WAV into outputs/narration/en/."""
    def fake_en_edge(text: str, output_path: Path, voice: str = narration_mod.EDGE_TTS_EN_VOICE) -> str:
        _write_tone_wav(output_path, duration_sec=2.0, sample_rate=24000)
        return voice

    monkeypatch.setattr(narration_mod, "synthesize_edge_tts_english", fake_en_edge)

    shot = {
        "shot_id": "shot_01",
        "duration_sec": 6.0,
        "narration_en": "My story begins in the cool mornings of Wegeltena.",
        "subtitle_en": "My story begins in the cool mornings of Wegeltena, Delanta.",
        "seed": 10101,
    }
    ok, wav_path, model_used, _ = narration_mod.generate_shot_narration(shot, dry_run=False, language="en")

    assert ok is True
    assert model_used == "en-US-AndrewMultilingualNeural"
    assert wav_path.exists()
    assert wav_path.parent.name == "en"
    assert compute_wav_rms(wav_path) > 0.1

    last_rec = json.loads((tmp_path / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last_rec["status"] == "success"
    assert last_rec["provider"] == "edge-tts"
    assert last_rec["parameters"]["language"] == "en"


def test_human_recorded_override_logs_provider(tmp_path):
    """When outputs/narration_recorded/{lang}/{shot_id}.wav exists, use it and log provider='human-recorded'."""
    rec_wav = tmp_path / "outputs" / "narration_recorded" / "am" / "shot_01.wav"
    _write_tone_wav(rec_wav, duration_sec=2.0, sample_rate=24000)

    shot = {"shot_id": "shot_01", "duration_sec": 6.0, "narration_am": "ሰላም", "seed": 10101}
    ok, wav_path, model_used, _ = narration_mod.generate_shot_narration(shot, dry_run=False, language="am")

    assert ok is True
    assert model_used == "human-recorded"
    assert wav_path.exists()
    assert wav_path.parent.name == "am"
    assert compute_wav_rms(wav_path) > 0.1

    last_rec = json.loads((tmp_path / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last_rec["provider"] == "human-recorded"
    assert last_rec["status"] == "success"


def test_keyframes_live_never_writes_fake_placeholder_on_failure(tmp_path, monkeypatch):
    """When dry_run=False and both Cloudflare + Gemini Image fail, never generate orange gradient circle PNG."""
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    out_png = tmp_path / "outputs" / "keyframes" / "shot_01.png"
    ok, path, model_used, _ = keyframes_mod.generate_image_cloudflare(
        prompt="Highland sunrise", output_path=out_png, seed=101, dry_run=False
    )

    assert ok is False
    assert model_used == "failed"
    assert not path.exists()


def test_keyframes_live_uses_gemini_image_fallback(tmp_path, monkeypatch):
    """When Cloudflare is missing/failing, real Gemini Image fallback succeeds cleanly."""
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")

    def fake_gemini_img(prompt: str, output_path: Path, api_key: str):
        img = Image.new("RGB", (64, 64), color=(180, 120, 60))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), "PNG")
        return "models/gemini-3.1-flash-image", None

    monkeypatch.setattr(keyframes_mod, "_try_gemini_image", fake_gemini_img)

    out_png = tmp_path / "outputs" / "keyframes" / "shot_01.png"
    ok, path, model_used, _ = keyframes_mod.generate_image_cloudflare(
        prompt="Highland sunrise", output_path=out_png, seed=101, dry_run=False
    )

    assert ok is True
    assert model_used == "models/gemini-3.1-flash-image"
    assert path.exists()

    last_rec = json.loads((tmp_path / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last_rec["provider"] == "google-genai"
    assert last_rec["status"] == "fallback"


def test_quality_critic_rejects_silent_wav_in_live_mode(tmp_path):
    """QualityCriticAgent must detect near-zero RMS silence and fail in live mode."""
    silent_wav = tmp_path / "outputs" / "narration" / "shot_01.wav"
    create_silence_wav(silent_wav, duration_sec=2.0)

    state = {
        "storyboard_data": {"shots": [{"shot_id": "shot_01", "duration_sec": 2.0}]},
        "target_shot_id": "shot_01",
        "dry_run": False,
        "audio_files": {"shot_01": str(silent_wav)},
        "retry_counts": {},
        "errors": [],
        "step_status": {},
        "trace_id": "critic-test",
    }

    # Retry loop up to MAX_RETRIES
    for attempt in range(MAX_RETRIES):
        res = quality_critic_node(state)
        state["retry_counts"] = res["retry_counts"]
        state["step_status"] = res["step_status"]
        state["errors"] = res["errors"]
        assert state["step_status"]["quality_critic"] == "retry"
        assert should_retry_audio(state) == "audio_voice"

    # After MAX_RETRIES, critic must fail cleanly and halt
    final_res = quality_critic_node(state)
    state["step_status"] = final_res["step_status"]
    state["errors"] = final_res["errors"]
    assert state["step_status"]["quality_critic"] == "failed"
    assert should_retry_audio(state) == "end"
    assert any("Silent narration detected" in e or "silent narration detected" in e for e in state["errors"])

    # Audible WAV in live mode passes immediately
    tone_wav = tmp_path / "outputs" / "narration" / "shot_02.wav"
    _write_tone_wav(tone_wav, duration_sec=2.0)
    ok_state = {
        "storyboard_data": {"shots": [{"shot_id": "shot_02", "duration_sec": 2.0}]},
        "target_shot_id": "shot_02",
        "dry_run": False,
        "audio_files": {"shot_02": str(tone_wav)},
        "retry_counts": {},
        "errors": [],
        "step_status": {},
        "trace_id": "critic-ok",
    }
    ok_res = quality_critic_node(ok_state)
    assert ok_res["step_status"]["quality_critic"] == "passed"
    assert len(ok_res["errors"]) == 0

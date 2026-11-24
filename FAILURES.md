# Failure Modes & Self-Healing Policies

## 1. Root-Cause Incident Post-Mortems (Discovered & Fixed)

### Incident #1: Silent Amharic Narration Masked as `status="success"`
- **Root Cause**:
  1. `pipeline/narration.py` prioritized deprecated `models/gemini-2.5-flash` and requested `response_mime_type="audio/wav"`, which Gemini API rejected (`404` / unsupported MIME config).
  2. An overly broad `except Exception: pass` swallowed the API failure, silently called `create_silence_wav()`, and STILL logged `status="success"` with cost `$0.00015` in `runs.jsonl`.
  3. `QualityCriticAgent` only checked `duration > 0.0` (which pure zero-PCM WAVs satisfied), allowing 74 seconds of complete silence through to `final_16x9.mp4`.
- **Permanent Fix**:
  - Prioritized `models/gemini-3.8-flash` using `response_modalities=["AUDIO"]` (without `speech_config` rejected by `v1`) with exponential backoff on `503 UNAVAILABLE`.
  - Added `pcm_to_wav()` + `convert_audio_to_wav()` converting raw `audio/L16` PCM streams cleanly to `24000 Hz` mono RIFF WAVs.
  - Integrated `edge-tts` (`am-ET-AmehaNeural` / `am-ET-MekdesNeural`) as a genuine neural Amharic speech fallback logging `status="fallback"` alongside the exact Gemini exception string.
  - Refused any silent fallback audio when `dry_run=False`.
  - Upgraded `QualityCriticAgent` to compute normalized WAV RMS amplitude (`compute_wav_rms() >= 0.001`) and fail + invalidate silent shots when `dry_run=False`.

### Incident #2: Synthetic Orange Circle Placeholders Shipped in Place of Real Keyframes
- **Root Cause**:
  1. Cloudflare Workers AI `@cf/black-forest-labs/flux-2-klein-4b` requires `multipart/form-data`, whereas the original code sent `application/json` with unsupported `num_steps` / `guidance` keys; fallback `@cf/black-forest-labs/flux-1-schnell` expects `steps` (not `num_steps`) and rejects unmapped keys.
  2. When Cloudflare calls failed in live mode, `generate_image_cloudflare` silently invoked `create_deterministic_reference_image()` (an orange gradient + sun circle), poisoning `outputs/keyframes/` and `.cache_manifest.json`.
- **Permanent Fix**:
  - Corrected `flux-2-klein-4b` to send `multipart/form-data` (`prompt`, `width`, `height`, `seed`) and `flux-1-schnell` to send clean JSON (`prompt`, `steps`, `seed`), normalizing all returned images cleanly to RGB PNG via Pillow.
  - Added genuine second-provider fallback via Gemini Image models (`models/gemini-3.1-flash-image` / `models/gemini-2.5-flash-image`).
  - Completely banned `create_deterministic_reference_image()` when `dry_run=False`: total provider failure fails loudly (`status="failed"`) rather than rendering fake shapes.

### Incident #3: Square Keyframe Stretching, Mode-3 Pan Drift & Unused Vertical End Card
- **Root Cause**:
  1. Feeding `1024x1024` (1:1) images straight to FFmpeg `zoompan=s=1920x1080` stretched subjects horizontally.
  2. `shots.py` mode 3 computed `x_expr = "iw/2-(ih/zoom/2)"` (height instead of width), drifting off-center.
  3. `assemble.py` hardcoded Ken Burns unconditionally even when `outputs/clips_raw/` existed, rendered `end_card_9x16.mp4` but cropped `final_16x9.mp4` sides instead, and used PIL's tiny default bitmap font lacking Ethiopic glyph coverage.
- **Permanent Fix**:
  - Pre-scaled & center-cropped (`scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080`) before `zoompan`, fixed `iw`, loaded `ebrima.ttf` for sharp Latin + Ethiopic end cards, conformed `outputs/clips_raw/` when present, and composed native `end_card_9x16.mp4` into `final_9x16.mp4`.

### Incident #4: Pytest Mutating Root `runs.jsonl` and `outputs/`
- **Root Cause**:
  - Module-level defaults such as `def log_run(..., log_path=RUNS_LOG_PATH)` evaluated at import time, plus integration tests (`test_langgraph_pipeline_dry_run`, `test_api_update_shot_validation_direct`, `test_mcp_tools`) writing directly to root `runs.jsonl`, `storyboard.json`, and `outputs/`.
- **Permanent Fix**:
  - Changed all path defaults to `Optional[Path] = None` resolved dynamically at call time.
  - Added `tests/conftest.py` (`autouse=True`) isolating all test I/O via `tmp_path` and `monkeypatch`, and isolated `test_api_update_shot_validation_direct` to a copied `storyboard.json`.

---

## 2. Runtime Failure & Mitigation Policy Matrix

| Failure Mode | Trigger | Impact | Self-Healing / Mitigation Policy |
|---|---|---|---|
| **Gemini 3.8 Flash Audio 503 / Empty** | Transient API 503 or unsupported modality | Shot lacks Gemini audio | Exponential backoff retry (up to 3x), then genuine spoken Amharic fallback via `edge-tts` (`am-ET-AmehaNeural`) logged as `status="fallback"`. |
| **Silent / Corrupt Narration WAV** | Zero PCM amplitude (`RMS < 0.001`) | Muted video section | `QualityCriticAgent` invalidates shot cache, routes back to `AudioVoiceAgent` (max 3 retries), or halts graph before video assembly. |
| **Cloudflare FLUX Error / Rate Limit** | 4xx/5xx or quota limit on Workers AI | Keyframe call fails | Switches to `flux-1-schnell`, then falls back to live Gemini Image (`gemini-3.1-flash-image` / `gemini-2.5-flash-image`). Zero synthetic fakes in live mode. |
| **Kaggle GPU OOM / Missing Clip** | Wan 2.2 script unexecuted or failed | No clip in `clips_raw/` | Falls back to varied-direction, aspect-safe FFmpeg `zoompan` Ken Burns motion shot and logs `fallback: ken_burns`. |
| **Missing Kaggle ACE-Step Score** | `outputs/music/score.wav` absent | No acoustic music track | Generates temporary FFmpeg ambient harmonic bed and honestly logs `status="fallback"` with `ffmpeg-ambient-fallback`. |
| **Amharic Narration Duration Variance** | Spoken duration longer than estimate | Audio clipped by video | `calculate_dynamic_shot_durations` adds `+0.5s` breathing room per shot, scaling total film cleanly within `60-90s`. |
| **Subtitle Text Overflow** | English translation exceeds line width | Text clips edge of screen | `wrap_subtitle_text` enforces `max 2 lines` and `max 40 chars/line`. |
| **Secret Leak in Config** | Accidental commit of `AIza...` / token | Security breach | `GovernanceSafetyNode` scans files and halts graph before network calls. |

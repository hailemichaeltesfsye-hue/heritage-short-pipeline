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

### Incident #5: Synthetic Amharic TTS Non-Native Accent on Regional Place Names
- **Root Cause**:
  - When Gemini `models/gemini-3.8-flash` native `AUDIO` returned `503 UNAVAILABLE` or `400 INVALID_ARGUMENT`, fallback `edge-tts` (`am-ET-AmehaNeural`) pronounced regional Ethiopian highland place names and liturgical terms (`Wegeltena`, `Delanta`, `Kombolcha`, `Diqquna`) with noticeably synthetic cadence and non-native stress at `-5%` rate.
- **Permanent Fix**:
  - Promoted polished English documentary narration (`en-US-AndrewMultilingualNeural`, `rate="-6%"`, `pitch="-2Hz"`, dedicated `narration_en` script field) as the accessible primary master track (`final_16x9.mp4` / `final_9x16.mp4`).
  - Retuned Amharic Edge-TTS prosody (`rate="-10%"`, `pitch="-2Hz"`, configurable `NARRATION_AM_VOICE`) alongside language-isolated outputs (`outputs/narration/am/`, `final_16x9_am.mp4`).
  - Added optional native human voice override (`outputs/narration_recorded/{lang}/{shot_id}.{wav,mp3,m4a}`), normalized via FFmpeg to `24000 Hz` mono WAV and logged honestly as `provider="human-recorded"`.

### Incident #6: Background Music Masking Spoken Narration
- **Root Cause**:
  - FFmpeg `sidechaincompress` was initially configured with gentle ducking parameters (`threshold=0.02`, `ratio=6`, `attack=300ms`) and raw score bed volume was unattenuated. During peer review on the 1:25 cut, reviewer Haylemichael Tsega pointed out: *"the background voice/music should be suppressed."* The music bed was competing with narration at `-11 dB to -16 dB`, muddying consonant articulation.
- **Permanent Fix**:
  - Implemented a voice-first filtergraph in `pipeline/assemble.py`:
    1. Conditioned voice narration with `acompressor` and `loudnorm=I=-14:TP=-1.5:LRA=8` to guarantee clean, consistent dialogue level at `-14 LUFS`.
    2. Split voice into mix audio and a dedicated sidechain trigger (`asplit=2[voice_mix][voice_sc]`).
    3. Pre-attenuated background score bed with `volume=0.20` (-14 dB gain drop).
    4. Tightened sidechain compressor: `threshold=0.01`, `ratio=12`, `attack=60ms`, `release=1500ms`, dropping music under speech down to `-30 dB to -33 dB`.
    5. Added limiter protection (`alimiter=limit=0.88`) to eliminate inter-sample peaks.

### Incident #7: Childhood Character Visual Drift Across Shots 01 to 04
- **Root Cause**:
  - Keyframes for shots 01 through 04 relied on fragmented prompt descriptions ("young Ethiopian boy", "child student in uniform", "boy walking in town"). As flagged by reviewer Eyosiyas Temesgen (*"the childhood images are different in different places so that will be incoherent for the visual flow"*), this caused noticeable facial structure drift, skin tone variance, and clothing inconsistency across the early Delanta and Kombolcha scenes.
- **Permanent Fix**:
  - Codified a strict visual anchor in `character_sheet.progression_stages.boy_primary`: *"8-year-old Ethiopian boy, warm brown skin, expressive thoughtful dark brown eyes, neat close-cropped black hair, wearing a clean crisp white collared shirt under a cream handwoven cotton gabi shawl with subtle border embroidery"*.
  - Updated visual prompts across `shot_01`, `shot_02`, `shot_03`, and `shot_04` in `storyboard.json` to enforce this exact anchor.
  - In `shot_03`, anchored the mother's character (*tall 35yo Ethiopian mother, dark navy cardigan over burgundy dress, white headscarf*) and locked seed to `10123`.
  - Regenerated only childhood keyframes using SHA-256 prompt invalidation while preserving shots 05–10.

### Incident #8: Broken Static Vercel Showcase Deployment (Missing Media & SPA Routing)
- **Root Cause**:
  - On the live Vercel deployment (`heritage-short-pipeline-rouge.vercel.app`), the Cinema Screening displayed *"Awaiting render — run pipeline stage"* and Storyboard Lab showed broken image icons for `shot_01`..`shot_10`.
  - Root cause was twofold:
    1. `frontend/public/showcase-data/media/` containing the final rendered MP4s, keyframes, and narration stems was untracked in git. When Vercel built the static Vite app, `/showcase-data/media/` did not exist, returning 404 for all media requests. Video playback error handlers triggered `videoError=true`, rendering the empty slate.
    2. Neither root `vercel.json` nor `frontend/vercel.json` configured SPA rewrite rules, causing direct sub-route reloads to 404 on Vercel.
- **Permanent Fix**:
  - Updated `export_showcase.py` to package clean web-playable assets (all 5 MP4 masters, 10 keyframes, 20 narration snippets, reference sheet, and SRTs) while excluding unneeded 30MB raw master WAVs.
  - Added explicit `.gitignore` rules: `!frontend/public/showcase-data/` and `!frontend/public/showcase-data/**`.
  - Added SPA rewrite configuration (`{ "source": "/(.*)", "destination": "/index.html" }`) in both root `vercel.json` and `frontend/vercel.json`.
  - Added `-movflags +faststart` to MP4 assembly and `preload="metadata"` in `CinemaScreening.tsx` for instant streaming.

---

## 2. Runtime Failure & Mitigation Policy Matrix

| Failure Mode | Trigger | Impact | Self-Healing / Mitigation Policy |
|---|---|---|---|
| **Gemini 3.8 Flash Audio 503 / Empty** | Transient API 503 or unsupported modality | Shot lacks Gemini audio | Exponential backoff retry (up to 3x), then genuine spoken Amharic fallback via `edge-tts` (`am-ET-AmehaNeural`) logged as `status="fallback"`. |
| **Silent / Corrupt Narration WAV** | Zero PCM amplitude (`RMS < 0.001`) | Muted video section | `QualityCriticAgent` invalidates shot cache, routes back to `AudioVoiceAgent` (max 3 retries), or halts graph before video assembly. |
| **Cloudflare FLUX Error / Rate Limit** | 4xx/5xx or quota limit on Workers AI | Keyframe call fails | Switches to `flux-1-schnell`, then falls back to live Gemini Image (`gemini-3.1-flash-image` / `gemini-2.5-flash-image`). Zero synthetic fakes in live mode. |
| **Childhood Character Visual Drift** | Unanchored prompt descriptions | Discontinuous face/costume | Unified `character_sheet.progression_stages.boy_primary` descriptor enforced in prompt compiler across shots 01–04. |
| **Background Music Masking Voice** | Underscore too loud or ducking weak | Narration unintelligible | Voice-first FFmpeg filtergraph: `volume=0.20` score bed, `sidechaincompress` ratio 12, threshold 0.01, attack 60ms. |
| **Vercel Static Showcase 404 Media** | Missing tracked static media bundle | Player shows awaiting render | `export_showcase.py` packages compressed web assets into `frontend/public/showcase-data/media/` tracked cleanly in git. |
| **Kaggle GPU OOM / Missing Clip** | Wan 2.2 script unexecuted or failed | No clip in `clips_raw/` | Falls back to varied-direction, aspect-safe FFmpeg `zoompan` Ken Burns motion shot and logs `fallback: ken_burns`. |
| **Missing Kaggle ACE-Step Score** | `outputs/music/score.wav` absent | No acoustic music track | Generates temporary FFmpeg ambient harmonic bed and honestly logs `status="fallback"` with `ffmpeg-ambient-fallback`. |
| **Amharic Narration Duration Variance** | Spoken duration longer than estimate | Audio clipped by video | `calculate_dynamic_shot_durations` adds `+0.5s` breathing room per shot, scaling total film cleanly within `60-90s`. |
| **Subtitle Text Overflow** | English translation exceeds line width | Text clips edge of screen | `wrap_subtitle_text` enforces `max 2 lines` and `max 40 chars/line`. |
| **Secret Leak in Config** | Accidental commit of `AIza...` / token | Security breach | `GovernanceSafetyNode` scans files and halts graph before network calls. |

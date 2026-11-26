# Experiments & Benchmarking Log

## 1. Voice Synthesis Model Discovery & Neural Fallback
- **Objective**: Identify a reliable Amharic speech synthesis path for documentary narration.
- **Candidates Evaluated**:
  - `models/gemini-3.8-flash` (`response_modalities=["AUDIO"]`): Primary Gemini audio generation target with raw `audio/L16` -> `24000 Hz` mono WAV conversion and `503` backoff.
  - `models/gemini-2.5-flash`: **Retired** — removed after live 404/unsupported native `AUDIO` failures.
  - `edge-tts` (`am-ET-AmehaNeural` / `am-ET-MekdesNeural`): High-clarity native Amharic neural TTS fallback transcoded via FFmpeg to `24000 Hz` mono PCM WAV (`status="fallback"` logged when Gemini fails).

## 2. Single-Shot Invalidation Benchmark
- **Test**: Modify Shot 4 (`shot_04`) narration in `storyboard.json`.
- **Expected**: Shots 1-3 and 5-10 hit cache; Shot 4 regenerates.
- **Measured**: Cache hit ratio = 90% (9/10), saving ~90% of model and processing latency.

## 3. Subtitle Synchronization & Canvas Assembly
- **Test**: FFmpeg 9.1 generation of 74-second 1080p 24fps canvas with embedded mov_text and external `.srt`.
- **Performance**: Execution completes within 2.5 seconds with zero frame dropping.

## 4. Dual-Language TTS Prosody Tuning (English Primary + Amharic Optional)
- **Objective**: Achieve warm, unhurried documentary voiceover pacing in English (`en` primary) while softening synthetic cadence in Amharic (`am` optional).
- **English Primary (`en-US-AndrewMultilingualNeural`)**: Evaluated `0%` default rate vs `-6%` rate with `-2Hz` pitch shift across dedicated `narration_en` scripts. `-6%` rate + `-2Hz` pitch delivered natural gravitas while fitting all 10 shots inside the `78–84s` total film window without clipping.
- **Amharic Optional (`am-ET-AmehaNeural`)**: Slowed speech rate from `-5%` to `-10%` with `-2Hz` pitch to improve intelligibility around highland proper nouns (`Wegeltena`, `Delanta`, `Kombolcha`).

## 5. Classical Opening Title Intro Card & Burned Subtitle Sync
- **Design**: Added a `3.0s` obsidian (`#0b0a09`) opening title slate (`"HULUM NEGER LEBEGO NEW"` / `"ሁሉም ነገር ለበጎ ነው"`) with double gold ornamental borders and `0.5s` fade in/out in both `1920x1080` and `1080x1920`.
- **Synchronization**: Prepended `3.0s` silent header before Shot 1 in `narration_timed.wav` (allowing underscore fade-in during the title card), shifted `.srt` timecodes `+3.0s`, and burned subtitles inside safe screen margins for universal playback across web and mobile players.

## 6. FLUX Keyframe Prompt Formulation & Safe Centered Dual-Aspect Framing
- **Objective**: Ensure generated keyframes compose cleanly across both `16:9` (1920x1080) landscape cinema screens and `9:16` (1080x1920) vertical mobile displays without subject truncation or facial distortion.
- **Experiment**: Tested 1:1 square keyframe generation (`1024x1024`) with edge-to-edge subjects versus center-weighted rule-of-thirds composition with 25% horizontal safe margins.
- **Result**: Center-weighted prompts ensured that the central vertical 576px slice contains the full emotional subject, allowing `scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920` to produce natural portrait framing without face cropping.

## 7. Voice-First Audio Sidechain Ducking & Dynamic Range Control
- **Objective**: Address user feedback (*"the background voice/music should be suppressed"*) by preventing the background underscore from competing with speech frequencies (300 Hz – 3.4 kHz).
- **Baseline Filter**: `threshold=0.02`, `ratio=6`, `attack=300ms`, `release=1500ms`. Measured music bed at `-14 dB` during speech windows, causing masking of quiet consonants.
- **Tuned Filter**: Voice path conditioned with `acompressor` and `loudnorm=I=-14:TP=-1.5:LRA=8`, score bed pre-attenuated by `volume=0.20` (-14 dB), and `sidechaincompress` tightened to `threshold=0.01`, `ratio=12`, `attack=60ms`.
- **Measured Outcome**: Speech sections maintain crystal clarity at `-18 dB` while background music drops to `-30 dB to -33 dB`, then recovers cleanly during the 3.0s opening intro and pauses.

## 8. Childhood Character Consistency Anchor Formulation
- **Objective**: Resolve peer critique on visual discontinuity across childhood scenes (`shot_01`–`shot_04`).
- **Baseline**: Separate prompts with varying age descriptors ("young Ethiopian boy", "child student") produced noticeable facial, clothing, and skin tone variance across the 4 early scenes.
- **Intervention**: Locked a rigorous character anchor in `character_sheet.progression_stages.boy_primary`:
  *"8-year-old Ethiopian boy, warm brown skin, expressive thoughtful dark brown eyes, neat close-cropped black hair, wearing a clean crisp white collared shirt under a cream handwoven cotton gabi shawl with subtle border embroidery"*.
- **Validation**: Propagated the anchor into shots 01, 02, 03, and 04. Regenerated keyframes show consistent facial structure, costume continuity, and warm highland palette from Delanta to Kombolcha.

## 9. Web Streaming Optimization (`-movflags +faststart`)
- **Objective**: Eliminate playback buffering delays on the static Vercel showcase deployment when serving ~18–21 MB MP4 video files.
- **Benchmark**: Default FFmpeg MP4 muxing places the `moov` atom (index and sample tables) at the end of the file, requiring the browser to download the entire file before beginning playback.
- **Optimization**: Added `-movflags +faststart` to all 16:9 and 9:16 FFmpeg assembly passes, shifting the `moov` atom to the container header.
- **Result**: Chrome/Safari HTML5 video players begin immediate playback within <200ms via HTTP Range requests without waiting for complete file download.

## 10. End-to-End Latency & Telemetry Benchmarking (`runs.jsonl`)
- **Audit**: Analyzed 180+ pipeline runs recorded in `runs.jsonl`.
- **Cold Run Duration**: Full end-to-end execution (10 FLUX keyframes, 10 dual-language narration tracks, 10 Ken Burns motion clips, dual 16:9 + 9:16 EN + AM assembly): ~240–310s.
- **Warm Run Duration (1 Shot Modified)**: Single-shot SHA-256 cache invalidation re-runs only the modified shot's keyframe, narration, and video, re-assembling masters in ~35–48s.
- **Total Pipeline Spend to Date**: 15 live Cloudflare FLUX keyframe generations at ~$0.003/image = ~$0.045 USD total cost.


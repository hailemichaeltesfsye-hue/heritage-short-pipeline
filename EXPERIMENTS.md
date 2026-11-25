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

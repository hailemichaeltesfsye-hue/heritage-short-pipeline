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

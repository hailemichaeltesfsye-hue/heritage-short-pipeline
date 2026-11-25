# System Design: AI Filmmaking Pipeline — The Heritage Short

## 1. System Objectives
The Heritage Short Pipeline automates the progression from an autobiographical storyboard specification to a synchronized audio-visual radio cut and complete cinematic dual-aspect short film (`16:9` and `9:16`).

## 2. Pipeline State Lifecycle
The pipeline is governed by `agents.state.PipelineState`, passed through LangGraph nodes:
1. `storyboard_path`: Input file location.
2. `is_valid_schema`: Boolean flag set by `StoryDirectorAgent`.
3. `safety_passed`: Boolean flag set by `GovernanceSafetyNode`.
4. `shot_hashes`: Mapping of `shot_id` -> SHA-256 hash calculated by `VisualConsistencyAgent`.
5. `keyframes`: Mapping of `shot_id` -> generated keyframe PNG path.
6. `audio_files`: Mapping of `shot_id` -> generated narration WAV path.
7. `shots_video`: Mapping of `shot_id` -> conformed or Ken Burns motion MP4 path.
8. `score_path`: Path to normalized soundtrack.
9. `final_16x9_path`: Path to assembled 16:9 master video.
10. `final_9x16_path`: Path to assembled 9:16 vertical video.
11. `errors`: Cumulative list of pipeline errors.
12. `retry_counts`: Mapping of `shot_id` -> retry attempt count managed by `QualityCriticAgent`.
13. `step_status`: Status dictionary of each node's execution.

## 3. Cache Invalidation Mechanics
- The cache key is computed over:
  - `shot_id`, `duration_sec`, `shot_type`, `visual_prompt`, `motion_prompt`, `narration_am`, `subtitle_en`, `seed`, and `style_block`.
- Stored in `outputs/.cache_manifest.json`.
- Modifying a single shot's narration, visual prompt, or seed triggers cache invalidation only for that single shot across keyframes, narration, and video clips. All other 9 shots result in zero-latency cache hits.

## 4. Keyframe Generation & Dual-Crop Framing
- Cloudflare Workers AI FLUX REST API generates 1024x1024 / 1280x720 keyframes.
- Prompts enforce centered subject composition with safe margins so that both `16:9` widescreen and `9:16` vertical crops retain emotional focal intimacy.
- Character sheet reference (`outputs/reference/character_sheet.png`) anchors facial consistency across childhood, deaconhood, and university engineering.

## 5. Audio Ducking, Loudness & Dual Video Assembly
- Spoken narration durations (`en` primary / `am` optional) are measured via `ffprobe`. Visual durations dynamically add `+0.5s` breathing room, scaled strictly within `60.0–90.0s` total runtime (`3.0s` opening card + `10` dynamic shots + `3.0s` AI end card).
- **Classical Opening Title Intro Card**: A `3.0s` obsidian-warm charcoal (`#0b0a09`) card with double ornamental gold borders, corner flourishes, serif typography (`"HULUM NEGER LEBEGO NEW"` / `"ሁሉም ነገር ለበጎ ነው"`), and `0.5s` fade in/out is prepended before Shot 1.
- Narration track prepends `3.0s` silence before Shot 1 so the underscore fades in gently across the intro card, while `.srt` subtitle timestamps shift `+3.0s` to match Shot 1 onset.
- Background underscore is ducked beneath voice narration using FFmpeg `sidechaincompress`:
  - `threshold=0.02`, `ratio=6`, `attack=300ms`, `release=1500ms`.
- Master audio is normalized via FFmpeg `loudnorm` targeting `-14 LUFS` and `-1.0 dB TP`.
- Crisp English subtitles (`max 2 lines`, `max 40 chars/line`) are burned directly inside safe screen margins onto both `16:9` and `9:16` exports alongside external `.srt` files.
- 3-second visible AI end card is rendered and appended cleanly to all exports:
  - English (Primary): `outputs/final_16x9.mp4` (`1920x1080`) & `outputs/final_9x16.mp4` (`1080x1920`)
  - Amharic (Optional): `outputs/final_16x9_am.mp4` & `outputs/final_9x16_am.mp4`

## 6. Dual-Language Narration Architecture
- CLI supports `--language en|am|both` (default `en`).
- Cached audio cleanly separates outputs under `outputs/narration/en/{shot_id}.wav` and `outputs/narration/am/{shot_id}.wav`.
- English primary synthesis uses `edge-tts` (`en-US-AndrewMultilingualNeural`, `rate="-6%"`, `pitch="-2Hz"`) from dedicated `narration_en` voiceover scripts.
- Amharic optional synthesis tries Gemini `models/gemini-3.8-flash` (`AUDIO`) first, falling back to `edge-tts` (`am-ET-AmehaNeural` / configurable `NARRATION_AM_VOICE`, `rate="-10%"`, `pitch="-2Hz"`).
- Optional native human voice recordings placed in `outputs/narration_recorded/{lang}/{shot_id}.{wav,mp3,m4a}` are automatically normalized to `24000 Hz` mono WAV via FFmpeg and logged with `provider="human-recorded"`.

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
- Amharic narration durations are measured via `ffprobe`. Visual durations dynamically add `+0.5s` breathing room.
- Background underscore is ducked beneath voice narration using FFmpeg `sidechaincompress`:
  - `threshold=0.02`, `ratio=6`, `attack=300ms`, `release=1500ms`.
- Master audio is normalized via FFmpeg `loudnorm` targeting `-14 LUFS` and `-1.0 dB TP`.
- Clean English `.srt` subtitles enforce `max 2 lines` and `max 40 chars/line`.
- 3-second visible AI end card is rendered and appended cleanly to both exports:
  - `outputs/final_16x9.mp4`: 1920x1080 24fps
  - `outputs/final_9x16.mp4`: 1080x1920 24fps

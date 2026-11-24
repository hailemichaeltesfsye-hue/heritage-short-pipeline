# Failure Modes & Self-Healing Policies

## 1. Catalog of Potential Failures & Mitigations

| Failure Mode | Trigger | Impact | Self-Healing / Mitigation Policy |
|---|---|---|---|
| **Cloudflare FLUX API 404/Unavailable** | Model `@cf/black-forest-labs/flux-2-klein-4b` offline | Keyframe call fails | Automatically falls back to `@cf/black-forest-labs/flux-1-schnell`, then offline deterministic reference generator. |
| **Kaggle GPU OOM / Missing Clip** | Wan 2.2 script unexecuted or failed | No clip in `clips_raw/` | Automatically switches to varied-direction FFmpeg `zoompan` Ken Burns motion shot and logs `fallback: ken_burns`. |
| **Amharic Narration Duration Variance** | Real TTS speed faster or slower | Narration clipped by visual | `calculate_dynamic_shot_durations` dynamically adds `+0.5s` breathing room per shot, scaling total film into 60-90s bounds. |
| **Subtitle Text Overflow** | English translation too long | Subtitles wrap offscreen | `wrap_subtitle_text` strictly enforces `max 2 lines` and `max 40 chars/line`. |
| **Audio Ducking Filter Failure** | Complex sidechaincompress graph error | Assembly halts | Automatic fallback to volume-scaled `amix` with smooth transitions. |
| **Secret Leak in Config** | Accidental commit of `AIza...` key | Security breach | `GovernanceSafetyNode` halts graph before network calls. |

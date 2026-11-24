# Multi-Agent Architecture: The Heritage Short

## 1. Multi-Agent Topology

The pipeline follows a directed state graph orchestrated via LangGraph:

```
[Start]
   │
   ▼
[GovernanceSafetyNode] ── (fails) ──► [END]
   │
   ▼ (passes)
[StoryDirectorAgent] ─── (fails) ──► [END]
   │
   ▼ (passes)
[SupervisorNode] ── (HITL checkpoint / auto)
   │
   ▼
[VisualConsistencyAgent] (Cloudflare FLUX Keyframes + Character Sheet)
   │
   ▼
[AudioVoiceAgent] ◄──────────────┐
   │                             │
   ▼                             │ (Retry on failure, <=3 retries)
[QualityCriticAgent] ────────────┘
   │
   ▼ (Passes)
[VideoEditorAgent] (Kaggle Wan 2.2 / Ken Burns + Ducking + Dual Assembly)
   │
   ▼
[GovernanceSafetyNode] (Post-assembly stream & duration verification)
   │
   ▼
 [END]
```

## 2. Agent Responsibilities

| Agent / Node | Responsibility | Failure Mode Handling |
|---|---|---|
| `GovernanceSafetyNode` | Validates `ETHICS.md` self-consent, scans for secret leaks, and verifies output MP4 streams & duration (60-90s). | Blocks graph execution on secret leaks or unverified output files. |
| `StoryDirectorAgent` | Validates `storyboard.json` against JSON schema, enforces duration (60-90s) & shot reasons. | Emits actionable validation errors. |
| `SupervisorNode` | Routes stages cleanly; pauses for human input when `--hitl` is enabled. | Provides manual override options. |
| `VisualConsistencyAgent` | Calls Cloudflare Workers AI FLUX for character sheet and centered keyframes; computes SHA-256 hashes. | Fallback from FLUX.2 klein to FLUX.1 schnell, then offline reference. |
| `AudioVoiceAgent` | Queries live Gemini TTS models; handles backoff; generates Amharic audio. | Automatic retry with exponential backoff (up to 3x). |
| `QualityCriticAgent` | Verifies generated audio duration (>0s) and file integrity. | Routes back to `AudioVoiceAgent` up to 3 times before fallback. |
| `VideoEditorAgent` | Manages motion shots (Wan 2.2 or Ken Burns), score ducking, loudnorm, AI end card, and exports `final_16x9.mp4` & `final_9x16.mp4`. | Varied-direction Ken Burns zoompan fallback and sidechaincompress fallback. |

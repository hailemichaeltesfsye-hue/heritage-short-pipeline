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
| `VisualConsistencyAgent` | Calls Cloudflare Workers AI FLUX (multipart FLUX.2 klein / JSON FLUX.1 schnell) for character sheet and centered keyframes; computes SHA-256 hashes. | Fallback to Gemini Image (`gemini-3.1-flash-image` / `gemini-2.5-flash-image`); fails loudly if `dry_run=False`. |
| `AudioVoiceAgent` | Calls `gemini-3.8-flash` (`response_modalities=["AUDIO"]`), normalizes raw PCM to 24kHz mono WAV. | Exponential backoff on 503, then real spoken `edge-tts` (`am-ET-AmehaNeural`) logged as `fallback`. |
| `QualityCriticAgent` | Verifies audio duration (`>0.1s`) AND normalized WAV RMS amplitude (`>= 0.001` in live mode). | Invalidates cache and routes back to `AudioVoiceAgent` up to 3x, or halts graph before assembly. |
| `VideoEditorAgent` | Manages motion shots (Wan 2.2 or Ken Burns), score ducking, loudnorm, AI end card, and exports `final_16x9.mp4` & `final_9x16.mp4`. | Varied-direction Ken Burns zoompan fallback and sidechaincompress fallback. |

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
- Background underscore is ducked beneath voice narration using a voice-first FFmpeg filtergraph:
  - Voice chain: conditioned via `acompressor=threshold=0.125:ratio=3:attack=15:release=120`, normalized to `-14 LUFS` via `loudnorm=I=-14:TP=-1.5:LRA=8`, then split into narration mix and sidechain control signals (`asplit=2[voice_mix][voice_sc]`).
  - Score bed: pre-attenuated by `volume=0.20` (-14 dB gain reduction) with gentle 2.0s fade-in.
  - Sidechain compression: `sidechaincompress=threshold=0.01:ratio=12:attack=60:release=1500`, aggressively suppressing the underscore underneath active speech.
  - Master mix: blended via `amix=inputs=2:duration=first:dropout_transition=2` and protected by `alimiter=limit=0.88:attack=5:release=50`.
- Faststart web streaming: MP4 exports include `-movflags +faststart` to relocate MOOV atoms to the file header for instant zero-buffer web and mobile playback.
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

## 7. User Feedback & Iteration Cycles

### User Test 1 (Slack `#all-technical-challenge` Peer Review)
A 1:25 work-in-progress cut of *The Heritage Short* was shared with peer engineers and filmmakers in the `#all-technical-challenge` Slack channel.

#### Peer Reviews Received
- **Arun Sharma**: Commended visual composition: *"great framing"*.
- **Haylemichael Tsega**: Flagged audio balance: *"I love it, but the background voice/music should be suppressed."*
- **Tsion Habtesilassie**: Provided positive review on narrative pacing, emotional arc, and cultural dignity.
- **Eyosiyas Temesgen**: Identified visual discontinuity across childhood scenes: *"It's Great work. But the childhood images are different in different places so that will be incoherent for the visual flow."*

#### Concrete Pipeline Changes Implemented
1. **Voice-First Audio Ducking Filtergraph**:
   - Replaced basic sidechain compression (`threshold=0.02`, `ratio=6`) with an aggressive voice-first topology: score bed pre-attenuated by `volume=0.20` (-14 dB gain drop), sidechain threshold lowered to `0.01`, ratio increased to `12`, and attack tightened to `60ms`.
   - Voice narration track normalized to `-14 LUFS` and split into mix and sidechain trigger paths.
   - Verified resulting audio levels: speech window sits clearly at `-18 dB` while background music in speech sections is suppressed to `-30 dB to -33 dB`, eliminating speech masking completely.
2. **Childhood Visual Anchor Locking (`shot_01`–`shot_04`)**:
   - Updated `character_sheet.progression_stages.boy_primary` in `storyboard.json` to define a strict, uniform visual identity: *"8-year-old Ethiopian boy, warm brown skin, expressive thoughtful dark brown eyes, neat close-cropped black hair, wearing a clean crisp white collared shirt under a cream handwoven cotton gabi shawl with subtle border embroidery"*.
   - Propagated this exact visual anchor across all childhood shots (`shot_01` Delanta path, `shot_02` Mesno Amba classroom, `shot_03` Kombolcha mother hand-holding, `shot_04` Kombolcha hospital recovery).
   - In `shot_03`, fully detailed the mother archetype (*tall 35yo Ethiopian mother, dark navy cardigan over burgundy dress, white headscarf*) and changed seed to `10123` to eliminate visual drift.
3. **Selective Cache-Invalidated Regeneration**:
   - Leveraged SHA-256 prompt hashing: only childhood shots regenerated; shots 05–10 maintained zero-latency cache hits.
   - Re-assembled dual-aspect masters (`final_16x9.mp4`, `final_9x16.mp4`, `final_16x9_am.mp4`, `final_9x16_am.mp4`, `radio_cut.mp4`) with `-movflags +faststart`.
   - Re-exported static showcase bundle to `frontend/public/showcase-data/`.

### Cultural Authenticity & Motivational Classical Score Refinement
Following V2 reviews, two targeted refinements were integrated:
1. **Authentic Ethiopian Orthodox Christian Teacher Representation (`shot_03`)**:
   - Resolved visual ambiguity where the mother appeared with a tight headscarf/hijab wrap.
   - Refined prompt to reflect authentic Ethiopian Orthodox Christian schoolteacher iconography: uncovered natural hair in traditional cornrow braids (`shuruba`), delicate silver Ethiopian Orthodox cross necklace, white handwoven `netela` shawl draped loosely over shoulders (leaving head, hair, and neck completely visible), modest teacher dress, and lesson notebook.
   - Regenerated keyframe and motion shot with seed `10125`, achieving full cultural fidelity.
2. **Motivational Classical Cinematic Instrumental Score**:
   - Upgraded audio synthesis in `pipeline/music.py` from basic fallback sines to a multi-layered, uplifting classical instrumental:
     - Warm, expressive acoustic piano arpeggios in D Major.
     - Sustained warm cello and string pads with natural vibrato and gentle chord swells.
     - Emotional 3-phase arc: reflective childhood in Delanta (0–30s), expanding harmonic richness during Abinet training (30–55s), and a soaring motivational climax for Software Engineering and direct address (55–80s).
     - Applied soft concert hall reverb (`aecho`) and warm acoustic equalization.
   - Strict ducking calibration in `pipeline/assemble.py`:
     - Plays gently at `-10 dB` (`volume=0.316`) during the 3.0s opening title card and 3.0s closing AI slate.
     - Ducks cleanly to `-20 dB` via `sidechaincompress` (`ratio=10`, `threshold=0.015`, `attack=60ms`, `release=1200ms`) whenever narration speaks, ensuring 100% speech intelligibility.

### User Test 2
```markdown
[PENDING - COLLECT 3 PEER REACTIONS ON V2]
- Target: Validate V2 cut with voice-first audio ducking, motivational classical score, and authentic cultural iconography
- Reviewer 1 (Classical Score & Audio Ducking Balance): [Pending Slack Review]
- Reviewer 2 (Childhood & Mother Cultural Consistency): [Pending Slack Review]
- Reviewer 3 (Overall Narrative Impact & Climax): [Pending Slack Review]
```


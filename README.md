# AI Filmmaking Pipeline: The Heritage Short

Production-grade, multi-agent AI filmmaking orchestrator producing the autobiographical Amharic short film:
**"Hulum Neger Lebego New (ሁሉም ነገር ለበጎ ነው)"**

---

## Highlights & Features
- **LangGraph Multi-Agent Orchestration**: Specialized state graph with Director, Visual Consistency, Audio Voice, Quality Critic (Self-Healing Loop), Video Editor, Governance/Safety, and Supervisor nodes.
- **Strict Storyboard Schema Contract**: Validates 10-shot Amharic narrative structure (~77s total) against `schema/storyboard.schema.json`.
- **Cloudflare Workers AI FLUX Keyframes**: Real REST integration with `@cf/black-forest-labs/flux-2-klein-4b` and automatic fallback to `@cf/black-forest-labs/flux-1-schnell`. Centered subject framing guarantees clean cropping for both `16:9` and `9:16`.
- **Kaggle Wan 2.2 & HunyuanVideo Runner**: Ready-to-upload GPU scripts (`kaggle/wan22_i2v_runner.py` / `.ipynb`) executing `Wan 2.2 TI2V-5B` image-to-video at 480p 24fps using concise `motion_prompt`s.
- **Deterministic Ken Burns Fallback**: Varied-direction FFmpeg `zoompan` motion shots (pan left/right, push-in, tilt, zoom-out) automatically generated when raw clips are absent.
- **Kaggle ACE-Step 1.5 Underscore**: Generates 3 candidate Ethiopian highland acoustic scores (`outputs/music/`), normalized with gentle in/out fades.
- **Mastered Dual-Aspect Exports**:
  - Dynamic visual duration adjustment (+0.5s breathing room) preventing narration cutoff.
  - Subtitle constraints strictly enforced: `max 2 lines`, `max 40 chars/line`.
  - FFmpeg `sidechaincompress` audio ducking with two-pass `-14 LUFS` and `-1.0 dB TP` loudnorm.
  - 3-second visible AI end card: *"Made with AI — Story, pipeline & Amharic narration by Hailemichael Tesfaye"*.
  - Dual deliverables: `outputs/final_16x9.mp4` and `outputs/final_9x16.mp4`.
- **Single-Shot SHA-256 Cache**: Per-shot manifest (`outputs/.cache_manifest.json`) across narration, keyframes, and video.
- **Custom MCP Server**: Real tools (`validate_storyboard`, `regenerate_shot`, `get_pipeline_metrics`) using `mcp.server.mcpserver`.
- **Strict Ethical AI Governance**: Verifies `ETHICS.md` self-consent records and protects family privacy.

---

## Phase 4 — Showcase UI & FastAPI Control Tower

### FastAPI Backend Bridge
Live REST API exposing storyboard, pipeline control, metrics, and media:
```bash
# Start development API server (port 8000)
uv run uvicorn api.server:app --reload --port 8000
```
Endpoints:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | FFmpeg path, storyboard exists, timestamp |
| `GET` | `/api/storyboard` | Full validated storyboard JSON |
| `PUT` | `/api/storyboard/shot/{shot_id}` | Safely update one shot's narration/prompt/seed |
| `POST` | `/api/pipeline/run` | Trigger stage (`all`, `keyframes`, `narration`, `music`, `assemble`, `radio-cut`) |
| `POST` | `/api/pipeline/approve` | Advance HITL checkpoint |
| `GET` | `/api/metrics` | Live parse of `runs.jsonl` — latency, cost, cache hit rate, model breakdown |
| `GET` | `/api/docs` | All 6 engineering journals (DESIGN, ARCHITECTURE, EXPERIMENTS, FAILURES, COSTS, ETHICS) |
| `GET` | `/media/{path}` | Static media — streams files from `outputs/` |

Swagger UI auto-generated at `http://localhost:8000/docs`.

### React + TypeScript + Vite Frontend
Film-studio dark/warm-amber editorial interface with 4 focused views:
1. **Cinema Screening Room** — Switch between `16:9`, `9:16 (mobile)`, and `Radio Cut` previews with Amharic narration + English subtitles
2. **Storyboard Contract & Single-Shot Lab** — Browse all 10 shots; edit & regenerate one shot via FastAPI
3. **Pipeline Observability** — Live `runs.jsonl` breakdown: latency, estimated cost (USD), cache hits, model calls, HITL controls
4. **Engineering Journals** — Rendered `DESIGN.md`, `ARCHITECTURE.md`, `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, `ETHICS.md`

```bash
# Install frontend dependencies
cd frontend && npm install

# Start dev server (port 5173, proxies /api to FastAPI)
npm run dev

# Production build
npm run build

# Type-check only
npx tsc --noEmit
```

### Export Static Showcase (Hugging Face Spaces)
Bundle storyboard, metrics, docs, and media into `frontend/public/showcase-data/`
for a zero-cost static deployment that works without a running backend:
```bash
uv run python pipeline/export_showcase.py
cd frontend && npm run build
```
See `deploy/huggingface/README.md` for Hugging Face Spaces deployment instructions.

### Makefile Shortcuts
```bash
make serve-api        # Start FastAPI backend on port 8000
make serve-frontend   # Start Vite dev server on port 5173
make export-showcase  # Bundle data for static deployment
make build-frontend   # Production frontend build
make deploy-static    # export-showcase + build-frontend
```

---

## Quickstart

### Prerequisites
- Python 3.11+
- `uv` package manager (`pip` is strictly not used)
- `ffmpeg` (Gyan.FFmpeg full build installed and verified)
- Node.js 18+ and npm (for the Phase 4 frontend)

### Installation
```bash
# Clone and navigate to workspace
cd heritage-short-pipeline

# Sync virtual environment using uv
uv sync
```

### Configuration
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```
Key variables:
- `GEMINI_API_KEY`: Google Gemini API key for Amharic TTS narration.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account identifier for Workers AI FLUX keyframe generation.
- `CLOUDFLARE_API_TOKEN`: Cloudflare API token with Workers AI read/write permissions.
- `KAGGLE_NOTEBOOK_URL`: URL to your Kaggle GPU instance running Wan 2.2 and ACE-Step 1.5.

---

## One-Command Film Generation
Run the entire end-to-end pipeline with one command:
```bash
uv run python -m pipeline.run --stage all
```
Or via Makefile:
```bash
make film
```

### Granular CLI Stages
```bash
# Dry run verification
uv run python -m pipeline.run --dry-run

# Keyframe generation only
uv run python -m pipeline.run --stage keyframes

# Narration generation only
uv run python -m pipeline.run --stage narration

# Audio & score mastering only
uv run python -m pipeline.run --stage music

# Assembly and final rendering
uv run python -m pipeline.run --stage assemble

# Single shot targeted regeneration
uv run python -m pipeline.run --shot shot_04 --force

# Storyboard validation
uv run python -m pipeline.run validate

# Telemetry metrics summary
uv run python -m pipeline.run metrics
```

---

## Kaggle GPU Runners
For cloud GPU acceleration:
1. **Wan 2.2 Video**: Upload `kaggle/wan22_i2v_runner.ipynb` to Kaggle, run with GPU (T4/A100), and download `outputs/clips_raw/`.
2. **ACE-Step 1.5 Score**: Upload `kaggle/acestep_score_runner.ipynb` to Kaggle, run with GPU, and download `outputs/music/`.

---

## Test Suite
Run the test suite verifying all stages:
```bash
uv run pytest -v
```

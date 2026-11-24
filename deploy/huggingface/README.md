---
title: The Heritage Short AI Filmmaking Showcase
emoji: 🎬
colorFrom: amber
colorTo: yellow
sdk: static
pinned: false
---

# The Heritage Short — AI Filmmaking Pipeline Showcase
### "Hulum L'Bego New (Everything for Good)"

Autobiographical Amharic short film authored by Hailemichael Tesfaye, produced via a production-grade multi-agent AI filmmaking orchestrator.

## Live Showcase Features
1. **Cinema Screening Room**: Dual-aspect video player (`16:9 Cinema Master` and `9:16 Vertical Safe`) + Radio Cut preview with Amharic speech and English subtitles.
2. **Storyboard Contract & Shot Lab**: Full 10-shot inspection with prompt definitions, seeds, and keyframe stills.
3. **Pipeline Observability**: Real telemetry records parsed from `runs.jsonl`, latency metrics, model distributions, and estimated USD compute expenses.
4. **Engineering Journals**: Direct access to `DESIGN.md`, `ARCHITECTURE.md`, `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, and `ETHICS.md`.

## Deployment Instructions
To deploy updates to this Hugging Face Space:
```bash
# 1. Export real showcase data from your latest local run
uv run python pipeline/export_showcase.py

# 2. Build the production React + TypeScript bundle
cd frontend
npm install
npm run build

# 3. Copy the compiled assets from frontend/dist/* into your Space repo and git push!
cp -r dist/* /path/to/hf-space/
cd /path/to/hf-space
git add .
git commit -m "Deploy updated Heritage Short showcase"
git push
```

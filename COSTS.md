# Cost Analysis & Estimation Framework

## 1. Cost Parameters
- **Gemini 2.5 Flash Input Tokens**: ~$0.000075 per 1k tokens
- **Gemini 2.5 Flash Output Tokens**: ~$0.0003 per 1k tokens
- **Gemini 3.8 Flash Audio Output**: ~$0.00015 per generated narration segment
- **Microsoft Edge-TTS Neural Voices (English Primary & Amharic Fallback)**: $0.00 (free neural synthesis)
- **Cloudflare Workers AI FLUX Image**: ~$0.003 per 1024x1024 image
- **Kaggle T4 / A100 GPU Compute**: Free tier allowance / ~$0.0004 per GPU second
- **Local FFmpeg Processing**: $0.00 (local CPU compute)

## 2. Estimated Full End-to-End Production Run (10 Shots, ~79–84 Seconds with Intro & End Card)

| Stage | Provider / Model | Units | Cost per Unit | Total Estimated Cost |
|---|---|---|---|---|
| Director Validation | Local Rules / Schema | 10 shots | $0.00 | $0.00 |
| Character Sheet Reference | Cloudflare Workers AI FLUX | 1 image | $0.003 | $0.003 USD |
| Shot Keyframes (10 shots) | Cloudflare Workers AI FLUX | 10 images | $0.003 | $0.030 USD |
| English Primary Narration | Edge-TTS (`en-US-AndrewMultilingualNeural`) | 10 shots | $0.00 | $0.0000 USD |
| Amharic Optional Narration | Gemini 3.8 Flash AUDIO / Edge-TTS Fallback | 10 shots | $0.00015 / $0.00 | $0.0000–$0.0015 USD |
| Motion Video (Wan 2.2 Draft) | Kaggle GPU (T4) | ~1.5 GPU min | $0.00 / free quota | $0.0000 USD |
| Score Underscore (ACE-Step 1.5) | Kaggle GPU (T4) | ~1.0 GPU min | $0.00 / free quota | $0.0000 USD |
| Opening Card, Burned Subs & Dual Assembly | Local FFmpeg + PIL | 2× EN + 2× AM 1080p24 | $0.00 | $0.00 |
| **Total Cold Run Production Cost** | | | | **~$0.033–$0.035 USD** |
| **Warm Run (1 Shot Edited)** | | 1 shot | | **~$0.004 USD** |

All costs and latencies are recorded in real-time in `runs.jsonl`.

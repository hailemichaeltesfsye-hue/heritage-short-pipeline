# Cost Analysis & Estimation Framework

## 1. Cost Parameters
- **Gemini 2.5 Flash Input Tokens**: ~$0.000075 per 1k tokens
- **Gemini 2.5 Flash Output Tokens**: ~$0.0003 per 1k tokens
- **Audio Output Modality (Gemini TTS)**: ~$0.00015 per second of generated audio
- **Cloudflare Workers AI FLUX Image**: ~$0.003 per 1024x1024 image
- **Kaggle T4 / A100 GPU Compute**: Free tier allowance / ~$0.0004 per GPU second
- **Local FFmpeg Processing**: $0.00 (local CPU compute)

## 2. Estimated Full End-to-End Production Run (10 Shots, ~77 Seconds)

| Stage | Provider / Model | Units | Cost per Unit | Total Estimated Cost |
|---|---|---|---|---|
| Director Validation | Local Rules / Schema | 10 shots | $0.00 | $0.00 |
| Character Sheet Reference | Cloudflare Workers AI FLUX | 1 image | $0.003 | $0.003 USD |
| Shot Keyframes (10 shots) | Cloudflare Workers AI FLUX | 10 images | $0.003 | $0.030 USD |
| Voice Narration (Full Run) | Gemini API TTS | 74 seconds | $0.00015 / sec | ~$0.0111 USD |
| Motion Video (Wan 2.2 Draft) | Kaggle GPU (T4) | ~1.5 GPU min | $0.00 / free quota | $0.0000 USD |
| Score Underscore (ACE-Step 1.5) | Kaggle GPU (T4) | ~1.0 GPU min | $0.00 / free quota | $0.0000 USD |
| Dual Assembly & Audio Mastering | Local FFmpeg | 2x 1080p24 encode | $0.00 | $0.00 |
| **Total Cold Run Production Cost** | | | | **~$0.044 USD** |
| **Warm Run (1 Shot Edited)** | | 1 shot | | **~$0.004 USD** |

All costs and latencies are recorded in real-time in `runs.jsonl`.

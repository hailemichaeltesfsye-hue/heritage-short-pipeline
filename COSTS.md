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

## 3. Projected Scale Analysis (10× and 100× Production)

The architecture leverages serverless edge inference (Cloudflare Workers AI FLUX), free neural TTS (Edge-TTS), local containerized FFmpeg assembly, and Kaggle/colab GPU quotas, yielding ultra-low unit economics compared to traditional production studios.

| Scale Dimension | 1 Film (Baseline: 80s) | 10 Films (10× Scale: 800s) | 100 Films (100× Scale: ~2.2 Hours) |
|---|---|---|---|
| **Keyframes (Cloudflare FLUX)** | 11 images: ~$0.033 | 110 images: ~$0.33 | 1,100 images: ~$3.30 |
| **Voiceover (Edge-TTS / Gemini)** | 20 tracks: ~$0.001 | 200 tracks: ~$0.01 | 2,000 tracks: ~$0.10 |
| **Motion Video (Wan 2.2 / Ken Burns)** | Free tier / local: $0.00 | Free quota: $0.00 | ~$1.20 (if paid T4 spot GPU) |
| **Soundtrack / Score Underscore** | Free tier / local: $0.00 | Free quota: $0.00 | ~$0.60 (if paid GPU) |
| **Assembly & Subtitles (FFmpeg)** | Local CPU: $0.00 | Local CPU: $0.00 | Local CPU / CI runner: $0.00 |
| **Total Production Cost** | **~$0.035 USD** | **~$0.34 USD** | **~$5.20 USD** (or ~$3.40 fully serverless) |
| **Per-Minute Unit Cost** | ~$0.026 / min | ~$0.026 / min | ~$0.039 / min |

### Key Economic Takeaways:
1. **Linear Marginal Cost**: Character sheet generation is amortized across shots. Single-shot edits cost only ~$0.004 due to SHA-256 caching.
2. **100× Film Run for <$6.00**: An entire 100-film documentary series costs less than a single stock footage clip purchase on traditional platforms ($60–$150).
3. **Bandwidth & Hosting**: Static Vite assets hosted on Vercel's free tier with zero ongoing server costs.


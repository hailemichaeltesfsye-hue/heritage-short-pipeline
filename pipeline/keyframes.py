"""Visual prompt compiler, Cloudflare Workers AI FLUX + Gemini Image keyframe generation, and caching."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import httpx
from PIL import Image, ImageDraw

from pipeline.cache import compute_shot_hash, is_shot_cached, update_shot_cache
from pipeline.logger import log_run

load_dotenv()

OUTPUTS_KEYFRAMES_DIR = Path("outputs/keyframes")
OUTPUTS_REFERENCE_DIR = Path("outputs/reference")

PRIMARY_FLUX_MODEL = os.getenv("CLOUDFLARE_FLUX_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")
FALLBACK_FLUX_MODEL = "@cf/black-forest-labs/flux-1-schnell"
GEMINI_IMAGE_MODELS = (
    "models/gemini-3.1-flash-image",
    "models/gemini-2.5-flash-image",
)


def compile_shot_prompts(storyboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compile character-sheet progression and style block into unified shot visual prompts."""
    style_block = storyboard_data.get("style_block", {})
    character_sheet = storyboard_data.get("character_sheet", {})
    stages = character_sheet.get("progression_stages", {})
    shots = storyboard_data.get("shots", [])

    compiled_shots: List[Dict[str, Any]] = []

    for shot in shots:
        shot_copy = dict(shot)
        shot_id = shot.get("shot_id", "")

        if shot_id in ("shot_01", "shot_02", "shot_03", "shot_04"):
            stage_desc = stages.get("boy_primary", "")
        elif shot_id in ("shot_05", "shot_06"):
            stage_desc = stages.get("teen_student_deacon", "")
        else:
            stage_desc = stages.get("young_adult_engineer", "")

        base_prompt = shot.get("visual_prompt", "")
        framing_guidance = (
            "Composed with subject centered in frame for clean 16:9 and 9:16 dual crop compatibility. "
            "Safe-area margins, cinematic 35mm photography, warm golden-hour highland lighting, "
            "photorealistic skin textures, strictly no text, no captions, no watermarks."
        )
        style_prompt = (
            f"Style: {style_block.get('visual_tone', '')}. "
            f"Lighting: {style_block.get('lighting', '')}. "
            f"Palette: {style_block.get('color_palette', '')}. "
            f"Cinematography: {style_block.get('cinematography', '')}."
        )

        full_prompt = f"{base_prompt} Character anchor: {stage_desc}. {framing_guidance} {style_prompt}"
        shot_copy["compiled_visual_prompt"] = full_prompt
        shot_copy["content_hash"] = compute_shot_hash(shot, style_block)
        compiled_shots.append(shot_copy)

    return compiled_shots


def create_deterministic_reference_image(
    output_path: Path,
    prompt: str,
    seed: int = 42,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """Generate a deterministic reference keyframe strictly for dry-run / unit testing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), color=(38, 24, 18))
    draw = ImageDraw.Draw(img)

    r_top, g_top, b_top = 210, 140, 70
    r_bot, g_bot, b_bot = 45, 25, 20
    for y in range(height):
        factor = y / float(height)
        r = int(r_top + (r_bot - r_top) * factor)
        g = int(g_top + (g_bot - g_top) * factor)
        b = int(b_top + (b_bot - b_top) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    cx, cy = width // 2, height // 2
    horizon_y = int(height * 0.6)
    draw.polygon(
        [
            (0, height),
            (0, horizon_y + 20),
            (width * 0.3, horizon_y - 40),
            (width * 0.7, horizon_y - 10),
            (width, horizon_y + 30),
            (width, height),
        ],
        fill=(58, 30, 22),
    )

    sun_r = 120
    draw.ellipse([cx - sun_r, cy - sun_r - 40, cx + sun_r, cy + sun_r - 40], fill=(255, 205, 120))
    img.save(str(output_path), "PNG")
    return output_path


def _save_validated_png(raw_bytes: bytes, output_path: Path) -> None:
    """Decode raw JPEG/PNG/WebP bytes with Pillow and write a verified RGB PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(raw_bytes)) as img:
        rgb = img.convert("RGB")
        rgb.save(str(output_path), "PNG")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Saved PNG at {output_path} is empty")


def _try_cloudflare_flux(
    prompt: str,
    output_path: Path,
    seed: Optional[int],
    account_id: str,
    api_token: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Call Cloudflare Workers AI FLUX models (FLUX.2 klein multipart / FLUX.1 schnell JSON)."""
    models_to_try: List[str] = []
    for m in (PRIMARY_FLUX_MODEL, FALLBACK_FLUX_MODEL):
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = "Cloudflare request did not execute"
    for model_name in models_to_try:
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}"
        for attempt in range(1, 3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    if "flux-2" in model_name:
                        # Workers AI FLUX.2 klein expects multipart/form-data (fixed 4 inference steps)
                        files = {
                            "prompt": (None, prompt[:2048]),
                            "width": (None, "1024"),
                            "height": (None, "1024"),
                            "seed": (None, str(seed or 42)),
                        }
                        res = client.post(
                            api_url,
                            headers={"Authorization": f"Bearer {api_token}"},
                            files=files,
                        )
                    else:
                        # FLUX.1 schnell expects JSON payload with prompt, steps, seed
                        payload = {
                            "prompt": prompt[:2048],
                            "steps": 4,
                            "seed": seed or 42,
                        }
                        res = client.post(
                            api_url,
                            headers={
                                "Authorization": f"Bearer {api_token}",
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        )

                if res.status_code == 200:
                    content_type = res.headers.get("content-type", "").lower()
                    raw_img: Optional[bytes] = None
                    if "image" in content_type or "octet-stream" in content_type:
                        raw_img = res.content
                    else:
                        data = res.json()
                        result = data.get("result") or {}
                        image_b64 = result.get("image")
                        if image_b64:
                            raw_img = base64.b64decode(image_b64)

                    if raw_img:
                        _save_validated_png(raw_img, output_path)
                        return model_name, None
                    last_error = f"{model_name} HTTP 200 returned no image data"
                    break

                last_error = f"{model_name} HTTP {res.status_code}: {res.text[:240]}"
                if res.status_code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(1.5)
                    continue
                break
            except Exception as exc:
                last_error = f"{model_name} error: {exc}"
                if attempt < 2:
                    time.sleep(1.0)
                    continue
                break

    return None, last_error


def _try_gemini_image(
    prompt: str,
    output_path: Path,
    api_key: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Real second-provider image generation using Gemini Flash Image models."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    last_error = "Gemini image generation returned no image"

    for model_name in GEMINI_IMAGE_MODELS:
        for modalities in (["IMAGE"], ["TEXT", "IMAGE"]):
            for attempt in range(1, 3):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=modalities,
                        ),
                    )
                    candidates = getattr(response, "candidates", None) or []
                    for candidate in candidates:
                        content = getattr(candidate, "content", None)
                        parts = getattr(content, "parts", None) or []
                        for part in parts:
                            inline = getattr(part, "inline_data", None)
                            if inline and getattr(inline, "data", None):
                                raw = inline.data
                                if isinstance(raw, str):
                                    raw = base64.b64decode(raw)
                                _save_validated_png(bytes(raw), output_path)
                                return model_name, None
                    last_error = f"{model_name} returned no inline image part"
                    break
                except Exception as exc:
                    last_error = f"{model_name} error: {exc}"
                    err_upper = str(exc).upper()
                    if ("503" in err_upper or "UNAVAILABLE" in err_upper or "429" in err_upper) and attempt < 2:
                        time.sleep(2.0)
                        continue
                    break

    return None, last_error


def generate_image_cloudflare(
    prompt: str,
    output_path: Path,
    seed: Optional[int] = None,
    dry_run: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, str, float]:
    """Generate a real keyframe image via Cloudflare FLUX or Gemini Image fallback.

    Never writes synthetic geometric placeholder PNGs when dry_run=False.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    if dry_run:
        create_deterministic_reference_image(output_path, prompt, seed=seed or 42)
        latency_ms = (time.time() - start_time) * 1000
        log_run(
            agent="VisualConsistencyAgent",
            stage="keyframes",
            shot_id=output_path.stem,
            provider="local",
            model="dry-run-flux",
            parameters={"prompt_len": len(prompt), "seed": seed},
            seed=seed,
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
            cache_hit=False,
            status="success",
            trace_id=trace_id,
        )
        return True, output_path, "dry-run-flux", latency_ms

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    cf_error: Optional[str] = None

    # 1. Primary Provider: Cloudflare Workers AI FLUX
    if account_id and api_token and not account_id.startswith("your_") and not api_token.startswith("your_"):
        cf_model, cf_error = _try_cloudflare_flux(prompt, output_path, seed, account_id, api_token)
        if cf_model and output_path.exists():
            latency_ms = (time.time() - start_time) * 1000
            used_fallback = cf_model != PRIMARY_FLUX_MODEL
            log_run(
                agent="VisualConsistencyAgent",
                stage="keyframes",
                shot_id=output_path.stem,
                provider="cloudflare",
                model=cf_model,
                parameters={"prompt_len": len(prompt)},
                seed=seed,
                latency_ms=latency_ms,
                estimated_cost_usd=0.003,
                cache_hit=False,
                status="fallback" if used_fallback else "success",
                error=cf_error,
                trace_id=trace_id,
            )
            return True, output_path, cf_model, latency_ms
    else:
        cf_error = "Cloudflare Workers AI credentials missing or unconfigured"

    # 2. Genuine Second Provider: Gemini Image Generation
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_error: Optional[str] = None
    if gemini_key and not gemini_key.startswith("your_"):
        gm_model, gemini_error = _try_gemini_image(prompt, output_path, gemini_key)
        if gm_model and output_path.exists():
            latency_ms = (time.time() - start_time) * 1000
            log_run(
                agent="VisualConsistencyAgent",
                stage="keyframes",
                shot_id=output_path.stem,
                provider="google-genai",
                model=gm_model,
                parameters={"prompt_len": len(prompt)},
                seed=seed,
                latency_ms=latency_ms,
                estimated_cost_usd=0.039,
                cache_hit=False,
                status="fallback",
                error=cf_error,
                trace_id=trace_id,
            )
            return True, output_path, gm_model, latency_ms
    else:
        gemini_error = "GEMINI_API_KEY missing or unconfigured"

    # Both real image providers failed — refuse to fake imagery when dry_run=False
    output_path.unlink(missing_ok=True)
    latency_ms = (time.time() - start_time) * 1000
    combined_error = f"Cloudflare failed ({cf_error}); Gemini Image failed ({gemini_error})"
    log_run(
        agent="VisualConsistencyAgent",
        stage="keyframes",
        shot_id=output_path.stem,
        provider="cloudflare+google-genai",
        model="keyframe-generator",
        parameters={"prompt_len": len(prompt)},
        seed=seed,
        latency_ms=latency_ms,
        estimated_cost_usd=0.0,
        cache_hit=False,
        status="failed",
        error=combined_error,
        trace_id=trace_id,
    )
    return False, output_path, "failed", latency_ms


def generate_character_sheet(
    storyboard_data: Dict[str, Any],
    output_path: Optional[Path] = None,
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Path:
    """Generate and cache the 3-stage protagonist character sheet."""
    resolved_path = Path(output_path) if output_path is not None else (OUTPUTS_REFERENCE_DIR / "character_sheet.png")
    if not force and resolved_path.exists() and resolved_path.stat().st_size > 0:
        return resolved_path

    character_sheet = storyboard_data.get("character_sheet", {})
    style_block = storyboard_data.get("style_block", {})
    prompt = (
        "3-stage character design sheet of Hailemichael Tesfaye showing consistent Ethiopian facial features: "
        f"Stage 1: {character_sheet.get('progression_stages', {}).get('boy_primary', '')}. "
        f"Stage 2: {character_sheet.get('progression_stages', {}).get('teen_student_deacon', '')}. "
        f"Stage 3: {character_sheet.get('progression_stages', {}).get('young_adult_engineer', '')}. "
        f"Warm Ethiopian highland palette: {style_block.get('color_palette', '')}. "
        "Strictly photorealistic, documentary intimacy, centered composition, no text, no labels."
    )

    success, path, _, _ = generate_image_cloudflare(
        prompt, resolved_path, seed=99999, dry_run=dry_run, trace_id=trace_id
    )
    if not success and not dry_run:
        raise RuntimeError(f"Failed to generate real character sheet at {resolved_path}")
    return path


def generate_shot_keyframe(
    shot: Dict[str, Any],
    style_block: Dict[str, Any],
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, bool]:
    """Generate or retrieve cached keyframe for a single shot."""
    resolved_dir = Path(output_dir) if output_dir is not None else OUTPUTS_KEYFRAMES_DIR
    resolved_dir.mkdir(parents=True, exist_ok=True)
    shot_id = shot["shot_id"]
    output_path = resolved_dir / f"{shot_id}.png"
    shot_hash = compute_shot_hash(shot, style_block)

    if not force and is_shot_cached(shot_id, shot_hash, [output_path]):
        log_run(
            agent="VisualConsistencyAgent",
            stage="keyframes",
            shot_id=shot_id,
            provider="cache",
            model="cache-manifest",
            parameters={"shot_hash": shot_hash},
            seed=shot.get("seed"),
            latency_ms=0.5,
            estimated_cost_usd=0.0,
            cache_hit=True,
            status="success",
            trace_id=trace_id,
        )
        return True, output_path, True

    compiled_prompt = shot.get("compiled_visual_prompt")
    if not compiled_prompt:
        compiled_shots = compile_shot_prompts({"shots": [shot], "style_block": style_block})
        compiled_prompt = compiled_shots[0]["compiled_visual_prompt"]

    success, keyframe_path, _, _ = generate_image_cloudflare(
        prompt=compiled_prompt,
        output_path=output_path,
        seed=shot.get("seed", 42),
        dry_run=dry_run,
        trace_id=trace_id,
    )

    if success and keyframe_path.exists() and keyframe_path.stat().st_size > 0:
        update_shot_cache(
            shot_id=shot_id,
            shot_hash=shot_hash,
            artifacts={"keyframe": str(keyframe_path)},
        )
        return True, keyframe_path, False

    return False, output_path, False


def generate_all_keyframes(
    storyboard_data: Dict[str, Any],
    output_dir: Optional[Path] = None,
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Dict[str, Path]:
    """Generate character reference sheet and all shot keyframes."""
    resolved_dir = Path(output_dir) if output_dir is not None else OUTPUTS_KEYFRAMES_DIR
    generate_character_sheet(storyboard_data, dry_run=dry_run, force=force, trace_id=trace_id)
    style_block = storyboard_data.get("style_block", {})
    compiled = compile_shot_prompts(storyboard_data)

    keyframes_map: Dict[str, Path] = {}
    failed_shots: List[str] = []
    for shot in compiled:
        shot_id = shot["shot_id"]
        success, keyframe_path, _ = generate_shot_keyframe(
            shot=shot,
            style_block=style_block,
            output_dir=resolved_dir,
            dry_run=dry_run,
            force=force,
            trace_id=trace_id,
        )
        if success:
            keyframes_map[shot_id] = keyframe_path
        else:
            failed_shots.append(shot_id)

    if failed_shots and not dry_run:
        raise RuntimeError(f"Real keyframe generation failed for shots: {', '.join(failed_shots)}")

    return keyframes_map

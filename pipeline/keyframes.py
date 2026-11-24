"""Visual prompt compiler, Cloudflare Workers AI FLUX keyframe generation, and consistency hashing."""

from __future__ import annotations

import io
import json
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


def create_deterministic_reference_image(output_path: Path, prompt: str, seed: int = 42, width: int = 1280, height: int = 720) -> Path:
    """Generate a clean deterministic reference keyframe with Ethiopian golden-hour palette.

    Used when offline/dry-run or when external Cloudflare credentials are not supplied.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), color=(38, 24, 18))
    draw = ImageDraw.Draw(img)

    # Render soft golden hour landscape gradient
    r_top, g_top, b_top = 210, 140, 70
    r_bot, g_bot, b_bot = 45, 25, 20
    for y in range(height):
        factor = y / float(height)
        r = int(r_top + (r_bot - r_top) * factor)
        g = int(g_top + (g_bot - g_top) * factor)
        b = int(b_top + (b_bot - b_top) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Center focal point indicator for 16:9 and 9:16 safe area
    cx, cy = width // 2, height // 2
    # Terracotta highland horizon silhouette
    horizon_y = int(height * 0.6)
    draw.polygon(
        [(0, height), (0, horizon_y + 20), (width * 0.3, horizon_y - 40), (width * 0.7, horizon_y - 10), (width, horizon_y + 30), (width, height)],
        fill=(58, 30, 22),
    )

    # Warm sun glow behind center subject
    sun_r = 120
    draw.ellipse([cx - sun_r, cy - sun_r - 40, cx + sun_r, cy + sun_r - 40], fill=(255, 205, 120))

    img.save(str(output_path), "PNG")
    return output_path


def generate_image_cloudflare(
    prompt: str,
    output_path: Path,
    seed: Optional[int] = None,
    dry_run: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, str, float]:
    """Call Cloudflare Workers AI FLUX model with automatic fallback and telemetry."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()

    # Dry-run or missing credentials: generate deterministic offline reference
    if dry_run or not account_id or not api_token or account_id.startswith("your_"):
        create_deterministic_reference_image(output_path, prompt, seed=seed or 42)
        latency_ms = (time.time() - start_time) * 1000
        model_name = "offline-reference-flux" if not dry_run else "dry-run-flux"
        log_run(
            agent="VisualConsistencyAgent",
            stage="keyframes",
            shot_id=output_path.stem,
            provider="local",
            model=model_name,
            parameters={"prompt_len": len(prompt), "seed": seed},
            seed=seed,
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
            cache_hit=False,
            status="success",
            trace_id=trace_id,
        )
        return True, output_path, model_name, latency_ms

    # Live Cloudflare Workers AI API calls with fallback
    models_to_try = [PRIMARY_FLUX_MODEL, FALLBACK_FLUX_MODEL]
    last_error = None

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "seed": seed or 42,
        "num_steps": 4,
        "guidance": 3.5,
        "width": 1024,
        "height": 1024,
    }

    for model_name in models_to_try:
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}"
        try:
            with httpx.Client(timeout=45.0) as client:
                res = client.post(api_url, headers=headers, json=payload)
                if res.status_code == 200:
                    content_type = res.headers.get("content-type", "")
                    if "image" in content_type:
                        with open(output_path, "wb") as f:
                            f.write(res.content)
                    else:
                        # JSON response with image bytes
                        data = res.json()
                        result = data.get("result", {})
                        image_b64 = result.get("image")
                        if image_b64:
                            import base64
                            with open(output_path, "wb") as f:
                                f.write(base64.b64decode(image_b64))

                    if output_path.exists() and output_path.stat().st_size > 0:
                        latency_ms = (time.time() - start_time) * 1000
                        log_run(
                            agent="VisualConsistencyAgent",
                            stage="keyframes",
                            shot_id=output_path.stem,
                            provider="cloudflare",
                            model=model_name,
                            parameters={"prompt_len": len(prompt)},
                            seed=seed,
                            latency_ms=latency_ms,
                            estimated_cost_usd=0.003,
                            cache_hit=False,
                            status="success",
                            trace_id=trace_id,
                        )
                        return True, output_path, model_name, latency_ms
                else:
                    last_error = f"{model_name} HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            last_error = f"{model_name} error: {e}"

    # Fallback to local reference generator if remote failed
    create_deterministic_reference_image(output_path, prompt, seed=seed or 42)
    latency_ms = (time.time() - start_time) * 1000
    log_run(
        agent="VisualConsistencyAgent",
        stage="keyframes",
        shot_id=output_path.stem,
        provider="cloudflare_fallback",
        model="offline-reference-flux",
        parameters={"prompt_len": len(prompt)},
        seed=seed,
        latency_ms=latency_ms,
        estimated_cost_usd=0.0,
        cache_hit=False,
        status="fallback",
        error=last_error,
        trace_id=trace_id,
    )
    return True, output_path, "offline-reference-flux", latency_ms


def generate_character_sheet(
    storyboard_data: Dict[str, Any],
    output_path: Path = OUTPUTS_REFERENCE_DIR / "character_sheet.png",
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Path:
    """Generate and cache the 3-stage protagonist character sheet."""
    if not force and output_path.exists() and output_path.stat().st_size > 0:
        return output_path

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

    generate_image_cloudflare(prompt, output_path, seed=99999, dry_run=dry_run, trace_id=trace_id)
    return output_path


def generate_shot_keyframe(
    shot: Dict[str, Any],
    style_block: Dict[str, Any],
    output_dir: Path = OUTPUTS_KEYFRAMES_DIR,
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Tuple[bool, Path, bool]:
    """Generate or retrieve cached keyframe for a single shot.

    Returns:
        (success, keyframe_path, was_cache_hit)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    shot_id = shot["shot_id"]
    output_path = output_dir / f"{shot_id}.png"
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

    # Cache miss or forced
    compiled_prompt = shot.get("compiled_visual_prompt")
    if not compiled_prompt:
        compiled_shots = compile_shot_prompts({"shots": [shot], "style_block": style_block})
        compiled_prompt = compiled_shots[0]["compiled_visual_prompt"]

    success, keyframe_path, model_used, latency = generate_image_cloudflare(
        prompt=compiled_prompt,
        output_path=output_path,
        seed=shot.get("seed", 42),
        dry_run=dry_run,
        trace_id=trace_id,
    )

    if success and keyframe_path.exists():
        update_shot_cache(
            shot_id=shot_id,
            shot_hash=shot_hash,
            artifacts={"keyframe": str(keyframe_path)},
        )
        return True, keyframe_path, False

    return False, output_path, False


def generate_all_keyframes(
    storyboard_data: Dict[str, Any],
    output_dir: Path = OUTPUTS_KEYFRAMES_DIR,
    dry_run: bool = False,
    force: bool = False,
    trace_id: Optional[str] = None,
) -> Dict[str, Path]:
    """Generate character reference sheet and all 10 shot keyframes."""
    generate_character_sheet(storyboard_data, dry_run=dry_run, force=force, trace_id=trace_id)
    style_block = storyboard_data.get("style_block", {})
    compiled = compile_shot_prompts(storyboard_data)

    keyframes_map: Dict[str, Path] = {}
    for shot in compiled:
        shot_id = shot["shot_id"]
        success, keyframe_path, _ = generate_shot_keyframe(
            shot=shot,
            style_block=style_block,
            output_dir=output_dir,
            dry_run=dry_run,
            force=force,
            trace_id=trace_id,
        )
        if success:
            keyframes_map[shot_id] = keyframe_path

    return keyframes_map

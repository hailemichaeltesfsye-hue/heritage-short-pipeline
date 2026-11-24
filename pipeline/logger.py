"""Structured JSONL run logging and telemetry for heritage-short-pipeline.

Appends 1 structured JSON line per model or pipeline operation to runs.jsonl.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

RUNS_LOG_PATH = Path("runs.jsonl")


def log_run(
    agent: str,
    stage: str,
    shot_id: Optional[str] = None,
    provider: str = "local",
    model: str = "none",
    parameters: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
    latency_ms: float = 0.0,
    estimated_cost_usd: float = 0.0,
    cache_hit: bool = False,
    status: str = "success",
    error: Optional[str] = None,
    trace_id: Optional[str] = None,
    log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Append a structured log record to runs.jsonl."""
    resolved_path = Path(log_path) if log_path is not None else RUNS_LOG_PATH
    record = {
        "trace_id": trace_id or str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "stage": stage,
        "shot_id": shot_id,
        "provider": provider,
        "model": model,
        "parameters": parameters or {},
        "seed": seed,
        "latency_ms": round(latency_ms, 2),
        "estimated_cost_usd": round(estimated_cost_usd, 6),
        "cache_hit": cache_hit,
        "status": status,
        "error": error,
    }
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def get_pipeline_metrics(log_path: Optional[Path] = None) -> Dict[str, Any]:
    """Aggregate metrics from runs.jsonl."""
    resolved_path = Path(log_path) if log_path is not None else RUNS_LOG_PATH
    if not resolved_path.exists():
        return {
            "total_runs": 0,
            "total_latency_ms": 0.0,
            "total_cost_usd": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_ratio": 0.0,
            "failures": 0,
        }

    total_runs = 0
    total_latency_ms = 0.0
    total_cost_usd = 0.0
    cache_hits = 0
    cache_misses = 0
    failures = 0

    with open(resolved_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                total_runs += 1
                total_latency_ms += data.get("latency_ms", 0.0)
                total_cost_usd += data.get("estimated_cost_usd", 0.0)
                if data.get("cache_hit", False):
                    cache_hits += 1
                else:
                    cache_misses += 1
                if data.get("status") != "success":
                    failures += 1
            except Exception:
                continue

    total_attempts = cache_hits + cache_misses
    hit_ratio = round(cache_hits / total_attempts, 4) if total_attempts > 0 else 0.0

    return {
        "total_runs": total_runs,
        "total_latency_ms": round(total_latency_ms, 2),
        "total_cost_usd": round(total_cost_usd, 6),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_ratio": hit_ratio,
        "failures": failures,
    }

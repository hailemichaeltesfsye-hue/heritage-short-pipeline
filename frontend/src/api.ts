import { MetricsData, OutputsManifest, Shot, StoryboardData } from './types';

const API_BASE = 'http://localhost:8000';

let isBackendLive: boolean | null = null;

export async function checkBackendConnection(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(1500),
    });
    isBackendLive = res.ok;
    return res.ok;
  } catch {
    isBackendLive = false;
    return false;
  }
}

export async function fetchStoryboard(): Promise<{ is_valid: boolean; storyboard: StoryboardData }> {
  const live = await checkBackendConnection();
  if (live) {
    const res = await fetch(`${API_BASE}/api/storyboard`);
    if (res.ok) return res.json();
  }
  const res = await fetch('/showcase-data/storyboard.json');
  return res.json();
}

export async function fetchOutputsManifest(): Promise<OutputsManifest> {
  const empty: OutputsManifest = { files: {}, keyframes: [], narration: [] };
  try {
    const live = isBackendLive ?? (await checkBackendConnection());
    if (live) {
      const res = await fetch(`${API_BASE}/api/outputs`);
      if (res.ok) return res.json();
    }
    const res = await fetch('/showcase-data/outputs.json');
    if (res.ok) return res.json();
  } catch {
    return empty;
  }
  return empty;
}

export async function updateShot(shotId: string, updates: Partial<Shot>): Promise<{ success: boolean; shot: Shot }> {
  const live = isBackendLive ?? (await checkBackendConnection());
  if (!live) {
    throw new Error('Static showcase mode: connect local FastAPI backend on port 8000 to edit shots.');
  }
  const res = await fetch(`${API_BASE}/api/storyboard/shot/${shotId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail?.errors?.join(', ') || 'Failed to update shot');
  }
  return res.json();
}

export async function triggerPipelineRun(
  stage: string,
  shotId?: string,
  dryRun = false,
  language: 'en' | 'am' | 'both' = 'en',
): Promise<Record<string, unknown>> {
  const live = isBackendLive ?? (await checkBackendConnection());
  if (!live) {
    throw new Error('Static showcase mode: pipeline execution requires local FastAPI backend.');
  }
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stage, shot_id: shotId, dry_run: dryRun, language }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg =
      typeof err.detail === 'string'
        ? err.detail
        : err.detail?.errors?.join(', ') || `Stage '${stage}' failed`;
    throw new Error(msg);
  }
  return res.json();
}

export async function approveHITL(): Promise<{ status: string; approved_at: string }> {
  const live = isBackendLive ?? (await checkBackendConnection());
  if (!live) {
    throw new Error('Static showcase mode: HITL approval requires local FastAPI backend.');
  }
  const res = await fetch(`${API_BASE}/api/pipeline/approve`, { method: 'POST' });
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsData> {
  const live = await checkBackendConnection();
  if (live) {
    const res = await fetch(`${API_BASE}/api/metrics`);
    if (res.ok) return res.json();
  }
  const res = await fetch('/showcase-data/metrics.json');
  return res.json();
}

export async function fetchDocs(): Promise<Record<string, string>> {
  const live = await checkBackendConnection();
  if (live) {
    const res = await fetch(`${API_BASE}/api/docs`);
    if (res.ok) return res.json();
  }
  const res = await fetch('/showcase-data/docs.json');
  return res.json();
}

export function getMediaUrl(relPath: string): string {
  if (isBackendLive) {
    return `${API_BASE}/media/${relPath}`;
  }
  return `/showcase-data/media/${relPath}`;
}

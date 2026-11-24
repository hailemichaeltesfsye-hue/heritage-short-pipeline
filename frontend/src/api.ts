import { MetricsData, Shot, StoryboardData } from './types';

const API_BASE = 'http://localhost:8000';

let isBackendLive: boolean | null = null;

export async function checkBackendConnection(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { method: 'GET', signal: AbortSignal.timeout(1500) });
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
  // Static showcase fallback
  const res = await fetch('/showcase-data/storyboard.json');
  return res.json();
}

export async function updateShot(shotId: string, updates: Partial<Shot>): Promise<{ success: boolean; shot: Shot }> {
  const live = isBackendLive ?? (await checkBackendConnection());
  if (!live) {
    throw new Error('Static Showcase Mode: Editing and live regeneration requires the local FastAPI server.');
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

export async function triggerPipelineRun(stage: string, shotId?: string): Promise<any> {
  const live = isBackendLive ?? (await checkBackendConnection());
  if (!live) {
    throw new Error('Static Showcase Mode: Pipeline execution requires the local FastAPI backend.');
  }
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stage, shot_id: shotId, dry_run: true }),
  });
  return res.json();
}

export async function approveHITL(): Promise<{ status: string; approved_at: string }> {
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
  // If backend is active, stream directly from FastAPI static mount; otherwise relative static showcase
  if (isBackendLive) {
    return `${API_BASE}/media/${relPath}`;
  }
  return `/showcase-data/media/${relPath}`;
}

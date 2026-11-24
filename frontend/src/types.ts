export interface Shot {
  shot_id: string;
  duration_sec: number;
  shot_type: string;
  visual_prompt: string;
  motion_prompt: string;
  narration_am: string;
  subtitle_en: string;
  reason: string;
  seed: number;
  compiled_visual_prompt?: string;
}

export interface StyleBlock {
  visual_tone: string;
  lighting: string;
  color_palette: string;
  cinematography: string;
}

export interface StoryboardData {
  title: string;
  language: string;
  total_duration_sec: number;
  style_block: StyleBlock;
  character_sheet: {
    protagonist: string;
    progression_stages: Record<string, string>;
  };
  music_cues: Array<{
    cue_id: string;
    start_sec: number;
    end_sec: number;
    mood: string;
    instrumentation: string;
  }>;
  shots: Shot[];
}

export interface MetricsSummary {
  total_runs: number;
  total_latency_ms: number;
  total_cost_usd: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_ratio: number;
  failures: number;
}

export interface RunLogEntry {
  trace_id: string;
  timestamp_utc: string;
  agent: string;
  stage: string;
  shot_id?: string;
  provider: string;
  model: string;
  parameters?: Record<string, any>;
  seed?: number;
  latency_ms: number;
  estimated_cost_usd: number;
  cache_hit: boolean;
  status: string;
  error?: string;
}

export interface MetricsData {
  summary: MetricsSummary;
  estimated_gpu_minutes: number;
  model_breakdown: Record<string, number>;
  stage_breakdown: Record<string, { count: number; total_latency_ms: number; total_cost_usd: number }>;
  recent_runs: RunLogEntry[];
  hitl_state?: {
    paused: boolean;
    last_checkpoint?: string | null;
    approved_at?: string | null;
  };
}

export type ViewMode = 'screening' | 'storyboard' | 'observability' | 'journals';
export type AspectRatioMode = '16x9' | '9x16' | 'radio_cut';

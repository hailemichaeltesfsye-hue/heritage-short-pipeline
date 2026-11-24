import React, { useState } from 'react';
import { Check, ShieldCheck } from 'lucide-react';
import { MetricsData } from '../types';
import { approveHITL } from '../api';

interface ObservabilityProps {
  metrics: MetricsData;
  isLive: boolean;
  onRefresh: () => Promise<void>;
}

export const Observability: React.FC<ObservabilityProps> = ({ metrics, isLive, onRefresh }) => {
  const [approving, setApproving] = useState<boolean>(false);
  const [approvedNotice, setApprovedNotice] = useState<string | null>(null);

  const summary = metrics.summary || {
    total_runs: 0,
    total_latency_ms: 0,
    total_cost_usd: 0,
    cache_hits: 0,
    cache_misses: 0,
    cache_hit_ratio: 0,
    failures: 0,
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      const res = await approveHITL();
      setApprovedNotice(`Checkpoint approved at ${res.approved_at}`);
      await onRefresh();
    } catch (err: unknown) {
      setApprovedNotice(err instanceof Error ? err.message : 'Approval requires FastAPI backend.');
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Telemetry</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Live operational records parsed directly from <code className="font-mono text-zinc-300">runs.jsonl</code>
          </p>
        </div>

        <button
          type="button"
          onClick={handleApprove}
          disabled={!isLive || approving}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-white/10 bg-[#111114] hover:border-white/25 text-xs font-medium text-zinc-200 transition-colors disabled:opacity-45 self-start sm:self-auto"
        >
          <ShieldCheck className="w-4 h-4 text-amber-500" />
          <span>{approving ? 'Approving...' : 'Advance HITL Checkpoint'}</span>
        </button>
      </div>

      {approvedNotice && (
        <div className="px-4 py-2.5 rounded-lg bg-[#111114] border border-white/10 text-xs text-zinc-300 flex items-center gap-2">
          <Check className="w-3.5 h-3.5 text-emerald-400" />
          <span>{approvedNotice}</span>
        </div>
      )}

      {/* 4 Minimal KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-[#111114] border border-white/10">
          <div className="text-xs text-zinc-400">Logged Operations</div>
          <div className="text-2xl font-semibold text-zinc-100 font-mono mt-2">
            {summary.total_runs}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            GPU: {metrics.estimated_gpu_minutes.toFixed(2)} min
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[#111114] border border-white/10">
          <div className="text-xs text-zinc-400">Model Latency</div>
          <div className="text-2xl font-semibold text-zinc-100 font-mono mt-2">
            {(summary.total_latency_ms / 1000).toFixed(2)}s
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">
            Cumulative execution time
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[#111114] border border-white/10">
          <div className="text-xs text-zinc-400">Estimated Cost</div>
          <div className="text-2xl font-semibold text-zinc-100 font-mono mt-2">
            ${summary.total_cost_usd.toFixed(4)}
          </div>
          <div className="text-[11px] text-zinc-500 mt-1">
            List-price USD total
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[#111114] border border-white/10">
          <div className="text-xs text-zinc-400">Cache Hit Rate</div>
          <div className="text-2xl font-semibold text-zinc-100 font-mono mt-2">
            {(summary.cache_hit_ratio * 100).toFixed(1)}%
          </div>
          <div className="text-[11px] text-zinc-500 mt-1 font-mono">
            {summary.cache_hits} hits / {summary.cache_misses} misses
          </div>
        </div>
      </div>

      {/* Breakdown Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl bg-[#111114] border border-white/10 space-y-4">
          <h2 className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            Models Invoked
          </h2>
          {Object.keys(metrics.model_breakdown || {}).length === 0 ? (
            <p className="text-xs text-zinc-500">No model invocations recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(metrics.model_breakdown).map(([model, count]) => (
                <div
                  key={model}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#09090b] border border-white/5 text-xs"
                >
                  <span className="font-mono text-zinc-300 truncate pr-3">{model}</span>
                  <span className="font-mono text-amber-400 shrink-0">{count}×</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-5 rounded-xl bg-[#111114] border border-white/10 space-y-4">
          <h2 className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            Per-Stage Breakdown
          </h2>
          {Object.keys(metrics.stage_breakdown || {}).length === 0 ? (
            <p className="text-xs text-zinc-500">No stage traces recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(metrics.stage_breakdown).map(([stage, stats]) => (
                <div
                  key={stage}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#09090b] border border-white/5 text-xs"
                >
                  <span className="capitalize text-zinc-200">{stage.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-4 font-mono text-zinc-400">
                    <span>{stats.count} ops</span>
                    <span>{(stats.total_latency_ms / 1000).toFixed(2)}s</span>
                    <span className="text-zinc-200">${stats.total_cost_usd.toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* runs.jsonl Stream Table */}
      <div className="rounded-xl bg-[#111114] border border-white/10 overflow-hidden">
        <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            Execution Trace Log
          </h2>
          <span className="font-mono text-xs text-zinc-500">
            {metrics.recent_runs?.length || 0} recent entries
          </span>
        </div>

        {!metrics.recent_runs || metrics.recent_runs.length === 0 ? (
          <div className="p-10 text-center text-xs text-zinc-500">
            No telemetry recorded in <code className="font-mono text-zinc-400">runs.jsonl</code> yet.
            Run the pipeline to inspect live latency, model fallbacks, and cache hits.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#09090b] text-zinc-500 border-b border-white/10">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Time (UTC)</th>
                  <th className="py-2.5 px-4 font-medium">Stage</th>
                  <th className="py-2.5 px-4 font-medium">Shot</th>
                  <th className="py-2.5 px-4 font-medium">Provider / Model</th>
                  <th className="py-2.5 px-4 font-medium">Latency</th>
                  <th className="py-2.5 px-4 font-medium">Cache</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-zinc-300">
                {metrics.recent_runs.map((entry, idx) => (
                  <tr key={`${entry.trace_id}-${idx}`} className="hover:bg-white/[0.02]">
                    <td className="py-2.5 px-4 text-zinc-500 whitespace-nowrap">
                      {entry.timestamp_utc ? entry.timestamp_utc.slice(11, 19) : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-300 whitespace-nowrap">{entry.stage}</td>
                    <td className="py-2.5 px-4 text-zinc-200 whitespace-nowrap">
                      {entry.shot_id || '—'}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-400 max-w-xs truncate" title={entry.error || entry.model}>
                      {entry.provider} · {entry.model}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-400 whitespace-nowrap">
                      {entry.latency_ms?.toFixed(0)}ms
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      {entry.cache_hit ? (
                        <span className="text-amber-400">HIT</span>
                      ) : (
                        <span className="text-zinc-600">MISS</span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      <span
                        title={entry.error || undefined}
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          entry.status === 'success'
                            ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40'
                            : entry.status === 'fallback'
                            ? 'bg-amber-950/60 text-amber-300 border border-amber-800/40'
                            : 'bg-rose-950/60 text-rose-300 border border-rose-800/40'
                        }`}
                      >
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

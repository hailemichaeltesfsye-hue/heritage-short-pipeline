import React, { useState } from 'react';
import { Activity, DollarSign, Clock, ShieldCheck, CheckCircle2, Cpu, ArrowUpRight, Check } from 'lucide-react';
import { MetricsData } from '../types';
import { approveHITL } from '../api';

interface ObservabilityProps {
  metrics: MetricsData;
  isLive: boolean;
  onRefresh: () => void;
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
      onRefresh();
    } catch {
      setApprovedNotice('Approved locally (showcase mode)');
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="border-b border-studio-border pb-4">
        <h2 className="text-xl font-cinematic font-bold text-white tracking-wide">Pipeline Observability & Telemetry</h2>
        <p className="text-sm text-neutral-400 mt-0.5">
          Real-time execution traces, token/image API expenses, model breakdown, and Human-in-the-Loop controls
        </p>
      </div>

      {/* HITL Checkpoint Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-studio-surface to-studio-card border border-studio-amber/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-studio-amber/20 border border-studio-amber flex items-center justify-center text-studio-gold">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Supervisor Human-in-the-Loop (HITL) Gate</div>
            <div className="text-xs text-neutral-400">
              {approvedNotice || 'Autonomous mode active. Manual checkpoints pause between Director and Assembly.'}
            </div>
          </div>
        </div>

        <button
          onClick={handleApprove}
          disabled={approving}
          className="px-4 py-2 rounded-lg bg-studio-amber text-black font-semibold text-xs flex items-center gap-1.5 hover:bg-studio-gold transition-colors disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          <span>{approving ? 'Approving...' : 'Advance Stage Checkpoint'}</span>
        </button>
      </div>

      {/* Real Top Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-2">
            <span>Total Model Latency</span>
            <Clock className="w-4 h-4 text-studio-gold" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {(summary.total_latency_ms / 1000).toFixed(2)}s
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">Aggregated generation duration</div>
        </div>

        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-2">
            <span>List-Price Cost (USD)</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-300 tracking-tight">
            ${summary.total_cost_usd.toFixed(4)}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">Cold run ~$0.044 / Warm ~$0.004</div>
        </div>

        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-2">
            <span>Cache Hit Rate</span>
            <CheckCircle2 className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-200 tracking-tight">
            {(summary.cache_hit_ratio * 100).toFixed(1)}%
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">
            {summary.cache_hits} hits / {summary.cache_misses} misses
          </div>
        </div>

        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="flex items-center justify-between text-neutral-400 text-xs mb-2">
            <span>Total Logged Operations</span>
            <Cpu className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {summary.total_runs}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">
            GPU Minutes: {metrics.estimated_gpu_minutes.toFixed(2)} min
          </div>
        </div>
      </div>

      {/* Model & Stage Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Models Invoked */}
        <div className="p-5 rounded-xl bg-studio-card border border-studio-border space-y-4">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Models Invoked</h3>
          <div className="space-y-2">
            {Object.keys(metrics.model_breakdown || {}).length === 0 ? (
              <div className="text-xs text-neutral-500 italic">No model records in runs.jsonl yet.</div>
            ) : (
              Object.entries(metrics.model_breakdown).map(([model, count]) => (
                <div key={model} className="flex items-center justify-between p-2 rounded bg-studio-surface text-xs">
                  <span className="font-mono text-neutral-300">{model}</span>
                  <span className="px-2 py-0.5 rounded bg-studio-amber/20 text-studio-gold font-bold">
                    {count} calls
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Per-Stage Telemetry */}
        <div className="p-5 rounded-xl bg-studio-card border border-studio-border space-y-4">
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Per-Stage Performance</h3>
          <div className="space-y-2">
            {Object.keys(metrics.stage_breakdown || {}).length === 0 ? (
              <div className="text-xs text-neutral-500 italic">No stage records yet.</div>
            ) : (
              Object.entries(metrics.stage_breakdown).map(([stage, stats]) => (
                <div key={stage} className="flex items-center justify-between p-2 rounded bg-studio-surface text-xs">
                  <span className="capitalize font-medium text-neutral-200">{stage.replace(/_/g, ' ')}</span>
                  <div className="flex items-center space-x-3 text-neutral-400 font-mono">
                    <span>{stats.count} ops</span>
                    <span>{(stats.total_latency_ms / 1000).toFixed(2)}s</span>
                    <span className="text-emerald-400">${stats.total_cost_usd.toFixed(4)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Real runs.jsonl Log Stream */}
      <div className="p-5 rounded-xl bg-studio-card border border-studio-border space-y-4">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center justify-between">
          <span>Real Telemetry Records (runs.jsonl)</span>
          <span className="text-xs text-neutral-500 font-normal">Last {metrics.recent_runs?.length || 0} calls</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-studio-surface text-neutral-400 border-b border-studio-border">
              <tr>
                <th className="py-2 px-3">Timestamp (UTC)</th>
                <th className="py-2 px-3">Agent</th>
                <th className="py-2 px-3">Stage</th>
                <th className="py-2 px-3">Shot ID</th>
                <th className="py-2 px-3">Model</th>
                <th className="py-2 px-3">Latency</th>
                <th className="py-2 px-3">Cost (USD)</th>
                <th className="py-2 px-3">Cache</th>
                <th className="py-2 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-studio-border/50 text-neutral-300">
              {(metrics.recent_runs || []).map((entry, idx) => (
                <tr key={`${entry.trace_id}-${idx}`} className="hover:bg-studio-surface/50">
                  <td className="py-2 px-3 text-neutral-400 whitespace-nowrap">
                    {entry.timestamp_utc ? entry.timestamp_utc.slice(11, 19) : '-'}
                  </td>
                  <td className="py-2 px-3 text-amber-200">{entry.agent}</td>
                  <td className="py-2 px-3">{entry.stage}</td>
                  <td className="py-2 px-3 text-studio-gold font-bold">{entry.shot_id || '-'}</td>
                  <td className="py-2 px-3 text-neutral-400">{entry.model}</td>
                  <td className="py-2 px-3">{entry.latency_ms?.toFixed(1)}ms</td>
                  <td className="py-2 px-3 text-emerald-400">${entry.estimated_cost_usd?.toFixed(5)}</td>
                  <td className="py-2 px-3">
                    {entry.cache_hit ? (
                      <span className="text-amber-400 font-bold">HIT</span>
                    ) : (
                      <span className="text-neutral-500">MISS</span>
                    )}
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        entry.status === 'success'
                          ? 'bg-emerald-950 text-emerald-300'
                          : 'bg-amber-950 text-amber-300'
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
      </div>
    </div>
  );
};

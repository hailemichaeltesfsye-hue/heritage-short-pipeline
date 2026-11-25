import React, { useState } from 'react';
import { AlertCircle, Check, Info, RefreshCw } from 'lucide-react';
import { OutputsManifest, Shot, StoryboardData } from '../types';
import { getMediaUrl, triggerPipelineRun, updateShot } from '../api';

interface StoryboardLabProps {
  storyboard: StoryboardData;
  outputs: OutputsManifest;
  isLive: boolean;
  onRefresh: () => Promise<void>;
}

export const StoryboardLab: React.FC<StoryboardLabProps> = ({
  storyboard,
  outputs,
  isLive,
  onRefresh,
}) => {
  const [selectedShot, setSelectedShot] = useState<Shot>(storyboard.shots[0]);
  const [editForm, setEditForm] = useState<Partial<Shot>>({});
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleSelectShot = (shot: Shot) => {
    setSelectedShot(shot);
    setEditForm({
      narration_en: shot.narration_en ?? shot.subtitle_en,
      narration_am: shot.narration_am,
      subtitle_en: shot.subtitle_en,
      visual_prompt: shot.visual_prompt,
      motion_prompt: shot.motion_prompt,
      seed: shot.seed,
    });
    setFeedback(null);
  };

  const handleSaveAndRegenerate = async () => {
    if (!isLive) {
      setFeedback({
        type: 'error',
        message: 'Static showcase mode: connect local FastAPI backend on port 8000 to regenerate shots.',
      });
      return;
    }

    setIsUpdating(true);
    setFeedback(null);
    try {
      await updateShot(selectedShot.shot_id, editForm);
      await triggerPipelineRun('keyframes', selectedShot.shot_id, false);
      await triggerPipelineRun('narration', selectedShot.shot_id, false, 'both');

      setFeedback({
        type: 'success',
        message: `${selectedShot.shot_id} saved and regenerated cleanly.`,
      });
      await onRefresh();
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to update shot',
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const subtitleDraft = editForm.subtitle_en ?? selectedShot.subtitle_en;

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Storyboard Lab</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Schema-validated 10-shot contract · {storyboard.total_duration_sec}s target runtime · Single-shot SHA-256 cache isolation
          </p>
        </div>
      </div>

      {!isLive && (
        <div className="px-4 py-3 rounded-lg bg-[#111114] border border-white/10 text-xs text-zinc-400 flex items-center gap-2.5">
          <Info className="w-4 h-4 text-zinc-400 shrink-0" />
          <span>
            Static read-only showcase mode. Start local FastAPI (<code className="font-mono text-zinc-300">make serve-api</code>) to edit prompts and regenerate single shots live.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Shot Contract Grid (Left 7 Cols) */}
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {storyboard.shots.map((shot, idx) => {
            const isSelected = shot.shot_id === selectedShot.shot_id;
            const hasKeyframe = outputs.keyframes?.includes(shot.shot_id);

            return (
              <button
                key={shot.shot_id}
                type="button"
                onClick={() => handleSelectShot(shot)}
                className={`text-left p-4 rounded-xl bg-[#111114] border transition-colors ${isSelected
                  ? 'border-amber-500/80 ring-1 ring-amber-500/20'
                  : 'border-white/10 hover:border-white/25'
                  }`}
              >
                <div className="aspect-video rounded-lg overflow-hidden bg-[#09090b] border border-white/5 mb-3 relative flex items-center justify-center">
                  {hasKeyframe ? (
                    <img
                      src={getMediaUrl(`keyframes/${shot.shot_id}.png`)}
                      alt={shot.shot_id}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-center space-y-1">
                      <span className="font-mono text-xs text-zinc-500 block">
                        SHOT {String(idx + 1).padStart(2, '0')}
                      </span>
                      <span className="text-[11px] text-zinc-600 capitalize">
                        {shot.shot_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                  <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/70 font-mono text-[10px] text-zinc-200">
                    {shot.shot_id}
                  </span>
                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 font-mono text-[10px] text-zinc-400">
                    {shot.duration_sec}s
                  </span>
                </div>

                <p className="font-ethiopic text-sm text-zinc-100 line-clamp-1">
                  {shot.narration_am}
                </p>
                <p className="text-xs text-zinc-400 line-clamp-1 mt-1">
                  “{shot.subtitle_en}”
                </p>

                <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                  <span className="capitalize">{shot.shot_type.replace(/_/g, ' ')}</span>
                  <span>seed {shot.seed}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Shot Inspector & Editor (Right 5 Cols) */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-[#111114] border border-white/10 space-y-5 sticky top-24">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <h2 className="text-base font-semibold text-zinc-100">
              {selectedShot.shot_id}
            </h2>
            <span className="font-mono text-xs text-zinc-400">
              {selectedShot.duration_sec}s · {selectedShot.shot_type.replace(/_/g, ' ')}
            </span>
          </div>

          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs flex items-start gap-2 border ${feedback.type === 'success'
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                : 'bg-rose-950/40 text-rose-300 border-rose-800/60'
                }`}
            >
              {feedback.type === 'success' ? (
                <Check className="w-4 h-4 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          <div className="space-y-4 text-xs">
            <div>
              <label className="block text-zinc-400 font-medium mb-1.5">
                English Narration — Primary (Edge-TTS AndrewMultilingual)
              </label>
              <textarea
                rows={3}
                disabled={!isLive}
                value={editForm.narration_en ?? selectedShot.narration_en ?? selectedShot.subtitle_en}
                onChange={(e) => setEditForm({ ...editForm, narration_en: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-[#09090b] border border-white/10 text-zinc-100 leading-relaxed focus:outline-none focus:border-amber-500/60 disabled:opacity-70"
              />
            </div>

            <div>
              <label className="block text-zinc-400 font-medium mb-1.5">
                Amharic Narration — Optional (Gemini 3.8 / Edge-TTS)
              </label>
              <textarea
                rows={2}
                disabled={!isLive}
                value={editForm.narration_am ?? selectedShot.narration_am}
                onChange={(e) => setEditForm({ ...editForm, narration_am: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-[#09090b] border border-white/10 text-zinc-100 font-ethiopic text-sm leading-relaxed focus:outline-none focus:border-amber-500/60 disabled:opacity-70"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-zinc-400 font-medium">English Subtitle</label>
                <span className="font-mono text-[11px] text-zinc-500">
                  {subtitleDraft.length} chars (wrapped ≤ 40/line × 2)
                </span>
              </div>
              <textarea
                rows={2}
                disabled={!isLive}
                value={subtitleDraft}
                onChange={(e) => setEditForm({ ...editForm, subtitle_en: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-[#09090b] border border-white/10 text-zinc-200 focus:outline-none focus:border-amber-500/60 disabled:opacity-70"
              />
            </div>

            <div>
              <label className="block text-zinc-400 font-medium mb-1.5">
                Visual Prompt (Cloudflare FLUX / Gemini Image)
              </label>
              <textarea
                rows={3}
                disabled={!isLive}
                value={editForm.visual_prompt ?? selectedShot.visual_prompt}
                onChange={(e) => setEditForm({ ...editForm, visual_prompt: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-[#09090b] border border-white/10 text-zinc-300 leading-relaxed focus:outline-none focus:border-amber-500/60 disabled:opacity-70"
              />
            </div>

            <div>
              <label className="block text-zinc-400 font-medium mb-1.5">
                Motion Prompt (Wan 2.2 / Ken Burns)
              </label>
              <textarea
                rows={2}
                disabled={!isLive}
                value={editForm.motion_prompt ?? selectedShot.motion_prompt}
                onChange={(e) => setEditForm({ ...editForm, motion_prompt: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-[#09090b] border border-white/10 text-zinc-300 focus:outline-none focus:border-amber-500/60 disabled:opacity-70"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-zinc-500 mb-1">Deterministic Seed</label>
                <input
                  type="number"
                  disabled={!isLive}
                  value={editForm.seed ?? selectedShot.seed}
                  onChange={(e) => setEditForm({ ...editForm, seed: parseInt(e.target.value, 10) || 0 })}
                  className="w-full p-2 rounded-lg bg-[#09090b] border border-white/10 text-zinc-200 font-mono focus:outline-none focus:border-amber-500/60 disabled:opacity-70"
                />
              </div>
              <div>
                <label className="block text-zinc-500 mb-1">Rationale</label>
                <div className="p-2 rounded-lg bg-[#09090b] border border-white/5 text-zinc-400 line-clamp-2">
                  {selectedShot.reason}
                </div>
              </div>
            </div>

            <button
              type="button"
              disabled={!isLive || isUpdating}
              onClick={handleSaveAndRegenerate}
              className="w-full py-2.5 px-4 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-40 disabled:hover:bg-amber-500"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isUpdating ? 'animate-spin' : ''}`} />
              <span>{isUpdating ? 'Regenerating Shot...' : 'Save & Regenerate Shot'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { RefreshCw, Edit3, Check, AlertCircle, Sparkles, Clock, Hash, Camera } from 'lucide-react';
import { Shot, StoryboardData } from '../types';
import { getMediaUrl, triggerPipelineRun, updateShot } from '../api';

interface StoryboardLabProps {
  storyboard: StoryboardData;
  isLive: boolean;
  onRefresh: () => void;
}

export const StoryboardLab: React.FC<StoryboardLabProps> = ({ storyboard, isLive, onRefresh }) => {
  const [selectedShot, setSelectedShot] = useState<Shot>(storyboard.shots[0]);
  const [editForm, setEditForm] = useState<Partial<Shot>>({});
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleSelectShot = (shot: Shot) => {
    setSelectedShot(shot);
    setEditForm({
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
        message: 'Static Showcase Mode: Connect local FastAPI on port 8000 to trigger live regeneration.',
      });
      return;
    }

    setIsUpdating(true);
    setFeedback(null);
    try {
      // 1. Update shot in storyboard.json safely
      await updateShot(selectedShot.shot_id, editForm);

      // 2. Trigger targeted single-shot pipeline execution
      await triggerPipelineRun('keyframes', selectedShot.shot_id);
      await triggerPipelineRun('narration', selectedShot.shot_id);

      setFeedback({
        type: 'success',
        message: `Shot ${selectedShot.shot_id} updated and regenerated successfully!`,
      });
      onRefresh();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to update shot',
      });
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-studio-border pb-4">
        <div>
          <h2 className="text-xl font-cinematic font-bold text-white tracking-wide">Storyboard Contract & Shot Lab</h2>
          <p className="text-sm text-neutral-400 mt-0.5">
            Strict schema contract validation ({storyboard.shots.length} shots, {storyboard.total_duration_sec}s total runtime)
          </p>
        </div>

        {!isLive && (
          <div className="px-3 py-1 rounded bg-amber-950/40 text-amber-300 border border-amber-800/60 text-xs flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <span>Read-Only Showcase Mode: Editing disabled on static deployment</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Shots Gallery Grid (Left 7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {storyboard.shots.map((shot, idx) => {
              const isSelected = shot.shot_id === selectedShot.shot_id;
              const keyframeUrl = getMediaUrl(`keyframes/${shot.shot_id}.png`);

              return (
                <div
                  key={shot.shot_id}
                  onClick={() => handleSelectShot(shot)}
                  className={`p-3 rounded-xl bg-studio-card border cursor-pointer transition-all hover:border-studio-amber ${
                    isSelected
                      ? 'border-studio-amber ring-2 ring-studio-amber/40 shadow-lg bg-studio-surface'
                      : 'border-studio-border'
                  }`}
                >
                  <div className="relative aspect-video rounded-lg overflow-hidden bg-black/60 mb-2.5">
                    <img
                      src={keyframeUrl}
                      alt={shot.shot_id}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Fallback image styling
                        (e.target as HTMLElement).style.opacity = '0.5';
                      }}
                    />
                    <div className="absolute top-2 left-2 bg-black/70 backdrop-blur px-2 py-0.5 rounded text-[10px] font-bold text-studio-gold">
                      #{idx + 1} • {shot.shot_id}
                    </div>
                    <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur px-1.5 py-0.5 rounded text-[10px] text-neutral-300">
                      {shot.duration_sec}s
                    </div>
                  </div>

                  <div className="text-xs text-amber-100 font-medium line-clamp-1 mb-1">
                    {shot.narration_am}
                  </div>
                  <div className="text-[11px] text-neutral-400 italic line-clamp-1">
                    "{shot.subtitle_en}"
                  </div>

                  <div className="mt-2.5 pt-2 border-t border-studio-border/60 flex items-center justify-between text-[10px] text-neutral-400">
                    <span className="capitalize">{shot.shot_type.replace(/_/g, ' ')}</span>
                    <span>Seed: {shot.seed}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Shot Editor Drawer (Right 5 Cols) */}
        <div className="lg:col-span-5 p-5 rounded-2xl bg-studio-card border border-studio-border space-y-5 sticky top-24">
          <div className="flex items-center justify-between pb-3 border-b border-studio-border">
            <div className="flex items-center space-x-2">
              <Camera className="w-5 h-5 text-studio-gold" />
              <h3 className="font-cinematic font-bold text-white text-base">
                Shot Lab: {selectedShot.shot_id}
              </h3>
            </div>
            <span className="text-xs text-neutral-400 font-mono">
              Duration: {selectedShot.duration_sec}s
            </span>
          </div>

          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                feedback.type === 'success'
                  ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
                  : 'bg-red-950/60 text-red-300 border border-red-800'
              }`}
            >
              {feedback.type === 'success' ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              <span>{feedback.message}</span>
            </div>
          )}

          <div className="space-y-4 text-xs">
            {/* Amharic Narration */}
            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Amharic Narration (TTS Input)</label>
              <textarea
                rows={2}
                value={editForm.narration_am ?? selectedShot.narration_am}
                onChange={(e) => setEditForm({ ...editForm, narration_am: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-studio-surface border border-studio-border text-amber-100 focus:outline-none focus:border-studio-amber font-sans"
              />
            </div>

            {/* English Subtitle */}
            <div>
              <label className="block text-neutral-300 font-semibold mb-1">English Subtitle (max 40 chars/line)</label>
              <textarea
                rows={2}
                value={editForm.subtitle_en ?? selectedShot.subtitle_en}
                onChange={(e) => setEditForm({ ...editForm, subtitle_en: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-studio-surface border border-studio-border text-neutral-200 focus:outline-none focus:border-studio-amber"
              />
            </div>

            {/* Visual Prompt */}
            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Visual Prompt (FLUX Keyframe)</label>
              <textarea
                rows={3}
                value={editForm.visual_prompt ?? selectedShot.visual_prompt}
                onChange={(e) => setEditForm({ ...editForm, visual_prompt: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-studio-surface border border-studio-border text-neutral-300 focus:outline-none focus:border-studio-amber"
              />
            </div>

            {/* Motion Prompt */}
            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Motion Prompt (Wan 2.2 / Ken Burns)</label>
              <textarea
                rows={2}
                value={editForm.motion_prompt ?? selectedShot.motion_prompt}
                onChange={(e) => setEditForm({ ...editForm, motion_prompt: e.target.value })}
                className="w-full p-2.5 rounded-lg bg-studio-surface border border-studio-border text-neutral-300 focus:outline-none focus:border-studio-amber"
              />
            </div>

            {/* Seed & Rationale */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-neutral-400 mb-1">Deterministic Seed</label>
                <input
                  type="number"
                  value={editForm.seed ?? selectedShot.seed}
                  onChange={(e) => setEditForm({ ...editForm, seed: parseInt(e.target.value) || 0 })}
                  className="w-full p-2 rounded bg-studio-surface border border-studio-border text-neutral-200"
                />
              </div>
              <div>
                <label className="block text-neutral-400 mb-1">Shot Type</label>
                <div className="p-2 rounded bg-studio-surface border border-studio-border text-neutral-400 capitalize">
                  {selectedShot.shot_type.replace(/_/g, ' ')}
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                disabled={isUpdating}
                onClick={handleSaveAndRegenerate}
                className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-studio-amber to-studio-gold text-black font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-amber-900/30 hover:brightness-110 disabled:opacity-50 transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${isUpdating ? 'animate-spin' : ''}`} />
                <span>{isUpdating ? 'Regenerating Shot...' : 'Save & Regenerate Shot'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

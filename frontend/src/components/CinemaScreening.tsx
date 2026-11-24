import React, { useState } from 'react';
import { Play, Pause, Volume2, Maximize2, Smartphone, Monitor, Radio, Info } from 'lucide-react';
import { AspectRatioMode, StoryboardData } from '../types';
import { getMediaUrl } from '../api';

interface CinemaScreeningProps {
  storyboard: StoryboardData;
}

export const CinemaScreening: React.FC<CinemaScreeningProps> = ({ storyboard }) => {
  const [aspectRatio, setAspectRatio] = useState<AspectRatioMode>('16x9');
  const [currentShotIndex, setCurrentShotIndex] = useState<number>(0);
  const [showRefSheet, setShowRefSheet] = useState<boolean>(false);

  const videoSrc =
    aspectRatio === '16x9'
      ? getMediaUrl('final_16x9.mp4')
      : aspectRatio === '9x16'
      ? getMediaUrl('final_9x16.mp4')
      : getMediaUrl('radio_cut.mp4');

  const currentShot = storyboard.shots[currentShotIndex] || storyboard.shots[0];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Aspect Ratio Switcher Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-studio-border pb-4">
        <div>
          <h2 className="text-xl font-cinematic font-bold text-white tracking-wide">Cinema Screening Room</h2>
          <p className="text-sm text-neutral-400 mt-0.5">
            Autobiographical Amharic short film authored by Hailemichael Tesfaye (~74s master + 3s AI end card)
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-studio-surface p-1 rounded-lg border border-studio-border">
          <button
            onClick={() => setAspectRatio('16x9')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              aspectRatio === '16x9'
                ? 'bg-studio-amber text-white shadow'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Monitor className="w-3.5 h-3.5" />
            <span>16:9 Cinema Master</span>
          </button>
          <button
            onClick={() => setAspectRatio('9x16')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              aspectRatio === '9x16'
                ? 'bg-studio-amber text-white shadow'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>9:16 Vertical Safe</span>
          </button>
          <button
            onClick={() => setAspectRatio('radio_cut')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              aspectRatio === 'radio_cut'
                ? 'bg-studio-amber text-white shadow'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Radio Cut</span>
          </button>
        </div>
      </div>

      {/* Main Screening Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Video Canvas Container */}
        <div className="lg:col-span-8 flex flex-col items-center">
          {aspectRatio === '9x16' ? (
            /* Vertical Mobile Frame */
            <div className="relative w-[340px] sm:w-[380px] h-[675px] bg-black rounded-[40px] p-3 shadow-2xl border-4 border-neutral-800 ring-1 ring-neutral-700/50 flex flex-col justify-center overflow-hidden">
              <div className="absolute top-4 left-1/2 -translate-x-1/2 w-28 h-4 bg-neutral-900 rounded-full z-20" />
              <video
                key={videoSrc}
                controls
                playsInline
                className="w-full h-full object-cover rounded-[32px] bg-black"
                src={videoSrc}
              >
                <track label="English" kind="subtitles" srcLang="en" src={getMediaUrl('subtitles.srt')} default />
              </video>
            </div>
          ) : (
            /* 16:9 Horizontal Cinematic Canvas */
            <div className="w-full aspect-video bg-black rounded-xl overflow-hidden shadow-2xl border border-studio-border relative group">
              <video
                key={videoSrc}
                controls
                playsInline
                className="w-full h-full object-contain bg-black"
                src={videoSrc}
              >
                <track label="English" kind="subtitles" srcLang="en" src={getMediaUrl('subtitles.srt')} default />
              </video>
            </div>
          )}

          {/* Audio Mastering & Mix Details */}
          <div className="w-full mt-4 p-4 rounded-lg bg-studio-card border border-studio-border flex flex-wrap items-center justify-between text-xs text-neutral-400 gap-4">
            <div className="flex items-center space-x-2">
              <Volume2 className="w-4 h-4 text-studio-gold" />
              <span>Audio: Dual-pass Loudnorm (-14 LUFS / -1.0 dB TP) + Sidechain Score Ducking</span>
            </div>
            <button
              onClick={() => setShowRefSheet(!showRefSheet)}
              className="text-studio-gold hover:underline flex items-center gap-1 font-medium"
            >
              <Info className="w-3.5 h-3.5" />
              {showRefSheet ? 'Hide Character Reference' : 'View Protagonist Sheet'}
            </button>
          </div>

          {/* Character Reference Drawer */}
          {showRefSheet && (
            <div className="w-full mt-4 p-4 rounded-lg bg-studio-card border border-studio-border">
              <h4 className="text-sm font-cinematic font-bold text-white mb-2">3-Stage Protagonist Progression Anchor</h4>
              <p className="text-xs text-neutral-400 mb-3">
                Generated via Cloudflare Workers AI FLUX to anchor Hailemichael's facial consistency across ages 8, 16, and 21.
              </p>
              <img
                src={getMediaUrl('reference/character_sheet.png')}
                alt="Hailemichael Tesfaye Character Reference Sheet"
                className="w-full rounded border border-studio-border object-cover"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            </div>
          )}
        </div>

        {/* Script & Narrative Synchronizer */}
        <div className="lg:col-span-4 space-y-4">
          <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3 flex items-center justify-between">
              <span>Narration & Subtitles</span>
              <span className="text-xs text-studio-gold font-normal">Shot {currentShotIndex + 1} of 10</span>
            </h3>

            {/* Current Shot Detail Card */}
            <div className="p-3.5 rounded-lg bg-studio-surface border border-studio-amber/30 space-y-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-studio-amber/20 text-studio-gold">
                  {currentShot.shot_id} • {currentShot.duration_sec}s • {currentShot.shot_type.replace(/_/g, ' ')}
                </span>
              </div>
              <div>
                <div className="text-xs text-neutral-400 uppercase font-semibold mb-1">Amharic Narration</div>
                <div className="text-base text-amber-100 font-medium leading-relaxed font-sans">
                  {currentShot.narration_am}
                </div>
              </div>
              <div>
                <div className="text-xs text-neutral-400 uppercase font-semibold mb-1">English Subtitle</div>
                <div className="text-sm text-neutral-200 italic leading-relaxed">
                  "{currentShot.subtitle_en}"
                </div>
              </div>
              <div className="pt-2 border-t border-studio-border text-xs text-neutral-400">
                <span className="text-neutral-500 font-medium">Rationale:</span> {currentShot.reason}
              </div>
            </div>

            {/* Shot Timeline Selector */}
            <div className="mt-4 space-y-2">
              <div className="text-xs font-semibold text-neutral-400 uppercase">Interactive Shot Index</div>
              <div className="grid grid-cols-5 gap-1.5">
                {storyboard.shots.map((shot, idx) => {
                  const isSelected = idx === currentShotIndex;
                  return (
                    <button
                      key={shot.shot_id}
                      onClick={() => setCurrentShotIndex(idx)}
                      className={`py-1.5 px-2 rounded text-xs font-medium text-center transition-all ${
                        isSelected
                          ? 'bg-studio-amber text-white font-bold ring-2 ring-studio-gold'
                          : 'bg-studio-surface text-neutral-400 hover:text-white hover:bg-neutral-800'
                      }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Aesthetic Palette Block */}
          <div className="p-4 rounded-xl bg-studio-card border border-studio-border text-xs space-y-2 text-neutral-300">
            <h4 className="font-semibold text-white uppercase tracking-wider">Highland Cinematic Realism</h4>
            <p><span className="text-neutral-400">Visual Tone:</span> {storyboard.style_block.visual_tone}</p>
            <p><span className="text-neutral-400">Lighting:</span> {storyboard.style_block.lighting}</p>
            <p><span className="text-neutral-400">Palette:</span> {storyboard.style_block.color_palette}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

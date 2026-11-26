import React, { useEffect, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Film,
  Languages,
  Monitor,
  Play,
  Radio,
  Smartphone,
  Terminal,
  UserCheck,
  Volume2,
  X,
} from 'lucide-react';
import { AspectRatioMode, NarrationLanguage, OutputsManifest, StoryboardData } from '../types';
import { getMediaUrl, triggerPipelineRun } from '../api';

interface CinemaScreeningProps {
  storyboard: StoryboardData;
  outputs: OutputsManifest;
  isLive: boolean;
  onRefresh: () => Promise<void>;
}

export const CinemaScreening: React.FC<CinemaScreeningProps> = ({
  storyboard,
  outputs,
  isLive,
  onRefresh,
}) => {
  const [aspectRatio, setAspectRatio] = useState<AspectRatioMode>('16x9');
  const [selectedLang, setSelectedLang] = useState<NarrationLanguage>('en');
  const [currentShotIndex, setCurrentShotIndex] = useState<number>(0);
  const [showRefModal, setShowRefModal] = useState<boolean>(false);
  const [showStyleDrawer, setShowStyleDrawer] = useState<boolean>(false);
  const [videoError, setVideoError] = useState<boolean>(false);
  const [rendering, setRendering] = useState<boolean>(false);
  const [renderError, setRenderError] = useState<string | null>(null);

  const mediaRelPath =
    selectedLang === 'en'
      ? aspectRatio === '16x9'
        ? 'final_16x9.mp4'
        : aspectRatio === '9x16'
          ? 'final_9x16.mp4'
          : 'radio_cut.mp4'
      : aspectRatio === '9x16'
        ? 'final_9x16_am.mp4'
        : 'final_16x9_am.mp4';

  const srtRelPath =
    selectedLang === 'am' && outputs.files?.['subtitles_am.srt']
      ? 'subtitles_am.srt'
      : 'subtitles.srt';

  const videoSrc = getMediaUrl(mediaRelPath);
  const videoExists = Boolean(outputs.files?.[mediaRelPath]) && !videoError;
  const charSheetExists = Boolean(outputs.files?.['reference/character_sheet.png']);

  const currentShot = storyboard.shots[currentShotIndex] || storyboard.shots[0];
  const langNarrationList =
    selectedLang === 'en' ? outputs.narration_en : outputs.narration_am;
  const usesLangSubdir = Boolean(langNarrationList?.includes(currentShot.shot_id));
  const shotHasNarration =
    usesLangSubdir || Boolean(outputs.narration?.includes(currentShot.shot_id));
  const shotAudioSrc = usesLangSubdir
    ? getMediaUrl(`narration/${selectedLang}/${currentShot.shot_id}.wav`)
    : getMediaUrl(`narration/${currentShot.shot_id}.wav`);

  useEffect(() => {
    setVideoError(false);
    setRenderError(null);
  }, [aspectRatio, selectedLang, outputs]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowRefModal(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleTriggerRender = async () => {
    setRendering(true);
    setRenderError(null);
    try {
      await triggerPipelineRun('all', undefined, false, selectedLang);
      await onRefresh();
    } catch (err: unknown) {
      setRenderError(err instanceof Error ? err.message : 'Pipeline execution failed');
    } finally {
      setRendering(false);
    }
  };

  const renderSlate = () => (
    <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center bg-[#0c0c0f]">
      <div className="w-11 h-11 rounded-full border border-white/10 bg-zinc-900 flex items-center justify-center text-zinc-400 mb-4">
        <Film className="w-5 h-5" />
      </div>
      <div className="text-sm font-medium text-zinc-200">
        Awaiting render — run pipeline stage
      </div>
      <p className="text-xs text-zinc-500 mt-1.5 max-w-sm leading-relaxed">
        {mediaRelPath} has not been rendered to disk yet. Run the live pipeline to synthesize{' '}
        {selectedLang === 'en' ? 'English' : 'Amharic'} narration, opening title card, and dual-aspect masters.
      </p>
      <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-900 border border-white/10 font-mono text-[11px] text-zinc-300">
        <Terminal className="w-3.5 h-3.5 text-amber-500" />
        <span>uv run python -m pipeline.run run --language {selectedLang}</span>
      </div>

      {isLive && (
        <button
          type="button"
          onClick={handleTriggerRender}
          disabled={rendering}
          className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold text-xs transition-colors disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{rendering ? 'Rendering Master Pipeline...' : 'Render Master Pipeline'}</span>
        </button>
      )}

      {renderError && (
        <p className="mt-3 text-xs text-rose-400 max-w-md">{renderError}</p>
      )}
    </div>
  );

  return (
    <div className="space-y-8">
      {/* Page Title, Language Toggle & Aspect Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Screening Room</h1>
          <p className="text-sm text-zinc-400 mt-1 font-ethiopic">
            {storyboard.title} · Hailemichael Tesfaye
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 self-start lg:self-auto">
          {/* Language Switcher */}
          <div
            className="inline-flex items-center bg-[#111114] p-1 rounded-lg border border-white/10"
            role="group"
            aria-label="Narration language"
          >
            <span className="flex items-center gap-1 pl-2 pr-1.5 text-[11px] text-zinc-500">
              <Languages className="w-3.5 h-3.5 text-amber-500" />
            </span>
            <button
              type="button"
              onClick={() => setSelectedLang('en')}
              className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${selectedLang === 'en'
                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              English (Primary)
            </button>
            <button
              type="button"
              onClick={() => setSelectedLang('am')}
              className={`px-2.5 py-1.5 rounded-md text-xs font-medium font-ethiopic transition-colors whitespace-nowrap ${selectedLang === 'am'
                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              አማርኛ (Amharic)
            </button>
          </div>

          {/* Aspect Switcher */}
          <div className="inline-flex items-center bg-[#111114] p-1 rounded-lg border border-white/10">
            <button
              type="button"
              onClick={() => setAspectRatio('16x9')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${aspectRatio === '16x9'
                ? 'bg-zinc-800 text-zinc-100 border border-white/10'
                : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              <Monitor className="w-3.5 h-3.5" />
              <span>16:9 Master</span>
            </button>
            <button
              type="button"
              onClick={() => setAspectRatio('9x16')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${aspectRatio === '9x16'
                ? 'bg-zinc-800 text-zinc-100 border border-white/10'
                : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              <Smartphone className="w-3.5 h-3.5" />
              <span>9:16 Vertical</span>
            </button>
            <button
              type="button"
              onClick={() => setAspectRatio('radio_cut')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${aspectRatio === 'radio_cut'
                ? 'bg-zinc-800 text-zinc-100 border border-white/10'
                : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Radio Cut</span>
            </button>
          </div>
        </div>
      </div>

      {/* 12-Column Editorial Screening Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left 8 Cols: Theater Viewport + 10-Shot Filmstrip */}
        <div className="lg:col-span-8 space-y-5">
          {aspectRatio === '9x16' ? (
            <div className="w-full py-4 flex justify-center bg-[#0c0c0f] rounded-xl border border-white/10">
              <div className="relative w-[300px] sm:w-[330px] aspect-[9/16] bg-black rounded-[34px] p-2 border-[3px] border-zinc-800 overflow-hidden">
                <div className="w-full h-full rounded-[26px] overflow-hidden bg-black">
                  {videoExists ? (
                    <video
                      key={videoSrc}
                      controls
                      playsInline
                      preload="metadata"
                      onError={() => setVideoError(true)}
                      className="w-full h-full object-cover bg-black"
                      src={videoSrc}
                    >
                      {outputs.files?.[srtRelPath] && (
                        <track
                          label="English"
                          kind="subtitles"
                          srcLang="en"
                          src={getMediaUrl(srtRelPath)}
                          default
                        />
                      )}
                    </video>
                  ) : (
                    renderSlate()
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="w-full aspect-video bg-black rounded-xl overflow-hidden border border-white/10">
              {videoExists ? (
                <video
                  key={videoSrc}
                  controls
                  playsInline
                  preload="metadata"
                  onError={() => setVideoError(true)}
                  className="w-full h-full object-contain bg-black"
                  src={videoSrc}
                >
                  {outputs.files?.[srtRelPath] && (
                    <track
                      label="English"
                      kind="subtitles"
                      srcLang="en"
                      src={getMediaUrl(srtRelPath)}
                      default
                    />
                  )}
                </video>
              ) : (
                renderSlate()
              )}
            </div>
          )}

          {/* 10-Shot Horizontal Filmstrip */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-4">
              <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                10-Shot Filmstrip
              </span>
              <button
                type="button"
                onClick={() => setShowRefModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-[#111114] hover:border-white/25 text-xs text-zinc-300 hover:text-zinc-100 transition-colors"
              >
                <UserCheck className="w-3.5 h-3.5 text-amber-500" />
                <span>Protagonist Reference Sheet</span>
              </button>
            </div>

            <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
              {storyboard.shots.map((shot, idx) => {
                const isSelected = idx === currentShotIndex;
                const hasKeyframe = outputs.keyframes?.includes(shot.shot_id);
                const shotNum = String(idx + 1).padStart(2, '0');

                return (
                  <button
                    key={shot.shot_id}
                    type="button"
                    onClick={() => setCurrentShotIndex(idx)}
                    title={`${shot.shot_id} — ${shot.subtitle_en}`}
                    className={`group relative aspect-video rounded-md overflow-hidden border text-left transition-all ${isSelected
                      ? 'border-amber-500 ring-1 ring-amber-500/30 bg-zinc-900'
                      : 'border-white/10 bg-[#111114] hover:border-white/25'
                      }`}
                  >
                    {hasKeyframe ? (
                      <img
                        src={getMediaUrl(`keyframes/${shot.shot_id}.png`)}
                        alt={shot.shot_id}
                        className="w-full h-full object-cover opacity-85 group-hover:opacity-100 transition-opacity"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-zinc-900/70">
                        <span
                          className={`font-mono text-xs ${isSelected ? 'text-amber-400 font-semibold' : 'text-zinc-500'
                            }`}
                        >
                          {shotNum}
                        </span>
                      </div>
                    )}
                    <span className="absolute bottom-0.5 left-1 font-mono text-[9px] text-zinc-300/90 bg-black/60 px-1 rounded">
                      {shotNum}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-zinc-500 pt-1">
            <span>Audio spec: Sidechain ducking · Dual-pass -14 LUFS / -1.0 dB TP</span>
            <span className="font-mono">3s intro + {storyboard.total_duration_sec}s contract + 3s AI slate</span>
          </div>
        </div>

        {/* Right 4 Cols: Script Spotlight Card */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-xl bg-[#111114] border border-white/10 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="font-mono text-xs text-amber-400">
                SHOT {String(currentShotIndex + 1).padStart(2, '0')} / {storyboard.shots.length}
              </span>
              <span className="font-mono text-[11px] text-zinc-500">
                {currentShot.duration_sec}s · seed {currentShot.seed}
              </span>
            </div>

            <div className="text-[11px] uppercase tracking-wider text-zinc-400 font-medium">
              {currentShot.shot_type.replace(/_/g, ' ')}
            </div>

            {selectedLang === 'en' ? (
              <>
                <div className="space-y-1.5">
                  <div className="text-[11px] uppercase tracking-wider text-amber-400/90">
                    English Narration (Primary)
                  </div>
                  <p className="text-base leading-relaxed text-zinc-100 font-normal">
                    {currentShot.narration_en || currentShot.subtitle_en}
                  </p>
                </div>
                <div className="space-y-1.5">
                  <div className="text-[11px] uppercase tracking-wider text-zinc-500">
                    Amharic Version
                  </div>
                  <p className="font-ethiopic text-sm leading-[1.8] text-zinc-400">
                    {currentShot.narration_am}
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-1.5">
                  <div className="text-[11px] uppercase tracking-wider text-amber-400/90">
                    Amharic Narration
                  </div>
                  <p className="font-ethiopic text-lg leading-[1.85] text-zinc-100 font-normal">
                    {currentShot.narration_am}
                  </p>
                </div>
                <div className="space-y-1.5">
                  <div className="text-[11px] uppercase tracking-wider text-zinc-500">
                    English Subtitle
                  </div>
                  <p className="text-sm text-zinc-300 leading-relaxed">
                    “{currentShot.subtitle_en}”
                  </p>
                </div>
              </>
            )}

            {shotHasNarration && (
              <div className="pt-2 border-t border-white/10">
                <div className="flex items-center gap-2 text-[11px] text-zinc-400 mb-2">
                  <Volume2 className="w-3.5 h-3.5 text-amber-500" />
                  <span>Shot Audio Stem ({selectedLang.toUpperCase()} · {currentShot.shot_id}.wav)</span>
                </div>
                <audio
                  key={`${selectedLang}-${currentShot.shot_id}`}
                  controls
                  src={shotAudioSrc}
                  className="w-full h-8"
                />
              </div>
            )}

            <div className="pt-4 border-t border-white/10 space-y-1">
              <div className="text-[11px] uppercase tracking-wider text-zinc-500">
                Director Rationale
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">{currentShot.reason}</p>
            </div>

            {/* Subtle Collapsible Style & Prompt Summary */}
            <div className="pt-3 border-t border-white/10">
              <button
                type="button"
                onClick={() => setShowStyleDrawer(!showStyleDrawer)}
                className="w-full flex items-center justify-between text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <span>Visual &amp; Style Direction</span>
                {showStyleDrawer ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>

              {showStyleDrawer && (
                <div className="mt-3 space-y-2.5 text-xs text-zinc-400 leading-relaxed">
                  <div>
                    <span className="text-zinc-500">Visual:</span> {currentShot.visual_prompt}
                  </div>
                  <div>
                    <span className="text-zinc-500">Motion:</span> {currentShot.motion_prompt}
                  </div>
                  <div className="pt-2 border-t border-white/5 space-y-1 text-[11px] text-zinc-500">
                    <div>
                      <span className="text-zinc-400">Tone:</span> {storyboard.style_block.visual_tone}
                    </div>
                    <div>
                      <span className="text-zinc-400">Lighting:</span> {storyboard.style_block.lighting}
                    </div>
                    <div>
                      <span className="text-zinc-400">Palette:</span> {storyboard.style_block.color_palette}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Protagonist Reference Sheet Modal */}
      {showRefModal && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6"
          onClick={() => setShowRefModal(false)}
        >
          <div
            className="max-w-3xl w-full rounded-xl bg-[#111114] border border-white/15 p-6 space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">
                  Protagonist Reference Sheet
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  3-stage facial &amp; wardrobe anchor across childhood, teen Abinet study, and university engineering.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowRefModal(false)}
                className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {charSheetExists ? (
              <div className="rounded-lg overflow-hidden border border-white/10 bg-black">
                <img
                  src={getMediaUrl('reference/character_sheet.png')}
                  alt="Protagonist 3-Stage Reference Sheet"
                  className="w-full max-h-[380px] object-contain mx-auto"
                />
              </div>
            ) : (
              <div className="p-8 rounded-lg border border-white/10 bg-[#09090b] text-center space-y-2">
                <p className="text-sm text-zinc-300">Character reference sheet not yet rendered</p>
                <p className="text-xs text-zinc-500 font-mono">
                  uv run python -m pipeline.run run --stage keyframes
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              {Object.entries(storyboard.character_sheet.progression_stages || {}).map(
                ([stageKey, desc]) => (
                  <div
                    key={stageKey}
                    className="p-3 rounded-lg border border-white/10 bg-[#09090b] space-y-1"
                  >
                    <div className="font-mono text-[11px] text-amber-400 uppercase">
                      {stageKey.replace(/_/g, ' ')}
                    </div>
                    <p className="text-zinc-400 leading-relaxed">{desc}</p>
                  </div>
                ),
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

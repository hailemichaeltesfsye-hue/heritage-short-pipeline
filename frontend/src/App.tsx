import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { CinemaScreening } from './components/CinemaScreening';
import { StoryboardLab } from './components/StoryboardLab';
import { Observability } from './components/Observability';
import { EngineeringJournals } from './components/EngineeringJournals';
import {
  checkBackendConnection,
  fetchDocs,
  fetchMetrics,
  fetchOutputsManifest,
  fetchStoryboard,
} from './api';
import { MetricsData, OutputsManifest, StoryboardData, ViewMode } from './types';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('screening');
  const [isLive, setIsLive] = useState<boolean>(false);
  const [storyboard, setStoryboard] = useState<StoryboardData | null>(null);
  const [outputs, setOutputs] = useState<OutputsManifest>({ files: {}, keyframes: [], narration: [] });
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [docs, setDocs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const live = await checkBackendConnection();
      setIsLive(live);

      const [sbRes, outRes, metRes, docRes] = await Promise.all([
        fetchStoryboard(),
        fetchOutputsManifest(),
        fetchMetrics(),
        fetchDocs(),
      ]);

      setStoryboard(sbRes.storyboard);
      setOutputs(outRes);
      setMetrics(metRes);
      setDocs(docRes);
    } catch (e) {
      console.error('Error loading showcase data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col font-sans">
      <Navbar currentView={currentView} onSelectView={setCurrentView} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
            <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <div className="text-xs text-zinc-500 font-mono">Loading Studio...</div>
          </div>
        ) : storyboard ? (
          <>
            {currentView === 'screening' && (
              <CinemaScreening
                storyboard={storyboard}
                outputs={outputs}
                isLive={isLive}
                onRefresh={loadData}
              />
            )}
            {currentView === 'storyboard' && (
              <StoryboardLab
                storyboard={storyboard}
                outputs={outputs}
                isLive={isLive}
                onRefresh={loadData}
              />
            )}
            {currentView === 'observability' && metrics && (
              <Observability metrics={metrics} isLive={isLive} onRefresh={loadData} />
            )}
            {currentView === 'journals' && <EngineeringJournals docs={docs} />}
          </>
        ) : (
          <div className="p-8 text-center text-sm text-zinc-400">
            Unable to load storyboard contract. Run <code className="font-mono">make export-showcase</code> or start FastAPI.
          </div>
        )}
      </main>

      <footer className="border-t border-white/10 py-6 text-center text-xs text-zinc-500">
        <p className="font-ethiopic">
          AI-Content Generation: The Heritage Short · “Hulum Neger Lebego New (ሁሉም ነገር ለበጎ ነው)”
        </p>
        <p className="mt-1 text-[11px] text-zinc-600">
          Hailemichael Tesfaye · LangGraph Multi-Agent Core · Gemini 3.8 / Edge-TTS · Cloudflare FLUX · Kaggle Wan 2.2 · FFmpeg
        </p>
      </footer>
    </div>
  );
};

export default App;

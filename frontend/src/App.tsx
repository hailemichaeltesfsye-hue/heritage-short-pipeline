import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { CinemaScreening } from './components/CinemaScreening';
import { StoryboardLab } from './components/StoryboardLab';
import { Observability } from './components/Observability';
import { EngineeringJournals } from './components/EngineeringJournals';
import { checkBackendConnection, fetchDocs, fetchMetrics, fetchStoryboard } from './api';
import { MetricsData, StoryboardData, ViewMode } from './types';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('screening');
  const [isLive, setIsLive] = useState<boolean>(false);
  const [storyboard, setStoryboard] = useState<StoryboardData | null>(null);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [docs, setDocs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    try {
      const live = await checkBackendConnection();
      setIsLive(live);

      const [sbRes, metRes, docRes] = await Promise.all([
        fetchStoryboard(),
        fetchMetrics(),
        fetchDocs(),
      ]);

      setStoryboard(sbRes.storyboard);
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
    <div className="min-h-screen bg-studio-bg flex flex-col font-sans">
      <Navbar currentView={currentView} onSelectView={setCurrentView} isLive={isLive} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
            <div className="w-8 h-8 border-2 border-studio-amber border-t-transparent rounded-full animate-spin" />
            <div className="text-xs text-neutral-400 font-cinematic uppercase tracking-widest">
              Initializing Studio Showcase...
            </div>
          </div>
        ) : storyboard ? (
          <>
            {currentView === 'screening' && <CinemaScreening storyboard={storyboard} />}
            {currentView === 'storyboard' && (
              <StoryboardLab storyboard={storyboard} isLive={isLive} onRefresh={loadData} />
            )}
            {currentView === 'observability' && metrics && (
              <Observability metrics={metrics} isLive={isLive} onRefresh={loadData} />
            )}
            {currentView === 'journals' && <EngineeringJournals docs={docs} />}
          </>
        ) : (
          <div className="p-8 text-center text-sm text-neutral-400">
            Failed to load storyboard data. Ensure outputs are exported.
          </div>
        )}
      </main>

      <footer className="border-t border-studio-border/60 py-6 text-center text-xs text-neutral-500 font-sans">
        <p>AI-Content Generation: The Heritage Short • "Hulum Neger Lebego New (ሁሉም ነገር ለበጎ ነው)"</p>
        <p className="mt-1 text-[11px] text-neutral-600">
          Created by Hailemichael Tesfaye • Multi-Agent LangGraph Core • Cloudflare Workers AI FLUX • Kaggle Wan 2.2 • FFmpeg
        </p>
      </footer>
    </div>
  );
};

export default App;

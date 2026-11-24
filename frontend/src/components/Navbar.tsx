import React from 'react';
import { Film, Sliders, Activity, BookOpen, Server, Globe } from 'lucide-react';
import { ViewMode } from '../types';

interface NavbarProps {
  currentView: ViewMode;
  onSelectView: (view: ViewMode) => void;
  isLive: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onSelectView, isLive }) => {
  const navItems: { id: ViewMode; label: string; icon: React.ReactNode }[] = [
    { id: 'screening', label: 'Cinema Screening', icon: <Film className="w-4 h-4" /> },
    { id: 'storyboard', label: 'Storyboard & Shot Lab', icon: <Sliders className="w-4 h-4" /> },
    { id: 'observability', label: 'Observability & Telemetry', icon: <Activity className="w-4 h-4" /> },
    { id: 'journals', label: 'Engineering Journals', icon: <BookOpen className="w-4 h-4" /> },
  ];

  return (
    <header className="border-b border-studio-border bg-studio-card/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onSelectView('screening')}>
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-studio-gold to-studio-amber flex items-center justify-center shadow-lg shadow-amber-900/20">
            <Film className="w-5 h-5 text-black" />
          </div>
          <div>
            <div className="font-cinematic tracking-wider text-base font-bold text-white flex items-center gap-2">
              HULUM NEGER LEBEGO NEW
              <span className="text-[10px] uppercase font-sans font-semibold tracking-wider px-2 py-0.5 rounded bg-studio-amber/20 text-studio-gold border border-studio-amber/40">
                Heritage Short
              </span>
            </div>
            <div className="text-xs text-neutral-400 font-sans">Multi-Agent AI Filmmaking Pipeline</div>
          </div>
        </div>

        <nav className="flex items-center space-x-1 sm:space-x-2">
          {navItems.map((item) => {
            const active = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectView(item.id)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                  active
                    ? 'bg-studio-amber/20 text-studio-gold border border-studio-amber/40 shadow-sm'
                    : 'text-neutral-300 hover:text-white hover:bg-studio-surface'
                }`}
              >
                {item.icon}
                <span className="hidden md:inline">{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="flex items-center space-x-2">
          <div
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isLive
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50'
                : 'bg-neutral-800 text-neutral-300 border-neutral-700'
            }`}
            title={isLive ? 'Connected to local FastAPI backend' : 'Serving static showcase bundle'}
          >
            {isLive ? <Server className="w-3.5 h-3.5 text-emerald-400" /> : <Globe className="w-3.5 h-3.5 text-amber-400" />}
            <span className="hidden sm:inline">{isLive ? 'FastAPI Live' : 'Showcase Mode'}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

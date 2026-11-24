import React from 'react';
import { Film } from 'lucide-react';
import { ViewMode } from '../types';

interface NavbarProps {
  currentView: ViewMode;
  onSelectView: (view: ViewMode) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onSelectView }) => {
  const navItems: { id: ViewMode; label: string }[] = [
    { id: 'screening', label: 'Screening Room' },
    { id: 'storyboard', label: 'Storyboard Lab' },
    { id: 'observability', label: 'Telemetry' },
    { id: 'journals', label: 'Journals' },
  ];

  return (
    <header className="h-16 border-b border-white/10 bg-[#09090b]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between gap-6">
        <button
          type="button"
          onClick={() => onSelectView('screening')}
          className="flex items-center gap-3 text-left shrink-0 focus:outline-none group"
        >
          <span className="w-7 h-7 rounded-md border border-white/15 bg-zinc-900 flex items-center justify-center text-amber-500 group-hover:border-amber-500/50 transition-colors">
            <Film className="w-3.5 h-3.5" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-zinc-100 whitespace-nowrap">
            Hulum Neger Lebego New
          </span>
        </button>

        <nav className="flex items-center gap-6 sm:gap-8 h-full overflow-x-auto">
          {navItems.map((item) => {
            const active = currentView === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectView(item.id)}
                className={`h-full flex items-center text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  active
                    ? 'border-amber-500 text-zinc-100'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};

import React, { useState } from 'react';
import { BookOpen, FileText, Check, Copy } from 'lucide-react';

interface EngineeringJournalsProps {
  docs: Record<string, string>;
}

export const EngineeringJournals: React.FC<EngineeringJournalsProps> = ({ docs }) => {
  const availableDocs = ['DESIGN', 'ARCHITECTURE', 'EXPERIMENTS', 'FAILURES', 'COSTS', 'ETHICS'];
  const [activeDoc, setActiveDoc] = useState<string>('DESIGN');
  const [copied, setCopied] = useState<boolean>(false);

  const currentContent = docs[activeDoc] || `# ${activeDoc}.md\nLoading documentation...`;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-studio-border pb-4">
        <div>
          <h2 className="text-xl font-cinematic font-bold text-white tracking-wide">Engineering Journals & Governance</h2>
          <p className="text-sm text-neutral-400 mt-0.5">
            Production system design, multi-agent architecture, self-consent records, and cost logs
          </p>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-surface border border-studio-border text-xs text-neutral-300 hover:text-white transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Navigation Sidebar (3 Cols) */}
        <div className="md:col-span-3 space-y-1">
          {availableDocs.map((docKey) => {
            const isSelected = activeDoc === docKey;
            return (
              <button
                key={docKey}
                onClick={() => setActiveDoc(docKey)}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-xs font-medium flex items-center justify-between transition-all ${
                  isSelected
                    ? 'bg-studio-amber text-white font-bold shadow'
                    : 'bg-studio-card text-neutral-300 hover:bg-studio-surface hover:text-white border border-studio-border'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-3.5 h-3.5" />
                  <span>{docKey}.md</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Document Content Viewer (9 Cols) */}
        <div className="md:col-span-9 p-6 rounded-2xl bg-studio-card border border-studio-border shadow-xl">
          <div className="prose prose-invert prose-amber max-w-none text-xs sm:text-sm leading-relaxed space-y-4">
            <pre className="whitespace-pre-wrap font-sans text-neutral-300 bg-transparent p-0 overflow-x-auto">
              {currentContent}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

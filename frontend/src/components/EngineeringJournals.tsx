import React, { useState } from 'react';
import { Check, Copy, FileText } from 'lucide-react';
import { SimpleMarkdown } from './SimpleMarkdown';

interface EngineeringJournalsProps {
  docs: Record<string, string>;
}

const DOC_ORDER = ['DESIGN', 'ARCHITECTURE', 'EXPERIMENTS', 'FAILURES', 'COSTS', 'ETHICS'];

export const EngineeringJournals: React.FC<EngineeringJournalsProps> = ({ docs }) => {
  const [activeDoc, setActiveDoc] = useState<string>('FAILURES');
  const [copied, setCopied] = useState<boolean>(false);

  const currentContent = docs[activeDoc] || `# ${activeDoc}.md\nLoading documentation...`;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Journals</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Architecture specifications, incident post-mortems, economics, and ethical consent framework
          </p>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#111114] border border-white/10 hover:border-white/25 text-xs text-zinc-300 hover:text-zinc-100 transition-colors self-start sm:self-auto"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        <div className="md:col-span-3 space-y-1">
          {DOC_ORDER.map((docKey) => {
            const isSelected = activeDoc === docKey;
            return (
              <button
                key={docKey}
                type="button"
                onClick={() => setActiveDoc(docKey)}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-xs font-mono flex items-center gap-2.5 transition-colors border ${
                  isSelected
                    ? 'bg-zinc-900 text-zinc-100 border-amber-500/60'
                    : 'bg-transparent text-zinc-400 border-transparent hover:bg-zinc-900/50 hover:text-zinc-200'
                }`}
              >
                <FileText className={`w-3.5 h-3.5 ${isSelected ? 'text-amber-500' : 'text-zinc-500'}`} />
                <span>{docKey}.md</span>
              </button>
            );
          })}
        </div>

        <article className="md:col-span-9 p-6 sm:p-8 rounded-xl bg-[#111114] border border-white/10">
          <SimpleMarkdown content={currentContent} />
        </article>
      </div>
    </div>
  );
};

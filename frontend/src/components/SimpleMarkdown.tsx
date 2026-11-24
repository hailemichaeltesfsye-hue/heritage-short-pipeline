import React from 'react';

interface SimpleMarkdownProps {
  content: string;
}

function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-zinc-800/90 text-amber-300 font-mono text-[12px]"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

export const SimpleMarkdown: React.FC<SimpleMarkdownProps> = ({ content }) => {
  const lines = content.split(/\r?\n/);
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code blocks
    if (line.trim().startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <pre
          key={`code-${i}`}
          className="my-4 p-4 rounded-lg bg-[#09090b] border border-white/10 font-mono text-xs text-zinc-300 overflow-x-auto leading-relaxed"
        >
          <code>{codeLines.join('\n')}</code>
        </pre>,
      );
      i++;
      continue;
    }

    // Markdown tables
    if (line.trim().startsWith('|') && i + 1 < lines.length && lines[i + 1].includes('---')) {
      const parseRow = (row: string) =>
        row
          .trim()
          .replace(/^\|/, '')
          .replace(/\|$/, '')
          .split('|')
          .map((c) => c.trim());

      const headers = parseRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(parseRow(lines[i]));
        i++;
      }

      elements.push(
        <div key={`table-${i}`} className="my-5 overflow-x-auto rounded-lg border border-white/10">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#09090b] text-zinc-400 border-b border-white/10">
              <tr>
                {headers.map((h, hi) => (
                  <th key={hi} className="py-2.5 px-3 font-medium">
                    {renderInline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-zinc-300">
              {rows.map((r, ri) => (
                <tr key={ri} className="hover:bg-white/[0.02]">
                  {r.map((cell, ci) => (
                    <td key={ci} className="py-2.5 px-3 align-top leading-relaxed">
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Headings
    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-xl font-semibold text-zinc-100 tracking-tight mb-4">
          {renderInline(line.slice(2))}
        </h1>,
      );
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h2
          key={`h2-${i}`}
          className="text-base font-semibold text-zinc-100 mt-7 mb-3 pt-4 border-t border-white/10"
        >
          {renderInline(line.slice(3))}
        </h2>,
      );
      i++;
      continue;
    }
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-sm font-semibold text-amber-400 mt-5 mb-2">
          {renderInline(line.slice(4))}
        </h3>,
      );
      i++;
      continue;
    }

    // Horizontal rule
    if (line.trim() === '---') {
      elements.push(<hr key={`hr-${i}`} className="my-6 border-white/10" />);
      i++;
      continue;
    }

    // Unordered or ordered lists
    if (/^\s*[-*]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      const ordered = /^\s*\d+\.\s+/.test(line);
      while (i < lines.length && (/^\s*[-*]\s+/.test(lines[i]) || /^\s*\d+\.\s+/.test(lines[i]))) {
        items.push(lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, ''));
        i++;
      }
      const ListTag = ordered ? 'ol' : 'ul';
      elements.push(
        <ListTag
          key={`list-${i}`}
          className={`my-3 space-y-1.5 pl-5 text-sm text-zinc-300 leading-relaxed ${
            ordered ? 'list-decimal' : 'list-disc'
          }`}
        >
          {items.map((item, idx) => (
            <li key={idx}>{renderInline(item)}</li>
          ))}
        </ListTag>,
      );
      continue;
    }

    // Blank line
    if (!line.trim()) {
      i++;
      continue;
    }

    // Paragraph
    elements.push(
      <p key={`p-${i}`} className="text-sm text-zinc-300 leading-relaxed my-2.5">
        {renderInline(line)}
      </p>,
    );
    i++;
  }

  return <div>{elements}</div>;
};

import React from 'react';

function SummaryPanel({ summary, filename, loading }) {
  const abstract = summary?.abstract;
  const sections = summary?.sections || {};
  const hasContent = abstract || Object.keys(sections).length > 0;

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-paper-200 shadow-sm p-4">
        <h2 className="font-display text-lg text-paper-900 mb-3">Paper Summary</h2>
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-paper-200 rounded w-full" />
          <div className="h-3 bg-paper-200 rounded w-5/6" />
          <div className="h-3 bg-paper-200 rounded w-4/5" />
          <div className="h-3 bg-paper-200 rounded w-full" />
          <div className="h-3 bg-paper-200 rounded w-3/4" />
        </div>
        <p className="text-sm text-paper-500 mt-2">Extracting and summarizing…</p>
      </div>
    );
  }

  if (!hasContent) {
    return (
      <div className="bg-white rounded-xl border border-paper-200 shadow-sm p-4">
        <h2 className="font-display text-lg text-paper-900 mb-3">Paper Summary</h2>
        <p className="text-sm text-paper-500">Upload a PDF to see the AI-generated summary here.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-paper-200 shadow-sm p-4 max-h-[400px] overflow-y-auto">
      <h2 className="font-display text-lg text-paper-900 mb-3">Paper Summary</h2>
      {filename && (
        <p className="text-xs text-paper-500 mb-2 truncate" title={filename}>
          {filename}
        </p>
      )}
      {abstract && (
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-paper-800 mb-1">Abstract</h3>
          <p className="text-sm text-paper-700 leading-relaxed">{abstract}</p>
        </div>
      )}
      {Object.keys(sections).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-paper-800 mb-2">Sections</h3>
          <ul className="space-y-2">
            {Object.entries(sections).map(([title, text]) => (
              <li key={title}>
                <span className="text-xs font-medium text-accent">{title}</span>
                <p className="text-sm text-paper-700 mt-0.5">{text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default SummaryPanel;

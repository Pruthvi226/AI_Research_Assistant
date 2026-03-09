import React from 'react';

function InsightsPanel({ data, loading }) {
  const contributions = data?.key_contributions || [];
  const futureResearch = data?.future_research || [];
  const limitations = data?.limitations || [];
  const researchGaps = data?.research_gaps || [];
  const suggestedTitles = data?.suggested_titles || [];
  const importantSentences = data?.important_sentences || [];

  const hasAny =
    contributions.length > 0 ||
    futureResearch.length > 0 ||
    limitations.length > 0 ||
    researchGaps.length > 0 ||
    suggestedTitles.length > 0 ||
    importantSentences.length > 0;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto">
        <h2 className="font-display text-lg text-paper-900 mb-3">Research Insights</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-paper-200 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!hasAny) {
    return (
      <div className="max-w-7xl mx-auto">
        <h2 className="font-display text-lg text-paper-900 mb-3">Research Insights</h2>
        <p className="text-sm text-paper-500">Upload a paper to see key contributions, future research ideas, and more.</p>
      </div>
    );
  }

  const list = (items, title, accent = false) => {
    if (!items.length) return null;
    return (
      <div className={`rounded-lg border p-4 ${accent ? 'border-accent/30 bg-accent/5' : 'border-paper-200 bg-white'}`}>
        <h3 className="text-sm font-semibold text-paper-800 mb-2">{title}</h3>
        <ul className="space-y-1.5 text-sm text-paper-700">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-paper-400 flex-shrink-0">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto">
      <h2 className="font-display text-lg text-paper-900 mb-4">Research Insights</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list(contributions, 'Key Contributions')}
        {list(futureResearch, 'Future Research Directions', true)}
        {list(limitations, 'Limitations')}
        {list(researchGaps, 'Research Gap Detection')}
        {list(suggestedTitles, 'Suggested Paper Titles')}
        {importantSentences.length > 0 && (
          <div className="rounded-lg border border-paper-200 bg-white p-4 md:col-span-2">
            <h3 className="text-sm font-semibold text-paper-800 mb-2">Important Sentences</h3>
            <ul className="space-y-1.5 text-sm text-paper-700">
              {importantSentences.map((s, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-paper-400 flex-shrink-0">•</span>
                  <span className="italic">{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default InsightsPanel;

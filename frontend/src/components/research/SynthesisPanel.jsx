import React from 'react';
import { Sparkles, X, GitPullRequest, Layout, Download, CheckCircle2 } from 'lucide-react';

const SynthesisPanel = ({ synthesisData, onClose, onActivateWorkspace, isActiveWorkspace }) => {
  if (!synthesisData) return null;

  const { headers, comparisons } = synthesisData;
  const sessionIds = Object.keys(headers);

  // Export synthesis report
  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(synthesisData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `Scientia_Synthesis_Matrix.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="h-full flex flex-col p-6 bg-[#0a0a0c] overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 select-none shrink-0">
        <div>
          <h2 className="text-2xl font-bold font-['Outfit'] tracking-tight text-white flex items-center gap-2">
            <GitPullRequest size={24} className="text-indigo-400 rotate-90" /> Comparative Synthesis Lab
          </h2>
          <p className="text-xs text-slate-500 mt-1">Cross-paper comparative synthesis compiled dynamically using Gemini.</p>
        </div>

        <div className="flex gap-3 shrink-0">
          <button
            onClick={onActivateWorkspace}
            disabled={isActiveWorkspace}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold shadow-lg transition-all ${isActiveWorkspace ? 'bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 cursor-default' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20 active:scale-95'}`}
          >
            {isActiveWorkspace ? (
              <>
                <CheckCircle2 size={14} /> Multi-Doc Active
              </>
            ) : (
              <>
                <Sparkles size={14} /> Activate RAG Multi-Doc Chat
              </>
            )}
          </button>

          <button 
            onClick={handleExport}
            className="p-2.5 glass-panel border-white/10 text-slate-400 hover:text-white hover:bg-white/5 transition-all text-xs flex items-center gap-1.5"
          >
            <Download size={14} /> Export
          </button>

          <button 
            onClick={onClose}
            className="p-2.5 glass-panel border-white/10 text-slate-400 hover:text-white hover:bg-white/5 transition-all"
            title="Return to library"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Main Comparative Matrix Grid */}
      <div className="flex-1 overflow-x-auto min-h-[400px]">
        <table className="w-full border-collapse text-left min-w-[700px]">
          {/* Header Row */}
          <thead>
            <tr className="border-b border-white/10 select-none">
              <th className="py-4 pr-6 text-xs font-bold text-slate-400 uppercase tracking-wider w-1/4">Research Index</th>
              {sessionIds.map(id => (
                <th key={id} className="py-4 px-6 text-xs font-bold text-white uppercase tracking-wider w-1/4 min-w-[200px] align-top">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
                      <Layout size={12} />
                    </div>
                    <span className="line-clamp-2 leading-relaxed" title={headers[id]}>{headers[id]}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Comparisons List */}
          <tbody>
            {comparisons.map((c, idx) => (
              <tr key={idx} className="border-b border-white/5 hover:bg-white/[0.005] transition-colors">
                {/* Metric Explanation Column */}
                <td className="py-6 pr-6 align-top">
                  <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider block mb-1">{c.attribute}</span>
                  <p className="text-[10px] text-slate-500 leading-relaxed max-w-[200px]">{c.explanation}</p>
                </td>

                {/* Values columns side-by-side */}
                {sessionIds.map(id => (
                  <td key={id} className="py-6 px-6 align-top text-xs text-slate-300 leading-relaxed font-mono">
                    <div className="p-4 bg-white/[0.01] border border-white/5 rounded-xl h-full font-serif italic text-slate-200">
                      "{c.values[id] || "No comparative metrics generated for this paper."}"
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SynthesisPanel;

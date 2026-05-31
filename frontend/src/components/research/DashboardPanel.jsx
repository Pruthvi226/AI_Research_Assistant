import React from 'react';
import { BookOpen, FileText, Sparkles, Clock, Compass, Activity, CheckSquare } from 'lucide-react';

const DashboardPanel = ({ papersCount, activePaper, apiSettings }) => {
  // Estimate stats
  const timeSavedHours = papersCount * 3.5;
  const activeEngine = apiSettings.has_key ? "Google Gemini 2.5 Flash" : "Local Model Fallback";

  const stats = [
    { label: "Analyzed Documents", value: papersCount, icon: BookOpen, color: "text-indigo-400 bg-indigo-500/10" },
    { label: "Reading Time Saved", value: `${timeSavedHours.toFixed(1)} hrs`, icon: Clock, color: "text-emerald-400 bg-emerald-500/10" },
    { label: "AI Reasoning Model", value: activeEngine, icon: Sparkles, color: "text-amber-400 bg-amber-500/10" },
  ];

  return (
    <div className="h-full flex flex-col p-6 bg-[#0a0a0c] overflow-y-auto">
      {/* Header */}
      <div className="mb-8 select-none">
        <h2 className="text-2xl font-bold font-['Outfit'] tracking-tight text-white flex items-center gap-2">
          <Activity size={24} className="text-indigo-400" /> Scientia.ai Command Center
        </h2>
        <p className="text-xs text-slate-500 mt-1">Aggregated statistics, workspace configurations, and technical reading metrics.</p>
      </div>

      {/* Grid of stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 select-none">
        {stats.map((stat, i) => (
          <div key={i} className="glass-panel p-6 border-white/5 bg-white/[0.005]">
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">{stat.label}</span>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${stat.color}`}>
                <stat.icon size={16} />
              </div>
            </div>
            <p className="text-2xl font-bold font-['Outfit'] text-white">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Workspace Info */}
        <div className="glass-panel p-6 border-white/5 bg-indigo-500/[0.005]">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2 select-none">
            <FileText size={16} className="text-indigo-400" /> Active Technical Workspace
          </h3>

          {activePaper ? (
            <div className="space-y-4">
              <div className="p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                <p className="text-xs font-semibold text-indigo-400 tracking-wider uppercase mb-1">Active File</p>
                <p className="text-sm font-bold text-white truncate">{activePaper.filename}</p>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">ID: {activePaper.session_id}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 select-none">
                <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg">
                  <span className="text-[9px] text-slate-500 font-semibold block mb-0.5 uppercase">Key Contributions</span>
                  <span className="text-sm font-bold text-slate-200 font-['Outfit']">
                    {activePaper.key_contributions?.length || 0} Points
                  </span>
                </div>
                <div className="p-3 bg-white/[0.01] border border-white/5 rounded-lg">
                  <span className="text-[9px] text-slate-500 font-semibold block mb-0.5 uppercase">Document Structure</span>
                  <span className="text-sm font-bold text-slate-200 font-['Outfit']">
                    {Object.keys(activePaper.summary?.sections || {}).length || 0} Sections
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center select-none">
              <p className="text-xs text-slate-500 italic">No technical document is currently active.</p>
              <p className="text-[10px] text-slate-600 max-w-xs mx-auto mt-2">
                Open "My Documents" or upload a new PDF via the "Chat Assistant" to activate a workspace.
              </p>
            </div>
          )}
        </div>

        {/* System Activity & Goals */}
        <div className="glass-panel p-6 border-white/5 bg-white/[0.005] select-none">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <CheckSquare size={16} className="text-indigo-400" /> Research Roadmap
          </h3>

          <ul className="space-y-3.5">
            <li className="flex gap-3 items-start">
              <div className="w-5 h-5 rounded bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">1</div>
              <div>
                <p className="text-xs font-semibold text-slate-200">Dynamic Keyring Validation</p>
                <p className="text-[10px] text-slate-500 mt-0.5">Integrate user API keys seamlessly on-demand to activate cloud models.</p>
              </div>
            </li>
            <li className="flex gap-3 items-start">
              <div className="w-5 h-5 rounded bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">2</div>
              <div>
                <p className="text-xs font-semibold text-slate-200">Semantic Vectorization</p>
                <p className="text-[10px] text-slate-500 mt-0.5">Execute FAISS clustering across local chunks to establish immediate RAG search caches.</p>
              </div>
            </li>
            <li className="flex gap-3 items-start">
              <div className="w-5 h-5 rounded bg-slate-500/20 text-slate-400 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">3</div>
              <div>
                <p className="text-xs font-semibold text-slate-200">Microservice Containerization</p>
                <p className="text-[10px] text-slate-500 mt-0.5">Orchestrate front-to-back assets inside secure, lightweight Docker containers.</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DashboardPanel;

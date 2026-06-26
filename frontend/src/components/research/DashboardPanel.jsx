import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { BookOpen, FileText, Sparkles, Clock, Activity, CheckSquare, Database, Download, RefreshCw } from 'lucide-react';

const DashboardPanel = ({ papersCount, activePaper, apiSettings }) => {
  const [agentLogs, setAgentLogs] = useState([]);
  const [generatedOutputs, setGeneratedOutputs] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboardData = useCallback(async () => {
    setRefreshing(true);
    try {
      const [logsRes, outputsRes, jobsRes] = await Promise.all([
        axios.get('/api/agent-logs?limit=8'),
        axios.get('/api/generated-outputs?limit=8'),
        axios.get('/api/jobs?limit=5')
      ]);
      setAgentLogs(logsRes.data.agent_logs || []);
      setGeneratedOutputs(outputsRes.data.generated_outputs || []);
      setJobs(jobsRes.data.jobs || []);
    } catch (err) {
      console.error('Failed to load agent dashboard data:', err);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Estimate stats
  const timeSavedHours = papersCount * 3.5;
  const activeEngine = apiSettings.has_key ? "Google Gemini 2.5 Flash" : "Local Model Fallback";

  const stats = [
    { label: "Analyzed Documents", value: papersCount, icon: BookOpen, color: "text-indigo-400 bg-indigo-500/10" },
    { label: "Reading Time Saved", value: `${timeSavedHours.toFixed(1)} hrs`, icon: Clock, color: "text-emerald-400 bg-emerald-500/10" },
    { label: "AI Reasoning Model", value: activeEngine, icon: Sparkles, color: "text-amber-400 bg-amber-500/10" },
    { label: "Generated Outputs", value: generatedOutputs.length, icon: Database, color: "text-cyan-400 bg-cyan-500/10" },
  ];

  return (
    <div className="h-full flex flex-col p-6 bg-[#0a0a0c] overflow-y-auto">
      {/* Header */}
      <div className="mb-8 select-none flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-['Outfit'] tracking-tight text-white flex items-center gap-2">
            <Activity size={24} className="text-indigo-400" /> Scientia.ai Command Center
          </h2>
          <p className="text-xs text-slate-500 mt-1">Aggregated statistics, workspace configurations, and technical reading metrics.</p>
        </div>
        <button
          onClick={loadDashboardData}
          disabled={refreshing}
          className="self-start sm:self-auto inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/10 transition-all disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Grid of stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8 select-none">
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
            <CheckSquare size={16} className="text-indigo-400" /> Background Jobs
          </h3>

          {jobs.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No background jobs have run in this session.</p>
          ) : (
            <div className="space-y-3 max-h-72 overflow-y-auto pr-2">
              {jobs.map(job => (
                <div key={job.id} className="p-3 bg-white/[0.02] border border-white/5 rounded-lg">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <span className="text-xs font-bold text-slate-200">{job.name}</span>
                    <span className="text-[9px] uppercase tracking-wider text-indigo-300">{job.status}</span>
                  </div>
                  <p className="text-[10px] text-slate-500 line-clamp-1">{job.message}</p>
                  <div className="h-1 bg-white/10 rounded-full overflow-hidden mt-2">
                    <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${job.progress || 0}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div className="glass-panel p-6 border-white/5 bg-white/[0.005]">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Activity size={16} className="text-emerald-400" /> Agent Logs
          </h3>
          {agentLogs.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No agent activity has been recorded yet.</p>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
              {agentLogs.map(log => (
                <div key={log.id} className="p-3 bg-white/[0.02] border border-white/5 rounded-lg">
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <span className="text-xs font-bold text-emerald-300">{log.selected_agent}</span>
                    <span className="text-[9px] uppercase tracking-wider text-slate-500">{log.status}</span>
                  </div>
                  <p className="text-[10px] text-slate-500 line-clamp-1">{log.intent}</p>
                  <p className="text-[11px] text-slate-300 line-clamp-2 mt-1">{log.query}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="glass-panel p-6 border-white/5 bg-white/[0.005]">
          <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Download size={16} className="text-cyan-400" /> Generated Outputs
          </h3>
          {generatedOutputs.length === 0 ? (
            <p className="text-xs text-slate-500 italic">Generated code, scripts, and audio will appear here.</p>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
              {generatedOutputs.map(output => (
                <div key={output.id} className="p-3 bg-white/[0.02] border border-white/5 rounded-lg">
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <span className="text-xs font-bold text-cyan-300">{output.title || output.output_type}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] uppercase tracking-wider text-slate-500">{output.output_type}</span>
                      <a
                        href={`/api/generated-outputs/${output.id}/download`}
                        download
                        className="text-[9px] font-bold uppercase tracking-wider text-emerald-300 hover:text-emerald-200"
                      >
                        Download
                      </a>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500 line-clamp-1">{output.session_id}</p>
                  {output.file_path && (
                    <p className="text-[10px] text-slate-400 line-clamp-1 mt-1 font-mono">{output.file_path}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPanel;

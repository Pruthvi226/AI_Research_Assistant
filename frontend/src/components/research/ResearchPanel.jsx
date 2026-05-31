import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Copy, Check, Info, AlertTriangle, Lightbulb, Compass, Award, FileText, ChevronDown, Download, Headphones, Volume2, Play, Pause, Loader2, Sliders, Code, Terminal, ExternalLink, Star, Sparkles } from 'lucide-react';



// Custom lightweight parser to convert GFM Markdown tables into gorgeous interactive HTML grids
const parseMarkdownTable = (markdown) => {
  if (!markdown) return null;
  
  const lines = markdown.trim().split('\n');
  if (lines.length < 2) return null;

  // Filter out table layout/separator borders (e.g. |---|---|)
  const dataLines = lines.filter(line => !line.match(/^\s*\|?\s*:?-+:?\s*\|/));
  
  if (dataLines.length === 0) return null;

  const parseRow = (line) => {
    let cleaned = line.trim();
    if (cleaned.startsWith('|')) cleaned = cleaned.substring(1);
    if (cleaned.endsWith('|')) cleaned = cleaned.substring(0, cleaned.length - 1);
    return cleaned.split('|').map(cell => cell.trim());
  };

  const headerCells = parseRow(dataLines[0]);
  const bodyRows = dataLines.slice(1).map(parseRow);

  return (
    <div className="overflow-x-auto w-full border border-white/5 rounded-xl my-4 select-none">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="bg-white/5 border-b border-white/10 font-['Outfit'] font-semibold text-slate-300">
            {headerCells.map((cell, idx) => (
              <th key={idx} className="py-2.5 px-4">{cell}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-white/5 hover:bg-white/[0.01] transition-all font-mono text-slate-400">
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="py-2.5 px-4">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ResearchPanel = ({ activePaper, loading }) => {
  const [activeTab, setActiveTab] = useState('summary');
  const [copiedSection, setCopiedSection] = useState(null);
  const [expandedSection, setExpandedSection] = useState(null);

  // Audio Podcast states
  const [audioUrl, setAudioUrl] = useState(null);
  const [generatingAudio, setGeneratingAudio] = useState(false);
  const [audioError, setAudioError] = useState(null);

  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);

  // Equations and Code states (Superpowers)
  const [sliderValues, setSliderValues] = useState({});
  const [activeSimulator, setActiveSimulator] = useState(null);
  const [githubRepos, setGithubRepos] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [synthesizedCode, setSynthesizedCode] = useState(null);
  const [compilingCode, setCompilingCode] = useState(false);
  const [codeError, setCodeError] = useState(null);

  // Fetch GitHub repos when paper loads
  useEffect(() => {
    if (!activePaper || !activePaper.filename || activePaper.session_id?.includes(',')) {
      setGithubRepos([]);
      return;
    }
    const fetchGithubRepos = async () => {
      setLoadingRepos(true);
      try {
        const query = encodeURIComponent(activePaper.filename.replace('.pdf', '').substring(0, 80));
        const res = await axios.get(`https://api.github.com/search/repositories?q=${query}`);
        setGithubRepos(res.data.items?.slice(0, 3) || []);
      } catch (err) {
        console.error("GitHub search failed:", err);
        setGithubRepos([]);
      } finally {
        setLoadingRepos(false);
      }
    };
    fetchGithubRepos();
  }, [activePaper]);

  // Sync / set default values when equations load
  useEffect(() => {
    const equations = activePaper?.summary?.equations || [];
    if (equations.length > 0) {
      const initialValues = {};
      equations.forEach(eq => {
        const eqVars = {};
        eq.variables?.forEach(v => {
          eqVars[v.name] = v.default !== undefined ? v.default : 1.0;
        });
        initialValues[eq.title] = eqVars;
      });
      setSliderValues(initialValues);
      setActiveSimulator(equations[0].title);
    } else {
      setSliderValues({});
      setActiveSimulator(null);
    }
    // Reset code synthesis states
    setSynthesizedCode(null);
    setCompilingCode(false);
    setCodeError(null);
  }, [activePaper]);

  const handleSynthesizeCode = async () => {
    if (!activePaper) return;
    setCompilingCode(true);
    setCodeError(null);
    try {
      const res = await axios.post('/synthesize_code', { session_id: activePaper.session_id });
      setSynthesizedCode(res.data.code);
    } catch (err) {
      setCodeError(err.response?.data?.error || "Failed to compile code scaffold.");
    } finally {
      setCompilingCode(false);
    }
  };

  const updateSliderValue = (eqTitle, varName, value) => {
    setSliderValues(prev => ({
      ...prev,
      [eqTitle]: {
        ...prev[eqTitle],
        [varName]: value
      }
    }));
  };

  const evaluateExpression = (expression, variablesObject) => {
    if (!expression || !variablesObject) return "0";
    try {
      let evaluated = expression;
      const keys = Object.keys(variablesObject).sort((a, b) => b.length - a.length);
      keys.forEach(key => {
        evaluated = evaluated.replaceAll(key, String(variablesObject[key]));
      });
      // Simple custom safe mathematical sanitizer to prevent non-math commands execution
      if (/[^0-9\+\-\*\/\(\)\.\s]/.test(evaluated.replace(/[a-zA-Z]/g, ''))) {
        return "Invalid";
      }
      const result = new Function(`return ${evaluated}`)();
      return isNaN(result) ? "0.00" : Number(result).toFixed(3);
    } catch (err) {
      return "Error";
    }
  };


  // Sync state if audio ends or updates
  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  // Reset audio states when paper changes
  useEffect(() => {
    setAudioUrl(null);
    setGeneratingAudio(false);
    setAudioError(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setPlaybackRate(1);
  }, [activePaper]);

  const handleSynthesizeAudio = async () => {
    setGeneratingAudio(true);
    setAudioError(null);
    try {
      const res = await axios.post('/podcast', { session_id: activePaper.session_id });
      setAudioUrl(res.data.url);
    } catch (err) {
      setAudioError(err.response?.data?.error || "Failed to generate audio summary.");
    } finally {
      setGeneratingAudio(false);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch(err => {
        console.error("Audio playback error:", err);
      });
    }
  };

  const handleSeek = (e) => {
    if (!audioRef.current) return;
    const time = Number(e.target.value);
    audioRef.current.currentTime = time;
    setCurrentTime(time);
  };

  const changeSpeed = () => {
    if (!audioRef.current) return;
    let nextRate = 1;
    if (playbackRate === 1) nextRate = 1.25;
    else if (playbackRate === 1.25) nextRate = 1.5;
    else if (playbackRate === 1.5) nextRate = 2;
    else nextRate = 1;
    
    audioRef.current.playbackRate = nextRate;
    setPlaybackRate(nextRate);
  };

  const formatTime = (secs) => {
    if (isNaN(secs)) return "0:00";
    const minutes = Math.floor(secs / 60);
    const seconds = Math.floor(secs % 60);
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
  };


  // Trigger KaTeX parsing when active document or tab selection changes
  useEffect(() => {
    if (window.renderMathInElement) {
      window.renderMathInElement(document.body, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true }
        ],
        throwOnError: false
      });
    }
  }, [activePaper, activeTab, expandedSection]);


  // Copy helper
  const handleCopy = (text, identifier) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(identifier);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  // Export full analysis helper
  const handleExport = () => {
    if (!activePaper) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activePaper, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `Scientia_Analysis_${activePaper.filename.replace('.pdf', '')}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Skeleton loading screen
  if (loading) {
    return (
      <div className="h-full flex flex-col p-6 bg-[#0f0f12] overflow-y-auto space-y-6 animate-pulse select-none">
        <div className="flex justify-between items-center mb-4">
          <div className="h-6 bg-white/10 rounded w-1/3" />
          <div className="h-8 bg-white/10 rounded w-16" />
        </div>
        <div className="h-32 bg-white/5 border border-white/10 rounded-2xl" />
        <div className="space-y-3">
          <div className="h-4 bg-white/10 rounded w-1/4" />
          <div className="h-10 bg-white/5 rounded" />
          <div className="h-10 bg-white/5 rounded" />
          <div className="h-10 bg-white/5 rounded" />
        </div>
      </div>
    );
  }

  // Welcome / empty state
  if (!activePaper) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center bg-[#0f0f12] select-none">
        <div className="w-16 h-16 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-500 mb-4 animate-pulse">
          <Compass size={28} />
        </div>
        <h3 className="text-base font-semibold mb-1 text-slate-300">Scientia.ai Research Lab</h3>
        <p className="text-xs text-slate-500 max-w-xs leading-relaxed px-4">
          Upload or select a technical document to generate summaries, identify research contributions, limitations, and future work.
        </p>
      </div>
    );
  }

  const contributions = activePaper.key_contributions || [];
  const limitations = activePaper.limitations || [];
  const futureResearch = activePaper.future_research || [];
  const gaps = activePaper.research_gaps || [];
  const suggestedTitles = activePaper.suggested_titles || [];
  const importantSentences = activePaper.important_sentences || [];
  const sections = activePaper.summary?.sections || {};

  // Render structured tabs
  return (
    <div className="h-full flex flex-col bg-[#0f0f12]">
      {/* Sticky top tab bar */}
      <div className="px-6 pt-6 pb-2 border-b border-white/5 flex items-center justify-between shrink-0 bg-[#0f0f12]">
        <div className="flex gap-4 overflow-x-auto no-scrollbar">
          <button 
            onClick={() => setActiveTab('summary')}
            className={`pb-3 text-xs font-semibold tracking-wider uppercase border-b-2 transition-all shrink-0 ${activeTab === 'summary' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-white'}`}
          >
            Summary
          </button>
          <button 
            onClick={() => setActiveTab('equations')}
            className={`pb-3 text-xs font-semibold tracking-wider uppercase border-b-2 transition-all shrink-0 ${activeTab === 'equations' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-white'}`}
          >
            Equations Playground
          </button>
          <button 
            onClick={() => setActiveTab('code')}
            className={`pb-3 text-xs font-semibold tracking-wider uppercase border-b-2 transition-all shrink-0 ${activeTab === 'code' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-white'}`}
          >
            Code & Repos
          </button>
          <button 
            onClick={() => setActiveTab('insights')}
            className={`pb-3 text-xs font-semibold tracking-wider uppercase border-b-2 transition-all shrink-0 ${activeTab === 'insights' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-white'}`}
          >
            Research Insights
          </button>
        </div>

        <button 
          onClick={handleExport}
          title="Export analysis report"
          className="p-2 glass-panel border-white/10 text-slate-400 hover:text-white hover:bg-white/5 transition-all text-xs flex items-center gap-1.5 shrink-0"
        >
          <Download size={12} /> Export
        </button>
      </div>

      {/* Dynamic Tab Renderer */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 pb-20">
        
        {activeTab === 'summary' && (
          <div className="space-y-6">
            {/* Abstract */}
            {activePaper.summary?.abstract && (
              <div className="glass-panel p-5 border-white/5 bg-white/[0.01] relative group">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase flex items-center gap-1.5">
                    <FileText size={12} /> Synthesized Abstract
                  </h4>
                  <button 
                    onClick={() => handleCopy(activePaper.summary.abstract, 'abstract')}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/5 text-slate-500 hover:text-white transition-all"
                  >
                    {copiedSection === 'abstract' ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                  </button>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed font-serif italic">
                  "{activePaper.summary.abstract}"
                </p>
              </div>
            )}
            {/* Audio Podcast Overview Card */}
            {!activePaper.session_id?.includes(',') && (
              <div className="glass-panel p-5 bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-transparent border-indigo-500/20 shadow-lg shadow-indigo-500/5 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none" />
                
                <div className="flex items-start gap-4">
                  {/* Equalizer / headphones illustration */}
                  <div className="w-12 h-12 rounded-2xl bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0 select-none">
                    {isPlaying ? (
                      <div className="flex items-end gap-[3px] h-6">
                        <span className="visualizer-bar" />
                        <span className="visualizer-bar" />
                        <span className="visualizer-bar" />
                        <span className="visualizer-bar" />
                        <span className="visualizer-bar" />
                      </div>
                    ) : (
                      <Headphones size={22} className={generatingAudio ? 'animate-bounce' : ''} />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <h4 className="text-xs font-bold text-white font-['Outfit']">NotebookLM-Style Podcast Briefing</h4>
                      <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-[8px] font-extrabold uppercase tracking-wider">
                        AI Podcast
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed mb-4">
                      A synthesized technical overview conversation diving into the core methodology, results, and critical critique of this paper.
                    </p>

                    {/* Audio state switcher */}
                    {generatingAudio ? (
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 text-xs text-indigo-400 font-semibold">
                          <Loader2 size={14} className="animate-spin" />
                          <span>Generating AI Podcast summary (this may take up to a minute)...</span>
                        </div>
                      </div>
                    ) : audioUrl ? (
                      <div className="space-y-3.5">
                        {/* Audio instance */}
                        <audio
                          ref={audioRef}
                          src={audioUrl}
                          onTimeUpdate={handleTimeUpdate}
                          onLoadedMetadata={handleLoadedMetadata}
                          onEnded={() => setIsPlaying(false)}
                          className="hidden"
                        />

                        {/* Player Controls */}
                        <div className="flex items-center gap-4 bg-white/5 border border-white/5 p-3 rounded-xl">
                          {/* Play/Pause Button */}
                          <button
                            onClick={togglePlay}
                            className="w-9 h-9 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/20 transition-all active:scale-95 cursor-pointer"
                          >
                            {isPlaying ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
                          </button>

                          {/* Time progress bar */}
                          <div className="flex-1 flex flex-col gap-1 min-w-0">
                            <input
                              type="range"
                              min={0}
                              max={duration || 0}
                              value={currentTime}
                              onChange={handleSeek}
                              className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500 focus:outline-none"
                            />
                            <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                              <span>{formatTime(currentTime)}</span>
                              <span>{formatTime(duration)}</span>
                            </div>
                          </div>

                          {/* Speed Controller */}
                          <button
                            onClick={changeSpeed}
                            className="px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/5 text-[10px] font-bold font-mono text-slate-300 hover:text-white transition-all hover:bg-white/10 shrink-0 cursor-pointer"
                          >
                            {playbackRate}x
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-3">
                        <button
                          onClick={handleSynthesizeAudio}
                          className="flex items-center justify-center gap-1.5 px-4 py-2 bg-indigo-500 hover:bg-indigo-400 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-lg shadow-indigo-500/10 transition-all self-start"
                        >
                          <Volume2 size={14} /> Generate Audio Briefing
                        </button>
                        {audioError && (
                          <div className="text-[10px] text-red-400 flex items-center gap-1">
                            <AlertTriangle size={10} className="shrink-0" />
                            <span>{audioError}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}


            {/* Interactive Section Summaries */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Document Structure Summary</h4>
              {Object.keys(sections).length === 0 ? (
                <p className="text-xs text-slate-500 italic">No section subdivisions detected in document.</p>
              ) : (
                Object.entries(sections).map(([title, text]) => {
                  const isExpanded = expandedSection === title;
                  return (
                    <div 
                      key={title} 
                      className={`glass-panel border-white/5 transition-all ${isExpanded ? 'bg-white/[0.02] border-indigo-500/20' : 'bg-white/[0.005]'}`}
                    >
                      <div 
                        onClick={() => setExpandedSection(isExpanded ? null : title)}
                        className="p-4 flex items-center justify-between cursor-pointer select-none"
                      >
                        <span className="text-xs font-semibold text-slate-200">{title}</span>
                        <ChevronDown size={14} className={`text-slate-500 transition-transform duration-300 ${isExpanded ? 'rotate-180 text-indigo-400' : ''}`} />
                      </div>
                      
                      {isExpanded && (
                        <div className="px-4 pb-4 border-t border-white/5 pt-3 animate-in fade-in duration-200 relative group">
                          <button 
                            onClick={() => handleCopy(text, title)}
                            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/5 text-slate-500 hover:text-white transition-all"
                          >
                            {copiedSection === title ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                          </button>
                          <p className="text-xs text-slate-400 leading-relaxed">
                            {text}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Technical Tables Section */}
            {activePaper.summary?.tables && activePaper.summary.tables.length > 0 && (
              <div className="space-y-4 pt-4 border-t border-white/5 mt-6">
                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider font-['Outfit']">Indexed Technical Tables</h4>
                <div className="space-y-6">
                  {activePaper.summary.tables.map((table, idx) => (
                    <div key={idx} className="glass-panel p-5 bg-white/[0.005] border-white/5">
                      <span className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase block mb-2">
                        {table.title || `Table ${idx + 1}`}
                      </span>
                      {parseMarkdownTable(table.markdown)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'equations' && (
          <div className="space-y-6">
            {/* Split layout: left list of equations, right interactive sandbox simulator */}
            {!activePaper.summary?.equations || activePaper.summary.equations.length === 0 ? (
              <div className="glass-panel p-8 text-center border-dashed border-2 border-white/5 select-none">
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-slate-500 mx-auto mb-3">
                  <Sliders size={20} />
                </div>
                <h4 className="text-sm font-semibold text-slate-300">No Mathematical Formulations Detected</h4>
                <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed mt-1">
                  Upload a technical paper containing complex equations (e.g. loss functions, layers weights) to activate this live simulator workspace.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Left Side: Equations Cards List */}
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Detected Equations</h4>
                  {activePaper.summary.equations.map((eq) => (
                    <div 
                      key={eq.title} 
                      onClick={() => setActiveSimulator(eq.title)}
                      className={`glass-panel p-5 border-white/5 cursor-pointer transition-all hover:bg-white/[0.01] ${activeSimulator === eq.title ? 'ring-2 ring-indigo-500/50 bg-indigo-500/[0.02]' : 'bg-white/[0.005]'}`}
                    >
                      <span className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase block mb-1">
                        {eq.title}
                      </span>
                      <div className="py-3 px-4 bg-white/5 border border-white/5 rounded-xl my-2 text-center overflow-x-auto text-sm font-serif select-all scrollbar-none">
                        $${eq.latex}$$
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed mt-2 line-clamp-2">
                        {eq.description}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Right Side: Interactive Sandbox Playground */}
                {activeSimulator && (
                  <div className="space-y-4">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Simulator Playground</h4>
                    {(() => {
                      const activeEq = activePaper.summary.equations.find(e => e.title === activeSimulator);
                      if (!activeEq) return null;
                      const currentEqVals = sliderValues[activeSimulator] || {};
                      const result = evaluateExpression(activeEq.js_expression, currentEqVals);

                      return (
                        <div className="glass-panel p-5 bg-gradient-to-br from-indigo-500/5 to-transparent border-indigo-500/10 shadow-lg space-y-6">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <Sparkles size={14} className="text-indigo-400 animate-pulse" />
                              <span className="text-xs font-bold text-white uppercase tracking-wider">{activeEq.title}</span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-relaxed">{activeEq.description}</p>
                          </div>

                          {/* Render Sliders for Variables */}
                          <div className="space-y-4">
                            <h5 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider border-b border-white/5 pb-1">Adjust System Coefficients</h5>
                            {activeEq.variables?.map(v => (
                              <div key={v.name} className="space-y-2">
                                <div className="flex justify-between text-xs">
                                  <span className="text-slate-300 font-medium">{v.label || v.name}</span>
                                  <span className="text-indigo-400 font-mono font-bold">{currentEqVals[v.name] !== undefined ? currentEqVals[v.name] : v.default}</span>
                                </div>
                                <input 
                                  type="range"
                                  min={v.min !== undefined ? v.min : 0}
                                  max={v.max !== undefined ? v.max : 10}
                                  step={v.step !== undefined ? v.step : 0.1}
                                  value={currentEqVals[v.name] !== undefined ? currentEqVals[v.name] : v.default}
                                  onChange={(e) => updateSliderValue(activeSimulator, v.name, Number(e.target.value))}
                                  className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-indigo-500 focus:outline-none"
                                />
                                {v.description && (
                                  <span className="text-[9px] text-slate-500 block italic leading-relaxed">{v.description}</span>
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Sandbox Result Output & Dynamic Visual Dashboard */}
                          <div className="pt-4 border-t border-white/5 space-y-4">
                            <div className="flex items-center justify-between p-4 bg-white/5 border border-white/5 rounded-2xl relative overflow-hidden">
                              <div className="absolute inset-0 bg-indigo-500/5 blur-xl pointer-events-none" />
                              <div className="relative min-w-0">
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Simulated Output Value</span>
                                <span className="text-2xl font-bold font-mono text-white tracking-tight break-all">{result}</span>
                              </div>
                              <div className="shrink-0 flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 select-none">
                                <Sliders size={20} className="animate-pulse" />
                              </div>
                            </div>

                            {/* Animated SVG circular dashboard visual gauge */}
                            {(!isNaN(result) && result !== "Error" && result !== "Invalid") && (
                              <div className="flex flex-col items-center justify-center p-6 bg-white/[0.01] rounded-2xl border border-white/5">
                                <div className="relative w-32 h-32 select-none">
                                  {/* Background SVG Gauge circle */}
                                  <svg className="w-full h-full transform -rotate-90">
                                    <circle
                                      cx="64"
                                      cy="64"
                                      r="50"
                                      stroke="currentColor"
                                      strokeWidth="8"
                                      className="text-white/5"
                                      fill="transparent"
                                    />
                                    <circle
                                      cx="64"
                                      cy="64"
                                      r="50"
                                      stroke="currentColor"
                                      strokeWidth="8"
                                      className="text-indigo-500 transition-all duration-300 ease-out"
                                      strokeDasharray={314}
                                      strokeDashoffset={314 - (314 * Math.min(Math.max(Number(result), 0), 10)) / 10}
                                      strokeLinecap="round"
                                      fill="transparent"
                                    />
                                  </svg>
                                  {/* Center Gauge values */}
                                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-sm font-extrabold text-white font-mono">{Math.min(Math.max(Math.round(Number(result) * 10), 0), 100)}%</span>
                                    <span className="text-[8px] text-slate-500 uppercase tracking-wider font-semibold">Load Level</span>
                                  </div>
                                </div>
                                <span className="text-[10px] text-slate-500 mt-3 text-center leading-relaxed">
                                  Interactive mathematical curve visualized under $${activeEq.latex}$$.
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}

              </div>
            )}
          </div>
        )}

        {activeTab === 'code' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Left Column (Span 1): GitHub Repository Matcher */}
              <div className="lg:col-span-1 space-y-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Star size={12} className="text-amber-400" /> Starred Implementations
                </h4>
                
                {loadingRepos ? (
                  <div className="space-y-3">
                    <div className="h-28 bg-white/5 border border-white/10 rounded-xl animate-pulse" />
                    <div className="h-28 bg-white/5 border border-white/10 rounded-xl animate-pulse" />
                  </div>
                ) : githubRepos.length === 0 ? (
                  <div className="glass-panel p-5 text-center border-white/5 bg-white/[0.005]">
                    <p className="text-xs text-slate-500 italic">No community GitHub repositories matching this title were located.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {githubRepos.map(repo => (
                      <div key={repo.id} className="glass-panel p-4 bg-white/[0.005] border-white/5 transition-all hover:bg-white/[0.015] flex flex-col justify-between h-28 relative group">
                        <div>
                          <div className="flex justify-between items-start gap-2">
                            <span className="text-xs font-bold text-slate-200 line-clamp-1 break-all pr-1">{repo.name}</span>
                            <a 
                              href={repo.html_url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="text-slate-500 hover:text-indigo-400 transition-colors shrink-0 cursor-pointer"
                            >
                              <ExternalLink size={12} />
                            </a>
                          </div>
                          <p className="text-[10px] text-slate-500 line-clamp-2 leading-relaxed mt-1">{repo.description || "No description provided."}</p>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-white/5">
                          <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 text-[9px] font-bold">
                            {repo.language || 'Code'}
                          </span>
                          <span className="flex items-center gap-1 text-[10px] font-bold text-amber-400 font-mono">
                            <Star size={10} className="fill-amber-400/20" /> {repo.stargazers_count.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Column (Span 2): Automated PyTorch Scaffold Compiler */}
              <div className="lg:col-span-2 space-y-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Code size={12} className="text-indigo-400" /> PyTorch Module Scaffold
                </h4>

                {compilingCode ? (
                  <div className="glass-panel p-6 bg-white/[0.005] border-white/5 flex flex-col items-center justify-center py-20 text-center select-none space-y-4">
                    <Loader2 size={24} className="text-indigo-400 animate-spin" />
                    <div>
                      <h4 className="text-xs font-semibold text-slate-300">Synthesizing PyTorch Neural Layers...</h4>
                      <p className="text-[10px] text-slate-500 max-w-xs leading-relaxed mt-1">
                        Gemini is analyzing paper layers, formulas, and parameters to compile custom modules, forward passes, and training boilerplates.
                      </p>
                    </div>
                  </div>
                ) : synthesizedCode ? (
                  <div className="glass-panel border-white/5 bg-[#0a0a0c] relative group overflow-hidden rounded-2xl flex flex-col h-[500px]">
                    {/* Floating Copy Trigger */}
                    <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
                      <span className="text-[10px] font-bold font-mono text-slate-400 uppercase flex items-center gap-1">
                        <Terminal size={12} /> generated_model.py
                      </span>
                      <button 
                        onClick={() => handleCopy(synthesizedCode, 'scaffold')}
                        className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-all cursor-pointer border border-white/5"
                      >
                        {copiedSection === 'scaffold' ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                        <span>{copiedSection === 'scaffold' ? 'Copied' : 'Copy Code'}</span>
                      </button>
                    </div>
                    
                    {/* Scrollable Editor code */}
                    <pre className="flex-1 overflow-auto p-4 text-xs font-mono text-emerald-400 leading-relaxed bg-[#08080a] scrollbar-none select-all select-text whitespace-pre">
                      {synthesizedCode}
                    </pre>
                  </div>
                ) : (
                  <div className="glass-panel p-8 text-center border-dashed border-2 border-white/5 select-none py-16">
                    <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-slate-500 mx-auto mb-3">
                      <Code size={20} />
                    </div>
                    <h4 className="text-sm font-semibold text-slate-300">Autopilot Code Scaffold Builder</h4>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed mt-1 mb-5">
                      Synthesize robust, ready-to-run PyTorch module layers and training boilerplate matching the exact methodology of this paper.
                    </p>
                    <button
                      onClick={handleSynthesizeCode}
                      className="flex items-center justify-center gap-1.5 px-4 py-2 bg-indigo-500 hover:bg-indigo-400 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-lg shadow-indigo-500/10 transition-all mx-auto"
                    >
                      <Code size={14} /> Synthesize PyTorch Scaffold
                    </button>
                    {codeError && (
                      <p className="text-[10px] text-red-400 mt-3 italic">{codeError}</p>
                    )}
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="space-y-6">
            {/* Grid of Key Contributions & Limitations */}
            <div className="grid grid-cols-1 gap-6">
              
              {/* Contributions */}
              {contributions.length > 0 && (
                <div className="glass-panel p-5 border-white/5 bg-indigo-500/[0.01]">
                  <h4 className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase flex items-center gap-1.5 mb-3">
                    <Award size={12} /> Key Academic Contributions
                  </h4>
                  <ul className="space-y-2.5">
                    {contributions.map((c, i) => (
                      <li key={i} className="flex gap-2 text-xs text-slate-300 leading-relaxed items-start">
                        <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-1.5 shrink-0" />
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Limitations */}
              {limitations.length > 0 && (
                <div className="glass-panel p-5 border-white/5 bg-red-500/[0.01]">
                  <h4 className="text-[10px] text-red-400 font-semibold tracking-wider uppercase flex items-center gap-1.5 mb-3">
                    <AlertTriangle size={12} /> Scope & Limitations
                  </h4>
                  <ul className="space-y-2.5">
                    {limitations.map((l, i) => (
                      <li key={i} className="flex gap-2 text-xs text-slate-300 leading-relaxed items-start">
                        <span className="w-1.5 h-1.5 bg-red-500 rounded-full mt-1.5 shrink-0" />
                        <span>{l}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Gaps */}
              {gaps.length > 0 && (
                <div className="glass-panel p-5 border-white/5 bg-amber-500/[0.01]">
                  <h4 className="text-[10px] text-amber-400 font-semibold tracking-wider uppercase flex items-center gap-1.5 mb-3">
                    <Compass size={12} /> Research Gap Detection
                  </h4>
                  <ul className="space-y-2.5">
                    {gaps.map((g, i) => (
                      <li key={i} className="flex gap-2 text-xs text-slate-300 leading-relaxed items-start">
                        <span className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 shrink-0" />
                        <span>{g}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Future Research & Suggested Titles */}
              {(futureResearch.length > 0 || suggestedTitles.length > 0) && (
                <div className="glass-panel p-5 border-white/5 bg-emerald-500/[0.01] space-y-4">
                  {futureResearch.length > 0 && (
                    <div>
                      <h4 className="text-[10px] text-emerald-400 font-semibold tracking-wider uppercase flex items-center gap-1.5 mb-3">
                        <Lightbulb size={12} /> Future Directions
                      </h4>
                      <ul className="space-y-2.5">
                        {futureResearch.map((fr, i) => (
                          <li key={i} className="flex gap-2 text-xs text-slate-300 leading-relaxed items-start">
                            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mt-1.5 shrink-0" />
                            <span>{fr}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {suggestedTitles.length > 0 && (
                    <div className="pt-4 border-t border-white/5">
                      <h4 className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase flex items-center gap-1.5 mb-3">
                        Suggested Follow-Up Titles
                      </h4>
                      <div className="flex flex-col gap-2">
                        {suggestedTitles.map((st, i) => (
                          <div key={i} className="p-2 bg-white/[0.02] border border-white/5 rounded text-xs text-slate-200 italic">
                            {st}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Highlight Sentences */}
              {importantSentences.length > 0 && (
                <div className="glass-panel p-5 border-white/5 md:col-span-2 relative group">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase flex items-center gap-1.5">
                      <Info size={12} /> Key Declarative Quotes
                    </h4>
                  </div>
                  <ul className="space-y-3">
                    {importantSentences.map((s, i) => (
                      <li key={i} className="border-l-2 border-indigo-500/30 pl-3 py-0.5 text-xs text-slate-400 leading-relaxed italic">
                        "{s}"
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default ResearchPanel;

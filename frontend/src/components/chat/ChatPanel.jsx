import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Sparkles, Paperclip, UploadCloud, HelpCircle, FileText } from 'lucide-react';

const ChatPanel = ({ activePaper, onUpload, loading }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [asking, setAsking] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const bottomRef = useRef(null);
  const fileInputRef = useRef(null);

  // Advanced Citation Drawer States
  const [activeCitation, setActiveCitation] = useState(null);
  const [loadingCitation, setLoadingCitation] = useState(false);

  // Trigger OpenAlex API citation metadata lookup
  const handleCitationClick = async (refNum) => {
    if (!activePaper) return;
    setLoadingCitation(true);
    setActiveCitation({ ref_num: refNum, loading: true });
    try {
      const res = await axios.get(`/citation?session_id=${activePaper.session_id}&ref_num=${refNum}`);
      setActiveCitation(res.data);
    } catch (err) {
      console.error(err);
      const errMsg = err.response?.data?.error || "Failed to load citation details.";
      setActiveCitation({
        ref_num: refNum,
        raw_text: `Reference [${refNum}]`,
        title: `Reference [${refNum}]`,
        abstract: errMsg,
        scholarly_found: false
      });
    } finally {
      setLoadingCitation(false);
    }
  };

  // Scans message content for citation brackets [1] and replaces them with interactive badges
  const renderMessageContent = (text) => {
    if (!text) return "";
    const regex = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const matchIndex = match.index;
      // Plain text preceding citation bracket
      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }
      
      const refNum = match[1];
      parts.push(
        <button
          key={matchIndex}
          onClick={() => handleCitationClick(refNum)}
          className="px-1.5 py-0.5 mx-0.5 text-[10px] font-bold text-indigo-400 hover:text-white bg-indigo-500/10 hover:bg-indigo-600 rounded cursor-pointer transition-all tracking-wide select-none outline-none align-middle"
          title={`View Scholarly Reference [${refNum}]`}
        >
          [{refNum}]
        </button>
      );
      
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return (
      <span className="whitespace-pre-wrap leading-relaxed">
        {parts.length > 0 ? parts : text}
      </span>
    );
  };


  // Status updates displayed during document processing
  const [processingStatus, setProcessingStatus] = useState("Initializing PDF processor...");

  useEffect(() => {
    if (loading) {
      const statuses = [
        "Opening PDF and extracting raw text...",
        "Cleaning document layout and formatting...",
        "Splitting text into semantic chunk tokens...",
        "Building local FAISS search indexes...",
        "Synthesizing key insights and summaries...",
        "Analyzing research limitations and future work...",
        "Finalizing Scientia.ai workspace..."
      ];
      let i = 0;
      const interval = setInterval(() => {
        if (i < statuses.length) {
          setProcessingStatus(statuses[i]);
          i++;
        }
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [loading]);

  // Load chat history when active document changes
  useEffect(() => {
    if (activePaper) {
      const loadHistory = async () => {
        try {
          const res = await axios.get(`/history?session_id=${activePaper.session_id}`);
          setMessages(res.data.history || []);
        } catch (err) {
          console.error("Failed to load chat history:", err);
          setMessages([
            { role: 'assistant', content: `Hello! I've loaded "${activePaper.filename}". Ask me anything about the methodology, results, or implications.` }
          ]);
        }
      };
      loadHistory();
    } else {
      setMessages([]);
    }
  }, [activePaper]);

  // Scroll to bottom of chat and trigger KaTeX rendering
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
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
  }, [messages, asking]);


  const handleSend = async () => {
    if (!input.trim() || asking || !activePaper) return;
    const question = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setInput('');
    setAsking(true);

    try {
      const res = await axios.post('/ask', {
        question: question,
        session_id: activePaper.session_id
      });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.answer,
        sections: res.data.relevant_sections || []
      }]);
    } catch (err) {
      console.error(err);
      const errMsg = err.response?.data?.error || err.message || "Failed to generate answer";
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${errMsg}. Please check your API key config in Settings.`
      }]);
    } finally {
      setAsking(false);
    }
  };

  // Drag and drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        onUpload(file);
      } else {
        alert("Please upload PDF documents only.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  // Predefined prompts for quick user exploration
  const quickPrompts = [
    "What is the main methodology used?",
    "Summarize the experimental findings",
    "Identify key limitations of this study",
  ];

  // Render Loading Phase
  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 bg-[#0a0a0c]">
        <div className="relative w-24 h-24 mb-8">
          {/* Animated pulsing orbit rings */}
          <div className="absolute inset-0 rounded-full border-4 border-indigo-600/30 animate-ping duration-1000" />
          <div className="absolute inset-2 rounded-full border-4 border-indigo-500/20 animate-pulse duration-700" />
          <div className="absolute inset-4 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-xl shadow-indigo-600/30">
            <Sparkles size={28} className="animate-spin duration-[4000ms]" />
          </div>
        </div>
        <h3 className="text-xl font-bold font-['Outfit'] tracking-tight mb-2 text-white">Synthesizing Document</h3>
        <p className="text-xs text-indigo-400 font-semibold tracking-wider uppercase mb-6 animate-pulse">Advanced AI Mode</p>
        
        <div className="w-full max-w-sm bg-white/5 border border-white/10 rounded-2xl p-4 backdrop-blur-xl">
          <p className="text-sm text-slate-300 text-center leading-relaxed font-medium transition-all duration-500">
            {processingStatus}
          </p>
          <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden mt-4">
            <div className="h-full bg-indigo-500 rounded-full animate-[loading-bar_10s_infinite]" style={{ width: '60%' }} />
          </div>
        </div>
      </div>
    );
  }

  // Render Upload Welcome Screen if no paper is active
  if (!activePaper) {
    return (
      <div 
        onDragEnter={handleDrag} 
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`h-full flex flex-col items-center justify-center p-8 bg-[#0a0a0c] select-none transition-all duration-300 ${dragActive ? 'bg-indigo-600/5' : ''}`}
      >
        <div className="max-w-xl text-center flex flex-col items-center gap-6">
          <div className={`w-20 h-20 rounded-2xl bg-indigo-600/10 border flex items-center justify-center text-indigo-400 shadow-2xl transition-all duration-300 ${dragActive ? 'scale-110 border-indigo-500 bg-indigo-500/20 text-indigo-300' : 'border-white/5'}`}>
            <UploadCloud size={36} className={`${dragActive ? 'animate-bounce' : ''}`} />
          </div>
          
          <div>
            <h2 className="text-3xl font-bold font-['Outfit'] tracking-tight mb-3 text-white">Analyze Your Technical Research</h2>
            <p className="text-slate-400 text-sm leading-relaxed px-4">
              Drag and drop any research PDF here. Scientia.ai will construct vector indices, extract core methodologies, limitations, and key contributions in real-time.
            </p>
          </div>

          <div className="flex gap-4">
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept=".pdf" 
              className="hidden" 
            />
            <button 
              onClick={triggerFileInput} 
              className="btn-primary flex items-center gap-2"
            >
              Browse PDF Paper
            </button>
          </div>

          {/* Tips card */}
          <div className="mt-8 p-4 glass-panel border-white/5 max-w-sm flex items-start gap-3 text-left">
            <HelpCircle size={18} className="text-indigo-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-400">
              <span className="font-semibold text-slate-200 block mb-1">Advanced RAG Pipelines:</span>
              Leverages high-speed FAISS semantic search and Google Gemini for deep paper reasoning, parsing context up to hundreds of pages effortlessly.
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render Real Chat Interface
  return (
    <div className="h-full flex flex-col bg-[#0a0a0c] relative">
      {/* Sticky Top Header */}
      <div className="px-6 py-4 border-b border-white/5 bg-[#0a0a0c]/80 backdrop-blur-md z-10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-indigo-400" />
          <span className="text-xs font-semibold text-slate-300 max-w-md truncate" title={activePaper.filename}>
            {activePaper.filename}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setMessages([{ role: 'assistant', content: `Hello! I've loaded "${activePaper.filename}". Ask me anything about the methodology, results, or implications.` }])}
            className="text-[10px] text-slate-500 hover:text-indigo-400 hover:bg-white/5 px-2 py-1 rounded transition-colors"
          >
            Clear Chat
          </button>
        </div>
      </div>

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 pb-32">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
              Successfully indexed and summarized the research document. Ask specific questions about findings, datasets, formulas, or related work.
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai animate-in fade-in duration-300'}>
            <div className="leading-relaxed text-sm">
              {renderMessageContent(m.content)}
            </div>
            
            {/* Cited References drawer */}
            {m.role === 'assistant' && m.sections && m.sections.length > 0 && (
              <details className="mt-4 pt-3 border-t border-white/5 group">
                <summary className="text-[10px] font-semibold text-slate-500 hover:text-indigo-400 cursor-pointer list-none flex items-center gap-1.5 transition-colors select-none">
                  <Sparkles size={10} className="text-indigo-500 animate-pulse" />
                  EXPLORE CITED DOCUMENT CHUNKS
                </summary>
                <div className="mt-3 space-y-2 max-h-48 overflow-y-auto pr-2">
                  {m.sections.map((section, idx) => (
                    <div key={idx} className="p-3 bg-white/[0.02] border border-white/5 rounded-lg text-[11px] text-slate-400 leading-relaxed font-mono">
                      {section}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}

        {asking && (
          <div className="chat-bubble-ai flex items-center gap-3 py-4 max-w-xs animate-pulse">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:0.2s]" />
              <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:0.4s]" />
            </div>
            <span className="text-xs text-slate-500 font-semibold tracking-wide uppercase">AI Thinking...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input container */}
      <div className="absolute bottom-6 left-0 right-0 px-6 z-10 bg-gradient-to-t from-[#0a0a0c] via-[#0a0a0c] to-transparent pt-4">
        {/* Quick Suggestion Prompts */}
        {messages.length < 3 && !asking && (
          <div className="mb-4 flex flex-wrap gap-2 justify-center max-w-xl mx-auto">
            {quickPrompts.map((p, idx) => (
              <button 
                key={idx}
                onClick={() => setInput(p)}
                className="text-[10px] font-medium text-slate-400 hover:text-indigo-400 bg-white/5 border border-white/5 hover:border-indigo-500/20 px-3 py-1.5 rounded-full transition-all duration-200"
              >
                {p}
              </button>
            ))}
          </div>
        )}

        <div className="max-w-2xl mx-auto glass-panel p-2 flex items-center gap-2 pr-4 shadow-2xl shadow-indigo-500/10 border-white/10">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept=".pdf" 
            className="hidden" 
          />
          <button 
            onClick={triggerFileInput}
            title="Upload/change paper" 
            className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <Paperclip size={18} />
          </button>
          
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask anything about this document..."
            disabled={asking}
            className="flex-1 bg-transparent border-none outline-none py-2 text-sm placeholder:text-slate-500 text-white disabled:opacity-50"
          />
          <button 
            onClick={handleSend} 
            disabled={asking || !input.trim()}
            className="bg-indigo-600 p-2 rounded-lg hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-white shrink-0"
          >
            <Send size={16} />
          </button>
        </div>
      </div>

      {/* Advanced Citation Scholarly Tooltip Drawer */}
      {activeCitation && (
        <div className="absolute right-0 top-0 bottom-0 w-80 bg-[#0f0f12]/95 border-l border-white/10 backdrop-blur-2xl p-6 z-30 shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-300 select-none">
          <div className="overflow-y-auto space-y-4 h-full pr-1">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h4 className="text-xs font-semibold text-indigo-400 tracking-wider uppercase">Citation Details [{activeCitation.ref_num}]</h4>
              <button 
                onClick={() => setActiveCitation(null)}
                className="text-xs font-bold text-slate-500 hover:text-white uppercase transition-colors"
              >
                Close
              </button>
            </div>
            
            {activeCitation.loading ? (
              <div className="space-y-4 animate-pulse pt-4">
                <div className="h-4 bg-white/10 rounded w-3/4" />
                <div className="h-3 bg-white/5 rounded w-1/2" />
                <div className="space-y-2">
                  <div className="h-3 bg-white/5 rounded w-full" />
                  <div className="h-3 bg-white/5 rounded w-5/6" />
                  <div className="h-3 bg-white/5 rounded w-4/5" />
                </div>
              </div>
            ) : (
              <div className="space-y-4 pt-2">
                <div>
                  <span className="text-[9px] text-slate-500 font-semibold block uppercase">Reference Citation</span>
                  <p className="text-xs text-slate-300 leading-relaxed mt-1 italic">
                    "{activeCitation.raw_text}"
                  </p>
                </div>

                {activeCitation.scholarly_found ? (
                  <>
                    <div className="pt-2 border-t border-white/5">
                      <span className="text-[9px] text-indigo-400 font-semibold block uppercase">OpenAlex Scholarly Match</span>
                      <p className="text-sm font-bold text-white leading-snug mt-1.5">{activeCitation.title}</p>
                    </div>

                    {activeCitation.authors && (
                      <div>
                        <span className="text-[9px] text-slate-500 font-semibold block uppercase">Authors</span>
                        <p className="text-xs text-slate-300 mt-0.5">{activeCitation.authors}</p>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      {activeCitation.year && (
                        <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-lg">
                          <span className="text-[8px] text-slate-500 font-semibold block uppercase">Year</span>
                          <span className="text-xs font-bold text-slate-200 font-['Outfit']">{activeCitation.year}</span>
                        </div>
                      )}
                      {activeCitation.citations !== undefined && (
                        <div className="p-2.5 bg-white/[0.01] border border-white/5 rounded-lg">
                          <span className="text-[8px] text-slate-500 font-semibold block uppercase">API Citations</span>
                          <span className="text-xs font-bold text-slate-200 font-['Outfit']">{activeCitation.citations} reads</span>
                        </div>
                      )}
                    </div>

                    <div className="pt-1">
                      <span className="text-[9px] text-slate-500 font-semibold block uppercase mb-1.5">Abstract Synopsis</span>
                      <div className="p-3 bg-white/[0.01] border border-white/5 rounded-xl text-[11px] text-slate-400 leading-relaxed font-serif italic max-h-52 overflow-y-auto pr-1">
                        "{activeCitation.abstract}"
                      </div>
                    </div>

                    {activeCitation.url && (
                      <div className="pt-2">
                        <a 
                          href={activeCitation.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="w-full py-2 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 text-center rounded-xl text-xs font-bold block border border-indigo-500/20 hover:border-indigo-500/30 transition-all uppercase tracking-wider"
                        >
                          Open Scholarly DOI
                        </a>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="pt-4 border-t border-white/5 p-4 bg-white/[0.01] border border-white/5 rounded-xl flex items-center justify-center text-center">
                    <p className="text-[10px] text-slate-500 leading-relaxed">
                      No matching paper registered in the open-access API registry for this specific index. Check spelling or parent bibliography.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPanel;

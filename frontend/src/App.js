import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Sparkles } from 'lucide-react';

// Premium Layout Components
import Sidebar from './components/layout/Sidebar.jsx';
import ChatPanel from './components/chat/ChatPanel.jsx';
import ResearchPanel from './components/research/ResearchPanel.jsx';

// New Advanced Panels
import DocsPanel from './components/research/DocsPanel.jsx';
import SettingsPanel from './components/research/SettingsPanel.jsx';
import DashboardPanel from './components/research/DashboardPanel.jsx';
import SynthesisPanel from './components/research/SynthesisPanel.jsx';

const App = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const [papers, setPapers] = useState([]);
  const [activePaper, setActivePaper] = useState(null);
  const [loadingPaper, setLoadingPaper] = useState(false);
  const [error, setError] = useState(null);
  const [apiSettings, setApiSettings] = useState({ has_key: false, masked_key: '' });

  // Comparative Synthesis States
  const [synthesisData, setSynthesisData] = useState(null);
  const [synthesisLoading, setSynthesisLoading] = useState(false);

  // 1. Fetch all documents from the backend
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await axios.get('/documents');
      setPapers(res.data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, []);

  // 2. Fetch API Key configurations from backend
  const fetchSettings = useCallback(async () => {
    try {
      const res = await axios.get('/settings');
      setApiSettings(res.data || { has_key: false, masked_key: '' });
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments();
    fetchSettings();
  }, [fetchDocuments, fetchSettings]);

  // 3. Select/Load an active document
  const handleSelectPaper = async (docId) => {
    setLoadingPaper(true);
    setError(null);
    try {
      const res = await axios.get(`/documents/${docId}`);
      setActivePaper(res.data);
      // Auto redirect to Research Lab split pane
      setActiveTab('research');
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Failed to select document';
      setError(msg);
    } finally {
      setLoadingPaper(false);
    }
  };

  // 4. Delete document
  const handleDeletePaper = async (docId) => {
    if (!window.confirm("Are you sure you want to delete this document and its chat history?")) return;
    try {
      await axios.delete(`/documents/${docId}`);
      if (activePaper?.session_id === docId || activePaper?.session_id?.split(',').includes(docId)) {
        setActivePaper(null);
      }
      fetchDocuments();
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('Failed to delete document');
    }
  };

  // 5. Upload document
  const handleUploadPaper = async (file) => {
    setLoadingPaper(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setActivePaper(res.data);
      fetchDocuments(); // Reload documents list
      setActiveTab('research'); // Slide into Research insights
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Upload and processing failed';
      setError(msg);
    } finally {
      setLoadingPaper(false);
    }
  };

  // 6. Synthesize comparative matrix
  const handleSynthesize = async (selectedIds) => {
    setLoadingPaper(true);
    setSynthesisLoading(true);
    setActiveTab('synthesis');
    setError(null);
    try {
      const res = await axios.post('/synthesis', { session_ids: selectedIds });
      setSynthesisData(res.data);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Comparative synthesis failed';
      setError(msg);
      setActiveTab('docs'); // Fallback to library
    } finally {
      setLoadingPaper(false);
      setSynthesisLoading(false);
    }
  };

  // 7. Activate Multi-Document vector QA workspace
  const handleActivateMultiDocWorkspace = () => {
    if (!synthesisData) return;
    const combinedIds = Object.keys(synthesisData.headers).join(',');
    const combinedFilename = `${Object.values(synthesisData.headers).length} Selected Papers`;
    setActivePaper({
      session_id: combinedIds,
      filename: combinedFilename,
      summary: {
        abstract: `Multi-Document comparative analysis workspace active across: ${Object.values(synthesisData.headers).join(', ')}. Ask cross-document queries below.`,
        sections: {}
      }
    });
    setActiveTab('chat');
  };

  // Eject active paper
  const handleEjectPaper = () => {
    setActivePaper(null);
  };

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'docs':
        return (
          <DocsPanel 
            papers={papers} 
            activePaper={activePaper}
            onSelect={handleSelectPaper} 
            onDelete={handleDeletePaper}
            onUpload={handleUploadPaper}
            loading={loadingPaper}
            onSynthesize={handleSynthesize}
          />
        );
      case 'settings':
        return (
          <SettingsPanel 
            settings={apiSettings} 
            onSave={fetchSettings}
          />
        );
      case 'dashboard':
        return (
          <DashboardPanel 
            papersCount={papers.length}
            activePaper={activePaper}
            apiSettings={apiSettings}
          />
        );
      case 'synthesis':
        if (synthesisLoading) {
          return (
            <div className="h-full flex flex-col items-center justify-center p-8 bg-[#0a0a0c] select-none">
              <div className="relative w-20 h-20 mb-6">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-600/30 animate-ping duration-1000" />
                <div className="absolute inset-2 rounded-full border-4 border-indigo-500/20 animate-pulse" />
                <div className="absolute inset-4 rounded-full bg-indigo-600 flex items-center justify-center text-white shadow-xl shadow-indigo-600/30">
                  <Sparkles size={24} className="animate-spin duration-[4000ms]" />
                </div>
              </div>
              <h3 className="text-lg font-bold font-['Outfit'] tracking-tight mb-2">Compiling Comparative Matrix</h3>
              <p className="text-xs text-slate-500 max-w-sm text-center leading-relaxed">
                Gemini is synthesizing paper methodologies, datasets, parameters, and results to generate a comprehensive cross-paper comparative report.
              </p>
            </div>
          );
        }
        return (
          <SynthesisPanel 
            synthesisData={synthesisData}
            onClose={() => setActiveTab('docs')}
            onActivateWorkspace={handleActivateMultiDocWorkspace}
            isActiveWorkspace={activePaper?.session_id === Object.keys(synthesisData?.headers || {}).join(',')}
          />
        );
      case 'chat':
      case 'research':
      default:
        return (
          <main className="flex-1 flex overflow-hidden relative">
            {/* Left chat panel (Full-screen in chat mode, half-screen in split research mode) */}
            <div className={`flex-1 h-full transition-all duration-500 ease-in-out ${activeTab === 'chat' ? 'w-full' : 'w-1/2'}`}>
              <ChatPanel 
                activePaper={activePaper}
                onUpload={handleUploadPaper}
                loading={loadingPaper}
              />
            </div>
            
            {/* Right side insights panel in Research Lab split mode */}
            {activeTab === 'research' && (
              <div className="w-1/2 border-l border-white/10 h-full overflow-hidden animate-in slide-in-from-right duration-500 bg-[#0f0f12]">
                <ResearchPanel 
                  activePaper={activePaper} 
                  loading={loadingPaper}
                />
              </div>
            )}
          </main>
        );
    }
  };

  return (
    <div className="flex h-screen bg-[#0a0a0c] text-[#f8fafc] font-['Inter'] overflow-hidden">
      {/* Dynamic Sidebar */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        activePaper={activePaper}
        onEjectPaper={handleEjectPaper}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Error notification header */}
        {error && (
          <div className="absolute top-4 right-4 z-50 max-w-md bg-red-500/10 border border-red-500/20 text-red-200 px-4 py-3 rounded-xl flex items-center justify-between shadow-2xl backdrop-blur-xl animate-in fade-in duration-300">
            <span className="text-sm font-medium mr-4">{error}</span>
            <button 
              onClick={() => setError(null)} 
              className="text-xs font-bold text-red-400 hover:text-red-300 uppercase tracking-wider"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Dynamic Panel Renderer */}
        {renderTabContent()}
      </div>
    </div>
  );
};

export default App;

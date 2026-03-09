import React, { useState, useCallback } from 'react';
import UploadPaper from './components/UploadPaper';
import SummaryPanel from './components/SummaryPanel';
import ChatInterface from './components/ChatInterface';
import InsightsPanel from './components/InsightsPanel';

function App() {
  const [paperData, setPaperData] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onUploadSuccess = useCallback((data) => {
    setPaperData(data);
    setSessionId(data.session_id || null);
    setError(null);
  }, []);

  const onUploadError = useCallback((err) => {
    setError(err?.message || 'Upload failed');
    setPaperData(null);
    setSessionId(null);
  }, []);

  const onUploadStart = useCallback(() => {
    setLoading(true);
    setError(null);
  }, []);

  const onUploadEnd = useCallback(() => {
    setLoading(false);
  }, []);

  return (
    <div className="min-h-screen bg-paper-50 text-paper-900 flex flex-col">
      {/* Header */}
      <header className="border-b border-paper-200 bg-white/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="font-display text-2xl md:text-3xl text-paper-900">
            AI Research Assistant
          </h1>
          <span className="text-sm text-paper-500 hidden sm:inline">
            Upload • Summarize • Chat
          </span>
        </div>
      </header>

      {error && (
        <div className="max-w-7xl mx-auto w-full px-4 py-2">
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-2 text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Main layout: left (upload + summary), right (chat), bottom (insights) */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-4 flex flex-col lg:flex-row gap-4">
        {/* Left: Upload + Summary */}
        <section className="lg:w-[380px] flex-shrink-0 flex flex-col gap-4">
          <UploadPaper
            onSuccess={onUploadSuccess}
            onError={onUploadError}
            onStart={onUploadStart}
            onEnd={onUploadEnd}
            disabled={loading}
          />
          <SummaryPanel
            summary={paperData?.summary}
            filename={paperData?.filename}
            loading={loading}
          />
        </section>

        {/* Right: Chat */}
        <section className="flex-1 min-w-0 flex flex-col">
          <ChatInterface
            sessionId={sessionId}
            hasPaper={!!paperData}
            loading={loading}
          />
        </section>
      </main>

      {/* Bottom: Insights */}
      <section className="border-t border-paper-200 bg-paper-100/50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <InsightsPanel data={paperData} loading={loading} />
        </div>
      </section>
    </div>
  );
}

export default App;

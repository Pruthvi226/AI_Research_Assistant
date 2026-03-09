import React, { useState, useRef, useEffect } from 'react';
import { askQuestion } from '../api';

function ChatInterface({ sessionId, hasPaper, loading }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || asking || !hasPaper) return;

    setError(null);
    setMessages((prev) => [...prev, { role: 'user', text: q, sections: null }]);
    setInput('');
    setAsking(true);

    try {
      const res = await askQuestion(q, sessionId || '');
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'user', text: q, sections: null },
        {
          role: 'assistant',
          text: res.answer,
          sections: res.relevant_sections || [],
        },
      ]);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Failed to get answer';
      setError(msg);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'user', text: q, sections: null },
        { role: 'assistant', text: `Error: ${msg}`, sections: [] },
      ]);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-paper-200 shadow-sm flex flex-col h-[480px]">
      <h2 className="font-display text-lg text-paper-900 p-4 border-b border-paper-200">
        Chat with Paper
      </h2>

      {!hasPaper && !loading && (
        <div className="flex-1 flex items-center justify-center p-6 text-center text-paper-500 text-sm">
          Upload a paper above to ask questions and get answers from the document.
        </div>
      )}

      {hasPaper && (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <p className="text-sm text-paper-500">
                Ask anything about the paper. Answers are generated from the most relevant sections.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    m.role === 'user'
                      ? 'bg-accent text-white'
                      : 'bg-paper-100 text-paper-800'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {m.role === 'assistant' && m.sections && m.sections.length > 0 && (
                    <details className="mt-2 pt-2 border-t border-paper-200">
                      <summary className="text-xs font-medium text-paper-600 cursor-pointer">
                        Relevant sections
                      </summary>
                      <ul className="mt-1 space-y-1 text-xs text-paper-600">
                        {m.sections.slice(0, 3).map((s, j) => (
                          <li key={j} className="line-clamp-2">
                            {s.slice(0, 200)}{s.length > 200 ? '…' : ''}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </div>
            ))}
            {asking && (
              <div className="flex justify-start">
                <div className="bg-paper-100 rounded-lg px-3 py-2 text-sm text-paper-600">
                  Thinking…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="p-4 border-t border-paper-200">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question about the paper..."
                disabled={asking}
                className="flex-1 rounded-lg border border-paper-200 px-3 py-2 text-sm focus:ring-2 focus:ring-accent focus:border-accent outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={asking || !input.trim()}
                className="px-4 py-2 rounded-lg bg-accent text-white font-medium text-sm hover:bg-accent-light disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </div>
            {error && (
              <p className="mt-2 text-xs text-red-600">{error}</p>
            )}
          </form>
        </>
      )}
    </div>
  );
}

export default ChatInterface;

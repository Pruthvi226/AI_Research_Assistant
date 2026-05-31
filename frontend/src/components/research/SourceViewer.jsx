import React from 'react';
import { FileText, ChevronRight } from 'lucide-react';

const SourceViewer = ({ sources }) => {
  return (
    <div className="p-4 space-y-4">
      <h3 className="text-sm font-semibold text-slate-400 mb-4 px-2">Cited Sources</h3>
      {sources.map((source, i) => (
        <div key={i} className="glass-panel p-3 hover:bg-white/5 transition-all cursor-pointer group">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/10 flex items-center justify-center text-indigo-400">
              <FileText size={16} />
            </div>
            <div className="flex-1 overflow-hidden">
              <h4 className="text-xs font-medium truncate">{source.title}</h4>
              <p className="text-[10px] text-slate-500 truncate">{source.url || 'Original Document'}</p>
            </div>
            <ChevronRight size={14} className="text-slate-600 group-hover:text-white transition-colors" />
          </div>
        </div>
      ))}
    </div>
  );
};

export default SourceViewer;

import React, { useState } from 'react';
import { BookOpen, FileText, Trash2, ArrowRight, Search, Plus, Sparkles, CheckSquare, Square } from 'lucide-react';

const DocsPanel = ({ papers, activePaper, onSelect, onDelete, onUpload, loading, uploadJob, onSynthesize }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);

  // Filter papers by search query
  const filteredPapers = papers.filter(p => 
    p.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  // Toggle selection for comparison
  const handleToggleSelect = (e, id) => {
    e.stopPropagation(); // Avoid triggering open
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="h-full flex flex-col p-6 bg-[#0a0a0c] overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 select-none">
        <div>
          <h2 className="text-2xl font-bold font-['Outfit'] tracking-tight text-white flex items-center gap-2">
            <BookOpen size={24} className="text-indigo-400" /> My Technical Library
          </h2>
          <p className="text-xs text-slate-500 mt-1">Manage, select active workspace, or checkmark multiple papers to synthesize.</p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Synthesize comparison button (Visible when >= 2 papers checked) */}
          {selectedIds.length >= 2 && (
            <button
              onClick={() => onSynthesize(selectedIds)}
              className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-lg shadow-indigo-600/30 animate-pulse transition-all shrink-0"
            >
              <Sparkles size={14} /> Compare Selected ({selectedIds.length})
            </button>
          )}

          <label className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-xl text-xs font-semibold cursor-pointer transition-all shrink-0">
            <Plus size={14} /> Upload Paper
            <input 
              type="file" 
              onChange={handleFileChange} 
              accept=".pdf" 
              disabled={loading}
              className="hidden" 
            />
          </label>
        </div>
      </div>

      {/* Loading state overlays */}
      {loading && (
        <div className="mb-6 p-4 glass-panel border-indigo-500/20 bg-indigo-500/5 flex items-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-xs font-semibold text-indigo-400">
              {uploadJob?.message || 'Processing and indexing document in background...'}
            </span>
            <div className="h-1 bg-white/10 rounded-full overflow-hidden mt-2">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(5, Math.min(100, uploadJob?.progress ?? 45))}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Search and select count */}
      <div className="flex justify-between items-center mb-6 gap-4">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by filename..."
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-xs text-white outline-none focus:border-indigo-500/50 transition-colors"
          />
        </div>
        {selectedIds.length > 0 && (
          <button 
            onClick={() => setSelectedIds([])}
            className="text-[10px] text-slate-500 hover:text-white uppercase font-bold tracking-wider"
          >
            Deselect All
          </button>
        )}
      </div>

      {/* Grid listing */}
      {filteredPapers.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-20 text-center glass-panel border-dashed border-2 border-white/5 p-8 select-none">
          <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-slate-600 mb-3">
            <FileText size={20} />
          </div>
          <h4 className="text-sm font-semibold text-slate-400">No Documents Found</h4>
          <p className="text-xs text-slate-500 max-w-xs leading-relaxed mt-1">
            {searchQuery ? "No papers match your search parameters." : "Your document vault is currently empty. Upload research papers to begin."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPapers.map((paper) => {
            const isActive = activePaper?.session_id === paper.id || activePaper?.session_id?.split(',').includes(paper.id);
            const isChecked = selectedIds.includes(paper.id);
            return (
              <div 
                key={paper.id} 
                className={`glass-panel p-5 border-white/5 flex flex-col justify-between transition-all group relative ${isActive ? 'ring-2 ring-indigo-500/50 bg-indigo-500/[0.02]' : 'hover:bg-white/[0.02]'}`}
              >
                {/* Checkbox select top left */}
                <button 
                  onClick={(e) => handleToggleSelect(e, paper.id)}
                  className="absolute top-4 left-4 p-1 text-slate-500 hover:text-indigo-400 z-10 transition-colors"
                  title="Checkmark to compare"
                >
                  {isChecked ? <CheckSquare size={16} className="text-indigo-500" /> : <Square size={16} />}
                </button>

                <div className="mb-4 pl-7">
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${isActive ? 'bg-indigo-500/20 text-indigo-400' : 'bg-white/5 text-slate-400'}`}>
                      <FileText size={16} />
                    </div>
                    
                    {/* Delete button */}
                    <button 
                      onClick={() => onDelete(paper.id)}
                      className="p-1.5 opacity-0 group-hover:opacity-100 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-all"
                      title="Delete document and logs"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  
                  <h3 className="text-xs font-semibold text-slate-200 line-clamp-2 leading-relaxed" title={paper.filename}>
                    {paper.filename}
                  </h3>
                  <p className="text-[9px] text-slate-500 mt-2 font-mono">
                    Parsed: {new Date(paper.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="pt-3 border-t border-white/5 flex items-center justify-between pl-7">
                  <span className="text-[9px] font-semibold text-indigo-400 tracking-wider uppercase">
                    {isActive ? 'Active workspace' : 'Inactive'}
                  </span>
                  
                  <button 
                    onClick={() => onSelect(paper.id)}
                    className="flex items-center gap-1 text-[10px] font-bold text-white hover:text-indigo-400 transition-colors uppercase tracking-wider"
                  >
                    Open <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DocsPanel;

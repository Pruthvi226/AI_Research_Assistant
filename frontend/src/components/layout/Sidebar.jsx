import React from 'react';
import { LayoutDashboard, MessageSquare, Search, BookOpen, Settings, FileText, X } from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab, activePaper, onEjectPaper }) => {
  const menuItems = [
    { id: 'chat', icon: MessageSquare, label: 'Chat Assistant' },
    { id: 'research', icon: Search, label: 'Research Lab' },
    { id: 'docs', icon: BookOpen, label: 'My Documents' },
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  ];

  return (
    <aside className="w-20 lg:w-64 border-r border-white/10 flex flex-col p-3 lg:p-4 bg-[#0a0a0c] select-none shrink-0">
      {/* Brand logo */}
      <div className="flex items-center justify-center lg:justify-start gap-3 px-1 lg:px-2 mb-8 lg:mb-10">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-500/30">S</div>
        <div className="hidden lg:flex flex-col">
          <span className="font-['Outfit'] text-xl font-bold tracking-tight text-white leading-none">Scientia.ai</span>
          <span className="text-[10px] text-slate-500 font-medium tracking-wide mt-1">RESEARCH LAB</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-2">
        {menuItems.map((item) => (
          <div
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            title={item.label}
            className={`sidebar-item justify-center lg:justify-start ${activeTab === item.id ? 'sidebar-item-active' : ''}`}
          >
            <item.icon size={20} />
            <span className="hidden lg:inline font-medium">{item.label}</span>
          </div>
        ))}
      </nav>

      {/* Active Paper Indicator */}
      {activePaper && (
        <div className="mx-0 lg:mx-2 mb-4 p-2 lg:p-3 bg-indigo-500/5 rounded-xl border border-indigo-500/10 flex items-center justify-center lg:justify-start gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 shrink-0">
            <FileText size={16} />
          </div>
          <div className="hidden lg:block flex-1 min-w-0">
            <p className="text-xs font-semibold truncate text-slate-200">{activePaper.filename}</p>
            <p className="text-[9px] text-slate-500 font-medium uppercase mt-0.5">Active Workspace</p>
          </div>
          <button 
            onClick={onEjectPaper} 
            title="Eject active paper" 
            className="hidden lg:block p-1 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Footer controls */}
      <div className="pt-6 border-t border-white/10 space-y-2">
        <div 
          onClick={() => setActiveTab('settings')}
          title="Settings"
          className={`sidebar-item justify-center lg:justify-start ${activeTab === 'settings' ? 'sidebar-item-active' : ''}`}
        >
          <Settings size={20} />
          <span className="hidden lg:inline">Settings</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;


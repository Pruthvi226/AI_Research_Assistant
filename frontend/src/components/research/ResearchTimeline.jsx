import React from 'react';
import { Clock, CheckCircle2, Circle } from 'lucide-react';

const ResearchTimeline = ({ steps }) => {
  return (
    <div className="p-6 space-y-8">
      <h3 className="text-sm font-semibold text-slate-400 mb-6">Research Journey</h3>
      <div className="relative pl-8 space-y-8 border-l border-white/10 ml-2">
        {steps.map((step, i) => (
          <div key={i} className="relative">
            <div className={`absolute -left-[41px] top-0 w-6 h-6 rounded-full flex items-center justify-center border-4 border-[#0a0a0c] ${step.status === 'completed' ? 'bg-indigo-600' : 'bg-[#16161a]'}`}>
              {step.status === 'completed' ? <CheckCircle2 size={12} className="text-white" /> : <Circle size={10} className="text-slate-600" />}
            </div>
            <div>
              <h4 className={`text-sm font-medium ${step.status === 'completed' ? 'text-white' : 'text-slate-500'}`}>{step.title}</h4>
              <p className="text-xs text-slate-500 mt-1">{step.description}</p>
              {step.time && <span className="text-[10px] text-indigo-400 mt-2 block flex items-center gap-1"><Clock size={10}/> {step.time}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResearchTimeline;

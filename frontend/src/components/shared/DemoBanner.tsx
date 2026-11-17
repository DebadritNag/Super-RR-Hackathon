import React from 'react';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

export const DemoBanner: React.FC = () => {
  return (
    <div className="bg-[#FDF3EB] border-b border-[#F8DCC9] text-[#202522] px-4 py-1.5 text-xs flex items-center justify-between select-none">
      <div className="flex items-center space-x-2 truncate">
        <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#D97736] text-white tracking-wider uppercase shrink-0">
          <AlertTriangle className="w-3 h-3" />
          <span>Experimental Submission</span>
        </span>
        <span className="text-[#777F79] hidden sm:inline">|</span>
        <span className="text-[#202522] font-medium text-[11px] truncate">
          <strong>Methodology Status:</strong> INTERNAL_EXPERIMENTAL_ONLY. Previous TEST holdout accessed in Phase 4. Rankings provisional under 70:30 combined criteria.
        </span>
      </div>
      <div className="hidden md:flex items-center space-x-2 text-[#777F79] shrink-0 text-[11px]">
        <span>RR SupeRR Selector Season 2</span>
        <ShieldAlert className="w-3.5 h-3.5 text-[#D97736]" />
      </div>
    </div>
  );
};

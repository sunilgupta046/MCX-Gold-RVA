import React from 'react';
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

export const DemoBanner = ({ isDemo = true }) => {
  if (!isDemo) return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2.5 text-xs text-amber-200">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium">
          <AlertTriangle size={15} className="text-amber-400 shrink-0 animate-bounce" />
          <span>
            <strong className="text-amber-300 font-semibold uppercase tracking-wider">Demo / Synthetic Dataset Active:</strong>{' '}
            Prices shown are statistically calibrated synthetic Bhavcopy simulations for development, quantitative testing, and algorithmic validation.
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-amber-400/90 font-mono">
          <span className="flex items-center gap-1">
            <ShieldAlert size={13} /> Paper Analysis Only (No Live Order Execution)
          </span>
          <span className="hidden lg:inline text-amber-500/40">•</span>
          <span className="hidden lg:inline text-slate-400">COZY NEXUS Quantitative Systems</span>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import clsx from 'clsx';

export const StatusBadge = ({ status, className = '' }) => {
  const norm = (status || '').toUpperCase();

  const styles = {
    // Signal Qualification Statuses
    QUALIFIED_FOR_REVIEW: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 font-bold',
    NO_SIGNAL: 'bg-slate-800/80 text-slate-400 border-slate-700/80',
    INSUFFICIENT_DATA: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    LIQUIDITY_WARNING: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
    EXPIRY_LOCKOUT: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    DISQUALIFIED: 'bg-rose-900/20 text-rose-400 border-rose-800/40',
    
    // Microstructure Diagnostics
    ADEQUATE: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    LOW_VOLUME: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
    LOW_OI: 'bg-amber-500/20 text-amber-300 border-amber-500/40',

    // Strengths
    EXTREME: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    HIGH: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    MEDIUM: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    LOW: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
    
    // Actions
    ACTIVE: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 animate-pulse',
    TRIGGERED: 'bg-gold-500/15 text-gold-400 border-gold-500/30',
    CLOSED: 'bg-slate-700/30 text-slate-400 border-slate-600/30',
    EXPIRED: 'bg-slate-700/30 text-slate-400 border-slate-600/30',

    // Data quality
    HEALTHY: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    WARNING: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    CRITICAL: 'bg-rose-500/15 text-rose-400 border-rose-500/30',

    // Pairs action
    LONG_SPREAD: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    SHORT_SPREAD: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  };

  const currentStyle = styles[norm] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide border',
        currentStyle,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 opacity-80" />
      {norm.replace(/_/g, ' ')}
    </span>
  );
};

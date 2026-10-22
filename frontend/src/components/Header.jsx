import React, { useState, useEffect } from 'react';
import { RefreshCw, Clock, Database, Sparkles } from 'lucide-react';
import { endpoints } from '../api/client';

export const Header = ({ title, subtitle, onRefresh, isRefreshing = false, isDemo = false }) => {
  const [time, setTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }) + ' IST'
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-navy-900/60 backdrop-blur border-b border-white/5 px-6 flex items-center justify-between shrink-0">
      <div>
        <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Dataset badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-navy-800 border border-white/5 text-xs font-mono text-slate-300">
          <Database size={13} className="text-gold-400" />
          <span>{isDemo ? 'DEMO DATASET' : 'MCX BHAVCOPY'}</span>
        </div>

        {/* Live IST clock */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-navy-800 border border-white/5 text-xs font-mono text-slate-400">
          <Clock size={13} className="text-cyan-400" />
          <span>{time}</span>
        </div>

        {/* Refresh trigger */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-medium border border-white/10 transition-colors disabled:opacity-50"
            title="Refresh current data"
          >
            <RefreshCw size={13} className={isRefreshing ? 'animate-spin text-gold-400' : ''} />
            <span className="hidden sm:inline">{isRefreshing ? 'Updating...' : 'Sync'}</span>
          </button>
        )}
      </div>
    </header>
  );
};

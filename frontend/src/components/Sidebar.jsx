import React from 'react';
import {
  LayoutDashboard,
  Layers,
  TrendingUp,
  FlaskConical,
  Radio,
  History,
  CheckCircle2,
  Sliders,
  Coins,
  ShieldCheck,
  Activity,
  DownloadCloud,
} from 'lucide-react';
import clsx from 'clsx';

export const NAVIGATION_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null },
  { id: 'contracts', label: 'Contract Explorer', icon: Layers, badge: '4' },
  { id: 'analytics', label: 'Relative Value Analytics', icon: TrendingUp, badge: 'RVA' },
  { id: 'backtest', label: 'Backtesting Lab', icon: FlaskConical, badge: null },
  { id: 'signals', label: 'Signal Center', icon: Radio, badge: 'Live' },
  { id: 'alerts', label: 'Alert History', icon: History, badge: 'Audit' },
  { id: 'ingestion', label: 'Bhavcopy Ingestion', icon: DownloadCloud, badge: 'MCX' },
  { id: 'quality', label: 'Data Quality', icon: CheckCircle2, badge: null },
  { id: 'admin', label: 'Admin Panel', icon: Sliders, badge: null },
];

export const Sidebar = ({ activeTab, onSelectTab, systemStatus = 'healthy' }) => {
  return (
    <aside className="w-64 bg-navy-900 border-r border-white/5 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center gap-3 border-b border-white/5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold-400 to-amber-600 flex items-center justify-center text-navy-950 font-bold shadow-lg shadow-gold-500/20">
            <Coins size={20} className="text-navy-950" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm tracking-tight text-white">MCX GOLD RVA</span>
            </div>
            <p className="text-[10px] uppercase font-mono tracking-wider text-gold-400/80">COZY NEXUS QUANT</p>
          </div>
        </div>

        {/* Navigation list */}
        <div className="p-3 space-y-1">
          <p className="px-3 py-2 text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
            Platform Modules
          </p>
          {NAVIGATION_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={clsx(
                  'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group',
                  isActive
                    ? 'bg-gold-500/10 text-gold-400 font-semibold border border-gold-500/20 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-navy-800/60'
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    size={17}
                    className={clsx(
                      'transition-colors',
                      isActive ? 'text-gold-400' : 'text-slate-500 group-hover:text-slate-300'
                    )}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={clsx(
                      'text-[10px] px-1.5 py-0.2 rounded font-mono font-medium',
                      item.badge === 'Live'
                        ? 'bg-rose-500/20 text-rose-400 animate-pulse'
                        : 'bg-navy-800 text-slate-400 border border-white/5'
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-white/5 space-y-3">
        <div className="rounded-lg bg-navy-850 p-3 border border-white/5 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 text-[11px]">Backend API</span>
            <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              {systemStatus}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
            <span>MCX Gold Mini/10/G/P</span>
            <span>v1.0.0</span>
          </div>
        </div>

        <div className="text-[10px] text-center text-slate-500 font-mono">
          Public Bhavcopy Analytics Engine
        </div>
      </div>
    </aside>
  );
};

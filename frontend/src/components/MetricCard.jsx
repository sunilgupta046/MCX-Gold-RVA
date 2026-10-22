import React from 'react';
import clsx from 'clsx';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export const MetricCard = ({
  title,
  value,
  subvalue,
  change,
  isPositiveGood = true,
  icon: Icon,
  badgeText,
  badgeColor = 'gold',
  className = '',
}) => {
  const isPositive = change !== undefined && change > 0;
  const isNegative = change !== undefined && change < 0;

  const trendColor =
    change === undefined || change === 0
      ? 'text-slate-400'
      : (isPositive && isPositiveGood) || (isNegative && !isPositiveGood)
      ? 'text-emerald-400'
      : 'text-rose-400';

  return (
    <div
      className={clsx(
        'rounded-xl card-gradient p-5 relative overflow-hidden group hover:border-slate-700 transition-all duration-200',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium tracking-wider uppercase text-slate-400">{title}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono tracking-tight text-white">{value}</span>
            {badgeText && (
              <span
                className={clsx(
                  'text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border',
                  badgeColor === 'gold' && 'bg-gold-500/10 text-gold-400 border-gold-500/20',
                  badgeColor === 'cyan' && 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
                  badgeColor === 'emerald' && 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
                  badgeColor === 'rose' && 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                )}
              >
                {badgeText}
              </span>
            )}
          </div>
          {subvalue && <p className="text-xs text-slate-400 mt-1 font-mono">{subvalue}</p>}
        </div>

        {Icon && (
          <div className="p-2.5 rounded-lg bg-navy-800/80 text-gold-400 border border-white/5 group-hover:scale-105 transition-transform">
            <Icon size={20} />
          </div>
        )}
      </div>

      {change !== undefined && (
        <div className="mt-3 pt-3 border-t border-white/5 flex items-center text-xs gap-1.5 font-mono">
          {isPositive && <TrendingUp size={14} className={trendColor} />}
          {isNegative && <TrendingDown size={14} className={trendColor} />}
          {change === 0 && <Minus size={14} className={trendColor} />}
          <span className={trendColor}>
            {isPositive ? `+${change}%` : `${change}%`}
          </span>
          <span className="text-slate-400">vs 20d mean</span>
        </div>
      )}
    </div>
  );
};

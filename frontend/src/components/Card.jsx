import React from 'react';
import clsx from 'clsx';

export const Card = ({ children, className = '', glow = false, ...props }) => {
  return (
    <div
      className={clsx(
        'rounded-xl card-gradient p-5 transition-all duration-200',
        glow && 'border-gold-500/30 glow-gold',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({ title, subtitle, action, className = '' }) => {
  return (
    <div className={clsx('flex items-center justify-between pb-3 mb-3 border-b border-white/5', className)}>
      <div>
        <h3 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner = ({ text = 'Loading quantitative analytics...', fullScreen = false }) => {
  const content = (
    <div className="flex flex-col items-center justify-center p-8 gap-3">
      <div className="relative">
        <div className="w-10 h-10 rounded-full border-2 border-gold-500/20 border-t-gold-500 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-4 h-4 rounded-full bg-gold-500/10" />
        </div>
      </div>
      <p className="text-xs font-mono text-slate-400 tracking-wide">{text}</p>
    </div>
  );

  if (fullScreen) {
    return <div className="min-h-[50vh] flex items-center justify-center">{content}</div>;
  }

  return content;
};

import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export const ErrorAlert = ({ message, onRetry }) => {
  return (
    <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-5 flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="text-rose-400 shrink-0 mt-0.5" size={18} />
        <div>
          <h4 className="text-sm font-semibold text-rose-300">Analytics Service Error</h4>
          <p className="text-xs text-rose-200/80 mt-1">{message || 'Unable to load dataset or calculate metrics.'}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-medium border border-rose-500/30 transition-colors"
        >
          <RefreshCw size={13} /> Retry
        </button>
      )}
    </div>
  );
};

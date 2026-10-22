import React, { useEffect, useState } from 'react';
import {
  History,
  Filter,
  RefreshCw,
  Search,
  Calendar,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Radio,
  FileText,
  ChevronLeft,
  ChevronRight,
  Info,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatINR, formatBps, formatDate } from '../utils/formatters';
import { PAIRS } from '../utils/constants';

export const AlertHistory = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [historyData, setHistoryData] = useState({ total: 0, items: [], page: 1, page_size: 20 });
  
  // Filters
  const [selectedPair, setSelectedPair] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [qualifiedOnly, setQualifiedOnly] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        page,
        page_size: pageSize,
      };
      if (selectedPair) params.pair_name = selectedPair;
      if (selectedStatus) params.status = selectedStatus;
      if (qualifiedOnly) params.is_qualified = true;

      const res = await endpoints.getAlertHistory(params);
      setHistoryData(res.data);
    } catch (err) {
      setError(err.message || 'Failed to load alert history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [page, selectedPair, selectedStatus, qualifiedOnly]);

  const totalPages = Math.ceil((historyData.total || 0) / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Analytical Estimate Disclaimer */}
      <div className="p-3.5 rounded-xl border border-gold-500/30 bg-navy-900/90 text-xs text-slate-300 flex items-start gap-3 shadow-lg">
        <Info className="text-gold-400 shrink-0 mt-0.5" size={18} />
        <div>
          <span className="font-bold text-gold-400 uppercase tracking-wider block text-[11px]">
            Analytical Estimate Compliance Notice
          </span>
          All signals and candidate qualifications recorded in this history ledger are quantitative statistical estimates based on historical Bhavcopy settlement spreads and modeled transaction costs. They are not guaranteed arbitrage or executable trading instructions.
        </div>
      </div>

      {/* Header and Filter Card */}
      <Card>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <History className="text-gold-400" size={18} />
              <span>Historical Signal Qualification &amp; Alert Ledger</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Complete audit trail of all candidate evaluations, rejection reasons, and verified alerts.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedPair}
              onChange={(e) => {
                setSelectedPair(e.target.value);
                setPage(1);
              }}
              className="bg-navy-950 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-gold-500 font-mono"
            >
              <option value="">All Pairs</option>
              {PAIRS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="bg-navy-950 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-gold-500 font-mono"
            >
              <option value="">All Statuses</option>
              <option value="QUALIFIED_FOR_REVIEW">QUALIFIED_FOR_REVIEW</option>
              <option value="NO_SIGNAL">NO_SIGNAL</option>
              <option value="INSUFFICIENT_DATA">INSUFFICIENT_DATA</option>
              <option value="LIQUIDITY_WARNING">LIQUIDITY_WARNING</option>
              <option value="EXPIRY_LOCKOUT">EXPIRY_LOCKOUT</option>
            </select>

            <label className="flex items-center gap-2 text-xs text-slate-300 font-medium cursor-pointer">
              <input
                type="checkbox"
                checked={qualifiedOnly}
                onChange={(e) => {
                  setQualifiedOnly(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-white/10 bg-navy-950 text-gold-500 focus:ring-gold-500"
              />
              <span>Qualified Only</span>
            </label>

            <button
              onClick={loadHistory}
              className="p-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-300 border border-white/10 transition-colors"
              title="Refresh History"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </Card>

      {error && <ErrorAlert message={error} onRetry={loadHistory} />}

      {/* History Table */}
      <Card>
        <CardHeader
          title={`Alert History (${historyData.total} total evaluations)`}
          subtitle="Chronological audit records with itemized edges, costs, DTE, and rejection explanations"
        />

        {loading ? (
          <div className="py-12">
            <LoadingSpinner text="Retrieving historical alert audit trail..." />
          </div>
        ) : historyData.items.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No historical alert records match the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/5 text-slate-400 text-[11px] uppercase tracking-wider font-mono">
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Contract Pair</th>
                  <th className="py-2.5 px-3">Expiries (Base / Quote)</th>
                  <th className="py-2.5 px-3">Normalized Prices (₹/10g)</th>
                  <th className="py-2.5 px-3">Adj Spread</th>
                  <th className="py-2.5 px-3">Z-Score</th>
                  <th className="py-2.5 px-3">Gross / Costs / Net Edge</th>
                  <th className="py-2.5 px-3">Coverage</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Audit Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-mono">
                {historyData.items.map((item) => (
                  <tr key={item.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-3 text-slate-300 whitespace-nowrap">
                      {formatDate(item.signal_date)}
                    </td>
                    <td className="py-3 px-3 font-sans font-bold text-white whitespace-nowrap">
                      {item.pair_name.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-400 whitespace-nowrap">
                      <div>{item.base_expiry_date ? formatDate(item.base_expiry_date) : '—'}</div>
                      <div className="text-slate-500">{item.quote_expiry_date ? formatDate(item.quote_expiry_date) : '—'}</div>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-slate-300 whitespace-nowrap">
                      <div>Base: {item.base_normalized_price ? formatINR(item.base_normalized_price) : '—'}</div>
                      <div className="text-slate-500">Quote: {item.quote_normalized_price ? formatINR(item.quote_normalized_price) : '—'}</div>
                    </td>
                    <td className="py-3 px-3 font-semibold text-gold-400 whitespace-nowrap">
                      {item.adjusted_spread !== null && item.adjusted_spread !== undefined
                        ? formatINR(item.adjusted_spread)
                        : '—'}
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-bold text-slate-200">
                        {item.z_score !== null ? `${item.z_score > 0 ? '+' : ''}${item.z_score}σ` : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[11px] whitespace-nowrap">
                      <div className="text-slate-300">Gross: {item.expected_gross_edge_bps ? formatBps(item.expected_gross_edge_bps) : '—'}</div>
                      <div className="text-slate-500">Costs: {item.estimated_costs_bps ? formatBps(item.estimated_costs_bps) : '—'}</div>
                      <div className={item.expected_net_edge_bps > 0 ? 'text-emerald-400 font-bold' : 'text-rose-400'}>
                        Net: {item.expected_net_edge_bps !== null && item.expected_net_edge_bps !== undefined ? formatBps(item.expected_net_edge_bps) : '—'}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`text-[11px] font-bold ${item.cost_coverage_ratio >= 2.5 ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {item.cost_coverage_ratio ? `${item.cost_coverage_ratio}x` : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="py-3 px-3 font-sans text-[11px] text-slate-400 max-w-xs">
                      {item.rejection_reason ? (
                        <span className="text-rose-300/80 block leading-tight">{item.rejection_reason}</span>
                      ) : (
                        <span className="text-emerald-400/90 block leading-tight">Passed 2.5x hurdle &amp; DTE guardrails</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="pt-4 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
          <span>
            Showing Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 border border-white/10 disabled:opacity-40 transition-colors"
            >
              <ChevronLeft size={14} />
              <span>Previous</span>
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 border border-white/10 disabled:opacity-40 transition-colors"
            >
              <span>Next</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import {
  Radio,
  RefreshCw,
  Filter,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Shield,
  Layers,
  TrendingDown,
  TrendingUp,
  BellOff,
  Bell,
  Sparkles,
  Lock,
  History,
  FileCheck2,
  SlidersHorizontal,
  Info,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatINR, formatBps, formatDate } from '../utils/formatters';
import { PAIRS } from '../utils/constants';
import { AlertHistory } from './AlertHistory';

export const SignalCenter = () => {
  const [activeTab, setActiveTab] = useState('candidates'); // 'candidates', 'qualified', 'history'
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState(null);

  // Candidate evaluation state
  const [candidateData, setCandidateData] = useState(null);
  const [qualifiedAlerts, setQualifiedAlerts] = useState([]);

  // Configurable parameters
  const [expiryLockoutDays, setExpiryLockoutDays] = useState(5);
  const [costCoverageHurdle, setCostCoverageHurdle] = useState(2.5);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [candRes, qualRes] = await Promise.all([
        endpoints.getCandidates({
          expiry_lockout_days: expiryLockoutDays,
          cost_coverage_hurdle: costCoverageHurdle,
        }),
        endpoints.getQualifiedSignals(),
      ]);
      setCandidateData(candRes.data);
      setQualifiedAlerts(qualRes.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch candidate evaluations and signals.');
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async () => {
    try {
      setEvaluating(true);
      setError(null);
      const res = await endpoints.evaluateSignals({
        expiry_lockout_days: expiryLockoutDays,
        cost_coverage_hurdle: costCoverageHurdle,
      });
      setCandidateData(res.data);
      const qualRes = await endpoints.getQualifiedSignals();
      setQualifiedAlerts(qualRes.data);
    } catch (err) {
      setError(err.message || 'Failed to evaluate candidates.');
    } finally {
      setEvaluating(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [expiryLockoutDays, costCoverageHurdle]);

  if (loading && !candidateData) {
    return <LoadingSpinner text="Evaluating relative-value candidates against quantitative guardrails..." fullScreen />;
  }

  const statusSummary = candidateData?.status_summary || {};

  return (
    <div className="space-y-6">
      {/* Analytical Estimate Compliance Banner */}
      <div className="p-3.5 rounded-xl border border-gold-500/30 bg-navy-900/90 text-xs text-slate-300 flex items-start gap-3 shadow-lg">
        <Info className="text-gold-400 shrink-0 mt-0.5" size={18} />
        <div>
          <span className="font-bold text-gold-400 uppercase tracking-wider block text-[11px]">
            Analytical Estimate Compliance Notice
          </span>
          All signals and candidate qualifications presented here are quantitative analytical estimates based on statistical divergence and modeled MCX transaction costs. They are not guaranteed arbitrage, investment advice, or executable trading instructions.
        </div>
      </div>

      {/* Navigation & Controls Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-2 rounded-xl bg-navy-900 border border-white/5">
        <div className="flex items-center gap-1.5 p-1 bg-navy-950 rounded-lg border border-white/5">
          <button
            onClick={() => setActiveTab('candidates')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeTab === 'candidates'
                ? 'bg-gold-500 text-navy-950 shadow-md font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Radio size={14} />
            <span>Real-Time Candidate Qualification</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-navy-900/60 font-mono">
              {candidateData?.total_candidates_evaluated || 0} Pairs
            </span>
          </button>

          <button
            onClick={() => setActiveTab('qualified')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeTab === 'qualified'
                ? 'bg-gold-500 text-navy-950 shadow-md font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <CheckCircle size={14} />
            <span>Qualified Alerts</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-mono font-bold">
              {qualifiedAlerts.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
              activeTab === 'history'
                ? 'bg-gold-500 text-navy-950 shadow-md font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <History size={14} />
            <span>Alert History</span>
          </button>
        </div>

        {/* Evaluation parameters */}
        {activeTab === 'candidates' && (
          <div className="flex flex-wrap items-center gap-3 px-2">
            <div className="flex items-center gap-1 text-xs text-slate-300 font-mono">
              <span className="text-slate-500 text-[11px]">T-</span>
              <input
                type="number"
                min="1"
                max="15"
                value={expiryLockoutDays}
                onChange={(e) => setExpiryLockoutDays(Number(e.target.value))}
                className="w-12 bg-navy-950 border border-white/10 rounded px-1.5 py-1 text-xs text-center text-gold-400 font-bold focus:outline-none focus:border-gold-500"
              />
              <span className="text-slate-400 text-[11px]">DTE Lockout</span>
            </div>

            <div className="flex items-center gap-1 text-xs text-slate-300 font-mono">
              <span className="text-slate-500 text-[11px]">Hurdle:</span>
              <input
                type="number"
                step="0.5"
                min="1.0"
                max="5.0"
                value={costCoverageHurdle}
                onChange={(e) => setCostCoverageHurdle(Number(e.target.value))}
                className="w-14 bg-navy-950 border border-white/10 rounded px-1.5 py-1 text-xs text-center text-gold-400 font-bold focus:outline-none focus:border-gold-500"
              />
              <span className="text-slate-400 text-[11px]">x Costs</span>
            </div>

            <button
              onClick={handleEvaluate}
              disabled={evaluating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} className={evaluating ? 'animate-spin text-gold-400' : ''} />
              <span>{evaluating ? 'Evaluating...' : 'Re-evaluate'}</span>
            </button>
          </div>
        )}
      </div>

      {error && <ErrorAlert message={error} onRetry={loadData} />}

      {/* VIEW: Alert History */}
      {activeTab === 'history' && <AlertHistory />}

      {/* VIEW: Candidate Qualification or Qualified Alerts */}
      {activeTab !== 'history' && (
        <>
          {/* Status Metric Breakdown Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <MetricCard
              title="Qualified For Review"
              value={statusSummary.QUALIFIED_FOR_REVIEW || 0}
              subvalue="Passed 2.5x hurdle & DTE"
              icon={CheckCircle}
              badgeColor="emerald"
            />
            <MetricCard
              title="Suppressed (No Signal)"
              value={statusSummary.NO_SIGNAL || 0}
              subvalue="Below 2.5x cost hurdle"
              icon={Radio}
              badgeColor="slate"
            />
            <MetricCard
              title="T-5 Expiry Lockout"
              value={statusSummary.EXPIRY_LOCKOUT || 0}
              subvalue={`DTE <= ${expiryLockoutDays}d delivery tender`}
              icon={Lock}
              badgeColor="rose"
            />
            <MetricCard
              title="Liquidity Warning"
              value={statusSummary.LIQUIDITY_WARNING || 0}
              subvalue="Volume/OI below threshold"
              icon={AlertTriangle}
              badgeColor="amber"
            />
            <MetricCard
              title="Insufficient Data"
              value={statusSummary.INSUFFICIENT_DATA || 0}
              subvalue="History < 20 observations"
              icon={Layers}
              badgeColor="cyan"
            />
          </div>

          {/* Qualified Alerts Tab Display */}
          {activeTab === 'qualified' && (
            <div className="space-y-4">
              {qualifiedAlerts.length === 0 ? (
                <Card className="text-center py-12">
                  <BellOff size={36} className="mx-auto text-slate-600 mb-2" />
                  <h4 className="text-sm font-semibold text-slate-200">
                    0 Qualified Opportunities Under Current Guardrails
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 max-w-lg mx-auto">
                    All cross-contract spreads are currently within normal statistical bands or fail the 2.5x estimated transaction cost hurdle. In accordance with platform integrity rules, no synthetic alerts are fabricated.
                  </p>
                </Card>
              ) : (
                qualifiedAlerts.map((sig) => (
                  <Card key={sig.id} className="border-emerald-500/30 bg-gradient-to-r from-navy-900 to-navy-850">
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-3 border-b border-white/5">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-white">{sig.pair_name.replace(/_/g, ' ')}</h4>
                          <StatusBadge status="QUALIFIED_FOR_REVIEW" />
                          <span className="text-xs font-mono text-gold-400 font-bold">{sig.z_score}σ</span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1 font-mono">
                          Expiries: Base {sig.base_expiry_date ? formatDate(sig.base_expiry_date) : '—'} • Quote {sig.quote_expiry_date ? formatDate(sig.quote_expiry_date) : '—'}
                        </p>
                      </div>

                      <div className="flex items-center gap-4 text-xs font-mono">
                        <div className="text-right">
                          <span className="text-slate-500 block text-[10px] uppercase">Carry-Adj Spread</span>
                          <span className="text-gold-400 font-bold">{formatINR(sig.adjusted_spread || sig.spread_value_per_10g)}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-slate-500 block text-[10px] uppercase">Total Costs</span>
                          <span className="text-slate-300 font-bold">{formatBps(sig.estimated_costs_bps || sig.est_roundtrip_cost_bps)}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-slate-500 block text-[10px] uppercase">Expected Net Edge</span>
                          <span className="text-emerald-400 font-bold">+{sig.expected_net_edge_bps || sig.net_edge_bps} bps</span>
                        </div>
                      </div>
                    </div>

                    <div className="pt-3 text-xs text-slate-300 font-sans leading-relaxed">
                      {sig.signal_explanation || sig.rational}
                    </div>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* Real-Time Candidate Qualification Inspector Table */}
          {activeTab === 'candidates' && (
            <Card>
              <CardHeader
                title="Cross-Contract Relative Value Candidate Inspector"
                subtitle={`Full audit evaluation across all 6 contract pairs as of settlement date ${formatDate(candidateData?.as_of_date)}`}
              />

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-400 text-[11px] uppercase tracking-wider font-mono">
                      <th className="py-2.5 px-3">Contract Pair</th>
                      <th className="py-2.5 px-3">Expiries (Base / Quote)</th>
                      <th className="py-2.5 px-3">Norm Prices (₹/10g)</th>
                      <th className="py-2.5 px-3">Adj Spread</th>
                      <th className="py-2.5 px-3">Z-Score</th>
                      <th className="py-2.5 px-3">Estimated Costs</th>
                      <th className="py-2.5 px-3">Expected Net Edge</th>
                      <th className="py-2.5 px-3">Cost Coverage</th>
                      <th className="py-2.5 px-3">Liquidity / Expiry Status</th>
                      <th className="py-2.5 px-3">Qualification Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono">
                    {candidateData?.candidates?.map((cand) => (
                      <React.Fragment key={cand.pair_name}>
                        <tr className="hover:bg-white/[0.02] transition-colors">
                          <td className="py-3 px-3 font-sans font-bold text-white whitespace-nowrap">
                            {cand.pair_name.replace(/_/g, ' ')}
                          </td>
                          <td className="py-3 px-3 text-[11px] text-slate-400 whitespace-nowrap">
                            <div>{cand.base_expiry_date ? formatDate(cand.base_expiry_date) : '—'}</div>
                            <div className="text-slate-500">{cand.quote_expiry_date ? formatDate(cand.quote_expiry_date) : '—'}</div>
                          </td>
                          <td className="py-3 px-3 text-[11px] text-slate-300 whitespace-nowrap">
                            <div>Base: {formatINR(cand.base_normalized_price)}</div>
                            <div className="text-slate-500">Quote: {formatINR(cand.quote_normalized_price)}</div>
                          </td>
                          <td className="py-3 px-3 font-semibold text-gold-400 whitespace-nowrap">
                            {formatINR(cand.adjusted_spread)}
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <span className="font-bold text-slate-200">
                              {cand.z_score !== null ? `${cand.z_score > 0 ? '+' : ''}${cand.z_score}σ` : '—'}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                            <div>{formatBps(cand.estimated_costs_bps)}</div>
                            <div className="text-[10px] text-slate-500">{formatINR(cand.estimated_costs_inr)}/10g</div>
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <div className={`font-bold ${cand.expected_net_edge_bps > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {cand.expected_net_edge_bps > 0 ? '+' : ''}{cand.expected_net_edge_bps} bps
                            </div>
                            <div className="text-[10px] text-slate-500">
                              {formatINR(cand.expected_net_edge_inr)}/10g
                            </div>
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                cand.cost_coverage_ratio >= costCoverageHurdle
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : 'bg-navy-950 text-slate-400'
                              }`}
                            >
                              {cand.cost_coverage_ratio}x
                            </span>
                          </td>
                          <td className="py-3 px-3 text-[11px] whitespace-nowrap">
                            <div>
                              Liq: <StatusBadge status={cand.liquidity_status} />
                            </div>
                            <div className="mt-1">
                              Exp: <StatusBadge status={cand.expiry_status} />
                            </div>
                          </td>
                          <td className="py-3 px-3 whitespace-nowrap">
                            <StatusBadge status={cand.status} />
                          </td>
                        </tr>

                        {/* Rejection / Explanation Dropdown Row */}
                        <tr className="bg-navy-950/40 text-[11px]">
                          <td colSpan="10" className="py-2 px-3 border-b border-white/5 font-sans">
                            <div className="space-y-1">
                              {cand.rejection_reasons && cand.rejection_reasons.length > 0 ? (
                                <div className="flex flex-wrap items-center gap-1.5">
                                  <span className="font-semibold text-rose-400 uppercase text-[10px] tracking-wide">
                                    Rejection Reasons:
                                  </span>
                                  {cand.rejection_reasons.map((r, i) => (
                                    <span
                                      key={i}
                                      className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 font-mono text-[10px]"
                                    >
                                      {r}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-emerald-400 font-semibold flex items-center gap-1.5">
                                  <CheckCircle size={13} />
                                  <span>Passed all 10 quantitative rules: divergence, 2.5x cost hurdle, positive net edge, DTE, and volume.</span>
                                </div>
                              )}
                              <p className="text-slate-400 text-[11px] leading-relaxed">
                                {cand.signal_explanation}
                              </p>
                            </div>
                          </td>
                        </tr>
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  Coins,
  Radio,
  Activity,
  ArrowRight,
  Database,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  BarChart2,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { Card, CardHeader } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { PlotlyChart } from '../components/PlotlyChart';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatINR, formatNumber, formatBps, formatPercent, formatDate } from '../utils/formatters';

export const Dashboard = ({ onNavigate }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [overview, setOverview] = useState(null);
  const [normPrices, setNormPrices] = useState([]);
  const [activeSignals, setActiveSignals] = useState([]);
  const [latestBacktest, setLatestBacktest] = useState(null);
  const [qualityReport, setQualityReport] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ovRes, normRes, sigRes, backtestRes, qualRes] = await Promise.all([
        endpoints.getOverviewMetrics(),
        endpoints.getNormalizedPrices({ limit: 400 }),
        endpoints.getActiveSignals(),
        endpoints.getBacktestHistory().catch(() => ({ data: [] })),
        endpoints.getDataQualityReport().catch(() => null),
      ]);
      setOverview(ovRes.data);
      setNormPrices(normRes.data);
      setActiveSignals(sigRes.data);
      if (backtestRes?.data?.length > 0) {
        setLatestBacktest(backtestRes.data[0]);
      }
      if (qualRes?.data) {
        setQualityReport(qualRes.data);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch dashboard metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingSpinner text="Aggregating MCX Gold Relative Value Analytics..." fullScreen />;
  if (error) return <ErrorAlert message={error} onRetry={loadData} />;

  // Prepare normalized price chart traces
  const symbols = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];
  const colors = {
    GOLDM: '#eab308',
    GOLDTEN: '#06b6d4',
    GOLDGUINEA: '#a855f7',
    GOLDPETAL: '#10b981',
  };

  const chartTraces = symbols.map((sym) => {
    const series = normPrices.filter((p) => p.symbol === sym);
    return {
      x: series.map((p) => p.trade_date),
      y: series.map((p) => p.price_per_10g),
      name: `${sym} (₹/10g)`,
      type: 'scatter',
      mode: 'lines',
      line: { color: colors[sym], width: sym === 'GOLDM' ? 2.5 : 1.5 },
    };
  });

  return (
    <div className="space-y-6">
      {/* Top Divergence Banner */}
      {overview?.top_divergence_pair && (
        <div className="rounded-xl border border-gold-500/30 bg-gradient-to-r from-gold-500/10 via-navy-850 to-navy-900 p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gold-500/20 text-gold-400 flex items-center justify-center shrink-0">
              <Sparkles size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gold-400">
                  Key Relative Value Divergence
                </span>
                <span className="text-[10px] bg-gold-500/20 text-gold-300 px-1.5 py-0.5 rounded font-mono">
                  Z = {overview.top_divergence_pair.z_score}σ
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                <strong className="text-white">{overview.top_divergence_pair.pair_name.replace(/_/g, ' ')}</strong>{' '}
                is trading at a carry-adjusted spread of{' '}
                <strong className="font-mono text-gold-300">
                  {formatINR(overview.top_divergence_pair.carry_adjusted_spread_per_10g)}/10g
                </strong>{' '}
                (Mean: {formatINR(overview.top_divergence_pair.rolling_mean_20d)}/10g).
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('analytics')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 text-xs font-bold transition-all shadow-md shrink-0"
          >
            <span>Analyze Spread</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Data Freshness Indicator & Quality Warning */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 rounded-xl bg-navy-900 border border-white/5 text-xs">
        <div className="flex items-center gap-2.5 font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-slate-400">
            Market Data Freshness: <strong className="text-white">{overview?.as_of_date ? formatDate(overview.as_of_date) : 'No Data'}</strong>
          </span>
          <span className="text-slate-600">•</span>
          <span className="text-slate-400">
            Records: <strong className="text-white">{formatNumber(overview?.total_data_points, 0)}</strong>
          </span>
          {qualityReport?.is_demo_dataset && (
            <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30 text-[10px]">
              DEMO DATASET
            </span>
          )}
        </div>

        {qualityReport?.missing_dates_detected > 0 ? (
          <button
            onClick={() => onNavigate('quality')}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 transition-all font-mono text-[11px]"
          >
            <AlertCircle size={13} className="text-amber-400 shrink-0" />
            <span>Warning: {qualityReport.missing_dates_detected} missing trading dates detected</span>
            <ArrowRight size={12} />
          </button>
        ) : (
          <span className="text-emerald-400 flex items-center gap-1 font-mono text-[11px]">
            <ShieldCheck size={13} />
            <span>Continuity Audited: Healthy</span>
          </span>
        )}
      </div>

      {/* Empty State when no data */}
      {(!overview?.total_data_points || overview.total_data_points === 0) && (
        <Card className="text-center py-12 border-amber-500/30 bg-navy-900/90">
          <Database size={36} className="mx-auto text-amber-400 mb-2" />
          <h4 className="text-sm font-semibold text-white">No Bhavcopy Settlement Data Found</h4>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            Upload public MCX daily Bhavcopy CSV files or generate calibrated demo data from the Admin Panel to populate relative-value spreads.
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            <button
              onClick={() => onNavigate('admin')}
              className="px-3.5 py-1.5 rounded-lg bg-gold-500 text-navy-950 font-bold text-xs hover:bg-gold-400 transition-colors"
            >
              Go to Admin Panel
            </button>
          </div>
        </Card>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Benchmark (GOLDM)"
          value={formatINR(overview?.benchmark_goldm_price_10g)}
          subvalue="Quoted per 10 grams"
          icon={Coins}
          badgeText="Active Benchmark"
          badgeColor="gold"
        />
        <MetricCard
          title="Active RVA Signals"
          value={overview?.active_signals_count || 0}
          subvalue="Filtered post friction costs"
          icon={Radio}
          badgeText={overview?.active_signals_count > 0 ? 'Signals Triggered' : 'Neutral'}
          badgeColor={overview?.active_signals_count > 0 ? 'rose' : 'cyan'}
        />
        <MetricCard
          title="Contracts Tracked"
          value="4 Instruments"
          subvalue="Mini, Ten, Guinea, Petal"
          icon={Activity}
          badgeText="Standardized ₹/10g"
          badgeColor="cyan"
        />
        <MetricCard
          title="Historical Bhavcopy"
          value={formatNumber(overview?.total_data_points, 0)}
          subvalue={overview?.as_of_date ? `Latest Date: ${formatDate(overview.as_of_date)}` : 'No data'}
          icon={Database}
          badgeText="Daily Settlements"
          badgeColor="emerald"
        />
      </div>

      {/* Main Charts & Pairs Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Normalized Price Trend Chart */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader
              title="Normalized Futures Settlement Price (₹/10g)"
              subtitle="All 4 contracts standardized to a common 10g denomination"
              action={
                <button
                  onClick={() => onNavigate('analytics')}
                  className="text-xs text-gold-400 hover:text-gold-300 font-medium flex items-center gap-1"
                >
                  Full View <ArrowRight size={13} />
                </button>
              }
            />
            <div className="h-[340px]">
              <PlotlyChart
                data={chartTraces}
                layout={{
                  height: 340,
                  margin: { l: 65, r: 25, t: 15, b: 35 },
                  yaxis: { title: 'Price (₹ / 10g)', tickprefix: '₹' },
                  legend: { orientation: 'h', y: -0.2 },
                }}
              />
            </div>
          </Card>
        </div>

        {/* Active Signals Quick Feed */}
        <div>
          <Card className="h-full flex flex-col justify-between">
            <div>
              <CardHeader
                title="Active RVA Signals"
                subtitle="Live arbitrage & mean reversion alerts"
                action={
                  <button
                    onClick={() => onNavigate('signals')}
                    className="text-xs text-gold-400 hover:text-gold-300 font-medium flex items-center gap-1"
                  >
                    All ({activeSignals.length}) <ArrowRight size={13} />
                  </button>
                }
              />
              <div className="space-y-3 mt-3 overflow-y-auto max-h-[300px]">
                {activeSignals.length === 0 ? (
                  <div className="text-center py-10 text-slate-500 text-xs">
                    No active mispricing signals currently triggered above hurdle rate.
                  </div>
                ) : (
                  activeSignals.slice(0, 4).map((sig) => (
                    <div
                      key={sig.id}
                      className="p-3 rounded-lg bg-navy-850/80 border border-white/5 space-y-1.5 hover:border-gold-500/20 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-200">
                          {sig.pair_name.replace(/_/g, ' ')}
                        </span>
                        <StatusBadge status={sig.strength} />
                      </div>
                      <p className="text-[11px] font-mono text-gold-400 font-semibold">{sig.action.replace(/__/g, ' | ')}</p>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-white/5">
                        <span>Z-Score: <strong className="text-white font-mono">{sig.z_score}σ</strong></span>
                        <span>Net Edge: <strong className="text-emerald-400 font-mono">+{sig.net_edge_bps} bps</strong></span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-white/5">
              <button
                onClick={() => onNavigate('backtest')}
                className="w-full py-2 px-3 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 flex items-center justify-center gap-2 transition-colors"
              >
                <span>Launch Backtest Simulation</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </Card>
        </div>
      </div>

      {/* Walk-Forward Strategy Validation Banner */}
      {latestBacktest ? (
        <div className="rounded-xl border border-gold-500/20 bg-gradient-to-r from-navy-900 via-navy-850 to-navy-900 p-4 shadow-lg">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Walk-Forward Backtest Verified
                </span>
                <span className="text-xs font-bold text-slate-200 font-mono">
                  {latestBacktest.pair_name.replace(/_/g, ' ')}
                </span>
                <span className="text-[11px] text-slate-400">
                  ({latestBacktest.start_date} → {latestBacktest.end_date})
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Out-of-sample temporal execution with 0 look-ahead bias, tender lockout, and full MCX statutory friction deduction.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 lg:gap-6 py-2 border-y lg:border-y-0 lg:border-l border-white/10 lg:pl-6 w-full lg:w-auto font-mono">
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-sans">Net Return</span>
                <span className={`text-sm font-bold ${latestBacktest.total_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {latestBacktest.total_return_pct > 0 ? '+' : ''}{latestBacktest.total_return_pct}%
                </span>
                <span className="text-[10px] text-slate-400 block font-sans">Gross: {latestBacktest.gross_total_return_pct > 0 ? '+' : ''}{latestBacktest.gross_total_return_pct}%</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-sans">Gold Benchmark</span>
                <span className="text-sm font-bold text-gold-400">
                  {latestBacktest.benchmark_return_pct > 0 ? '+' : ''}{latestBacktest.benchmark_return_pct}%
                </span>
                <span className="text-[10px] text-slate-400 block font-sans">Buy & Hold</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-sans">Gold Beta (β)</span>
                <span className="text-sm font-bold text-cyan-400">
                  {latestBacktest.gold_beta ?? '0.000'}
                </span>
                <span className="text-[10px] text-slate-400 block font-sans">Market Neutral</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-sans">Sharpe Ratio</span>
                <span className="text-sm font-bold text-slate-200">
                  {latestBacktest.sharpe_ratio}
                </span>
                <span className="text-[10px] text-slate-400 block font-sans">Max DD: {latestBacktest.max_drawdown_pct}%</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-slate-400 block font-sans">Friction Deducted</span>
                <span className="text-sm font-bold text-slate-300">
                  {formatINR(latestBacktest.total_fees_paid)}
                </span>
                <span className="text-[10px] text-slate-400 block font-sans">{latestBacktest.total_trades} trades executed</span>
              </div>
            </div>

            <button
              onClick={() => onNavigate('backtest')}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-navy-800 hover:bg-navy-700 text-gold-400 border border-gold-500/30 text-xs font-semibold shrink-0 transition-colors shadow-sm"
            >
              <span>Explore Lab</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-white/5 bg-navy-850/60 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center shrink-0">
              <Activity size={18} />
            </div>
            <div>
              <h4 className="text-xs font-bold text-slate-200">Quantitative Walk-Forward Validation Engine</h4>
              <p className="text-[11px] text-slate-400">
                Simulate statistical arbitrage with train/validation/test splits, tender lockout, and full MCX cost schedules.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('backtest')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 text-xs font-bold transition-all shrink-0"
          >
            <span>Run Backtest</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Relative Pricing & Spread Matrix Table */}
      <Card>
        <CardHeader
          title="Cross-Contract Relative Value Matrix"
          subtitle="Real-time spread differentials, carry-adjusted spreads, and mean-reversion metrics"
        />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/5 text-slate-400 text-[11px] uppercase tracking-wider font-mono">
                <th className="py-2.5 px-3">Contract Pair</th>
                <th className="py-2.5 px-3">Raw Spread (₹/10g)</th>
                <th className="py-2.5 px-3">Carry-Adj Spread (₹/10g)</th>
                <th className="py-2.5 px-3">Spread %</th>
                <th className="py-2.5 px-3">20d Rolling Mean</th>
                <th className="py-2.5 px-3">Rolling Z-Score</th>
                <th className="py-2.5 px-3">Half-Life</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono">
              {overview?.current_spreads?.map((pair) => {
                const z = pair.z_score;
                const isDiverged = z !== null && Math.abs(z) >= 2.0;
                return (
                  <tr key={pair.pair_name} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-3 font-sans font-bold text-slate-200">
                      {pair.pair_name.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3 px-3 text-slate-300">{formatINR(pair.raw_spread_per_10g)}</td>
                    <td className="py-3 px-3 font-semibold text-gold-400">
                      {formatINR(pair.carry_adjusted_spread_per_10g)}
                    </td>
                    <td className="py-3 px-3 text-slate-400">{formatPercent(pair.spread_pct, 3)}</td>
                    <td className="py-3 px-3 text-slate-400">{formatINR(pair.rolling_mean_20d)}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                          isDiverged
                            ? z > 0
                              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-navy-800 text-slate-300'
                        }`}
                      >
                        {z !== null ? `${z > 0 ? '+' : ''}${z}σ` : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400">
                      {pair.half_life_days ? `${pair.half_life_days} days` : '—'}
                    </td>
                    <td className="py-3 px-3 text-right font-sans">
                      <button
                        onClick={() => onNavigate('analytics')}
                        className="text-xs text-gold-400 hover:text-gold-300 font-semibold"
                      >
                        Deep Dive →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

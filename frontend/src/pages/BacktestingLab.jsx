import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  Play,
  TrendingUp,
  Percent,
  ShieldAlert,
  Award,
  DollarSign,
  Activity,
  History,
  FileSpreadsheet,
  Shuffle,
  Split,
  Sliders,
  Download,
  ShieldCheck,
  CheckCircle,
  HelpCircle,
  BarChart2,
  Calendar,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { MetricCard } from '../components/MetricCard';
import { PlotlyChart } from '../components/PlotlyChart';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatINR, formatNumber, formatPercent, formatDate } from '../utils/formatters';
import { PAIRS } from '../utils/constants';

export const BacktestingLab = () => {
  const [running, setRunning] = useState(false);
  const [runningSensitivity, setRunningSensitivity] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('performance'); // 'performance', 'sensitivity', 'trades'
  
  // Strategy Parameters
  const [pairName, setPairName] = useState('GOLDM_vs_GOLDPETAL');
  const [entryZ, setEntryZ] = useState(2.0);
  const [exitZ, setExitZ] = useState(0.5);
  const [stopLossZ, setStopLossZ] = useState(3.5);
  const [windowDays, setWindowDays] = useState(20);
  const [useCarryAdj, setUseCarryAdj] = useState(true);
  const [includeCosts, setIncludeCosts] = useState(true);
  const [brokeragePerLot, setBrokeragePerLot] = useState(20.0);
  const [slippageTicksBase, setSlippageTicksBase] = useState(1.0);
  const [slippageTicksQuote, setSlippageTicksQuote] = useState(1.0);
  const [expiryLockoutDays, setExpiryLockoutDays] = useState(5);
  const [minVolumeLots, setMinVolumeLots] = useState(50);
  const [minOpenInterest, setMinOpenInterest] = useState(100);
  const [trainRatio, setTrainRatio] = useState(0.50);
  const [valRatio, setValRatio] = useState(0.25);
  const [walkForward, setWalkForward] = useState(false);
  const [trainWindowDays, setTrainWindowDays] = useState(40);
  const [testWindowDays, setTestWindowDays] = useState(15);
  const [capital, setCapital] = useState(1000000);

  // Result states
  const [result, setResult] = useState(null);
  const [sensitivityResult, setSensitivityResult] = useState(null);

  const executeBacktest = async () => {
    try {
      setRunning(true);
      setError(null);
      const res = await endpoints.runBacktest({
        pair_name: pairName,
        entry_z: parseFloat(entryZ),
        exit_z: parseFloat(exitZ),
        stop_loss_z: parseFloat(stopLossZ),
        window_days: parseInt(windowDays),
        use_carry_adj: useCarryAdj,
        include_costs: includeCosts,
        brokerage_per_lot_inr: parseFloat(brokeragePerLot),
        slippage_ticks_base: parseFloat(slippageTicksBase),
        slippage_ticks_quote: parseFloat(slippageTicksQuote),
        expiry_lockout_days: parseInt(expiryLockoutDays),
        min_volume_lots: parseInt(minVolumeLots),
        min_open_interest: parseInt(minOpenInterest),
        train_ratio: parseFloat(trainRatio),
        val_ratio: parseFloat(valRatio),
        walk_forward: walkForward,
        train_window_days: parseInt(trainWindowDays),
        test_window_days: parseInt(testWindowDays),
        capital: parseFloat(capital),
      });
      setResult(res.data);
    } catch (err) {
      setError(err.message || 'Backtest simulation execution failed.');
    } finally {
      setRunning(false);
    }
  };

  const executeSensitivity = async () => {
    try {
      setRunningSensitivity(true);
      const res = await endpoints.runSensitivity({ pair_name: pairName, capital: parseFloat(capital) });
      setSensitivityResult(res.data);
      setActiveTab('sensitivity');
    } catch (err) {
      setError(err.message || 'Sensitivity analysis execution failed.');
    } finally {
      setRunningSensitivity(false);
    }
  };

  useEffect(() => {
    executeBacktest();
  }, []);

  // CSV Export Handlers
  const handleExportTradesCSV = () => {
    if (!result?.id) return;
    window.open(endpoints.getTradesCsvUrl(result.id), '_blank');
  };

  const handleExportEquityCSV = () => {
    if (!result?.id) return;
    window.open(endpoints.getEquityCsvUrl(result.id), '_blank');
  };

  // Equity Curve Traces - Net vs Gross vs Gold Benchmark
  const dates = result?.equity_curve?.map((p) => p.date) || [];
  const netEquities = result?.equity_curve?.map((p) => p.equity) || [];
  const grossEquities = result?.equity_curve?.map((p) => p.gross_equity ?? p.equity) || [];
  const benchEquities = result?.equity_curve?.map((p) => p.benchmark_equity ?? capital) || [];
  const initialCapLine = dates.map(() => capital);

  const netEquityTrace = {
    x: dates,
    y: netEquities,
    name: 'Strategy Net Equity (Post Costs & Slippage)',
    type: 'scatter',
    mode: 'lines',
    line: { color: '#10b981', width: 2.5 },
  };

  const grossEquityTrace = {
    x: dates,
    y: grossEquities,
    name: 'Strategy Gross Equity (Zero Friction Reference)',
    type: 'scatter',
    mode: 'lines',
    line: { color: '#06b6d4', width: 1.5, dash: 'dot' },
  };

  const benchmarkTrace = {
    x: dates,
    y: benchEquities,
    name: 'Gold Benchmark Buy-and-Hold',
    type: 'scatter',
    mode: 'lines',
    line: { color: '#eab308', width: 1.5, dash: 'dash' },
  };

  const benchmarkCapTrace = {
    x: dates,
    y: initialCapLine,
    name: 'Initial Capital Reference',
    type: 'scatter',
    mode: 'lines',
    line: { color: 'rgba(255, 255, 255, 0.25)', dash: 'dash', width: 1 },
  };

  // Drawdown Underwater Series
  let peak = capital;
  const drawdowns = netEquities.map((eq) => {
    if (eq > peak) peak = eq;
    return ((eq - peak) / peak) * 100.0;
  });

  const drawdownTrace = {
    x: dates,
    y: drawdowns,
    name: 'Net Drawdown (%)',
    type: 'scatter',
    fill: 'tozeroy',
    fillcolor: 'rgba(244, 63, 94, 0.2)',
    line: { color: '#f43f5e', width: 1.5 },
  };

  return (
    <div className="space-y-6">
      {/* Strategy Setup Card */}
      <Card>
        <CardHeader
          title="MCX Gold Relative Value — Walk-Forward Backtesting Engine"
          subtitle="Test whether relative-value opportunities remain profitable after modeled transaction costs, slippage, and expiry lockouts without look-ahead bias"
          action={
            <div className="flex items-center gap-2">
              <button
                onClick={executeSensitivity}
                disabled={runningSensitivity || running}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-all disabled:opacity-50"
              >
                <Sliders size={13} className={runningSensitivity ? 'animate-spin text-gold-400' : ''} />
                <span>{runningSensitivity ? 'Analyzing Grid...' : 'Sensitivity Grid'}</span>
              </button>
              <button
                onClick={executeBacktest}
                disabled={running || runningSensitivity}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 text-xs font-bold transition-all shadow-md disabled:opacity-50"
              >
                <Play size={14} className={running ? 'animate-spin' : ''} />
                <span>{running ? 'Simulating Fills...' : 'Run Simulation'}</span>
              </button>
            </div>
          }
        />

        {/* Primary Parameter Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3.5 pt-2 text-xs">
          <div>
            <label className="text-slate-400 font-mono block mb-1">Contract Pair</label>
            <select
              value={pairName}
              onChange={(e) => setPairName(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-medium focus:border-gold-500 focus:outline-none"
            >
              {PAIRS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Entry Threshold (Z-Score)</label>
            <input
              type="number"
              step="0.1"
              value={entryZ}
              onChange={(e) => setEntryZ(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Exit Threshold (Z-Score)</label>
            <input
              type="number"
              step="0.1"
              value={exitZ}
              onChange={(e) => setExitZ(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Stop-Loss (Z-Score)</label>
            <input
              type="number"
              step="0.1"
              value={stopLossZ}
              onChange={(e) => setStopLossZ(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Expiry Lockout Window</label>
            <div className="flex items-center gap-1.5">
              <input
                type="number"
                min="1"
                max="20"
                value={expiryLockoutDays}
                onChange={(e) => setExpiryLockoutDays(e.target.value)}
                className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
              />
              <span className="text-[11px] text-slate-500 font-mono shrink-0">days</span>
            </div>
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Initial Capital (INR)</label>
            <input
              type="number"
              step="100000"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Advanced Execution & Liquidity Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3.5 pt-3 border-t border-white/5 mt-3 text-xs">
          <div>
            <label className="text-slate-400 font-mono block mb-1">Base Slippage (Ticks)</label>
            <input
              type="number"
              step="0.5"
              min="0"
              value={slippageTicksBase}
              onChange={(e) => setSlippageTicksBase(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Quote Slippage (Ticks)</label>
            <input
              type="number"
              step="0.5"
              min="0"
              value={slippageTicksQuote}
              onChange={(e) => setSlippageTicksQuote(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Brokerage (₹/Lot)</label>
            <input
              type="number"
              step="5"
              min="0"
              value={brokeragePerLot}
              onChange={(e) => setBrokeragePerLot(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Min Volume Filter</label>
            <input
              type="number"
              step="10"
              min="0"
              value={minVolumeLots}
              onChange={(e) => setMinVolumeLots(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 font-mono block mb-1">Min Open Interest</label>
            <input
              type="number"
              step="50"
              min="0"
              value={minOpenInterest}
              onChange={(e) => setMinOpenInterest(e.target.value)}
              className="w-full bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1.5 text-white font-mono focus:border-gold-500 focus:outline-none"
            />
          </div>

          <div className="flex flex-col justify-end gap-1.5">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="carryCheck"
                checked={useCarryAdj}
                onChange={(e) => setUseCarryAdj(e.target.checked)}
                className="rounded bg-navy-900 border-white/20 text-gold-500 focus:ring-0"
              />
              <label htmlFor="carryCheck" className="text-slate-300 font-medium cursor-pointer text-[11px]">
                Carry Adjusted Spread
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="costCheck"
                checked={includeCosts}
                onChange={(e) => setIncludeCosts(e.target.checked)}
                className="rounded bg-navy-900 border-white/20 text-gold-500 focus:ring-0"
              />
              <label htmlFor="costCheck" className="text-slate-300 font-medium cursor-pointer text-[11px]">
                Include MCX Taxes & CTT
              </label>
            </div>
          </div>
        </div>

        {/* Validation Partition Mode Toggle */}
        <div className="mt-3.5 pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <span className="text-slate-400 font-mono">Validation Framework:</span>
            <button
              onClick={() => setWalkForward(false)}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all border ${
                !walkForward
                  ? 'bg-gold-500/20 text-gold-400 border-gold-500/40 shadow-sm'
                  : 'bg-navy-900 text-slate-400 border-white/10 hover:text-white'
              }`}
            >
              3-Way Chronological Split (Train / Val / Out-of-Sample Test)
            </button>
            <button
              onClick={() => setWalkForward(true)}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all border ${
                walkForward
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 shadow-sm'
                  : 'bg-navy-900 text-slate-400 border-white/10 hover:text-white'
              }`}
            >
              Rolling Walk-Forward Multi-Fold
            </button>
          </div>

          {walkForward ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 font-mono">Train Window:</span>
                <input
                  type="number"
                  value={trainWindowDays}
                  onChange={(e) => setTrainWindowDays(e.target.value)}
                  className="w-14 bg-navy-900 border border-white/10 rounded px-2 py-0.5 text-white font-mono text-center"
                />
                <span className="text-slate-400">d</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400 font-mono">Test Window:</span>
                <input
                  type="number"
                  value={testWindowDays}
                  onChange={(e) => setTestWindowDays(e.target.value)}
                  className="w-14 bg-navy-900 border border-white/10 rounded px-2 py-0.5 text-white font-mono text-center"
                />
                <span className="text-slate-400">d</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-slate-400 font-mono text-[11px]">
              <span>Train: 50%</span>
              <span>&bull;</span>
              <span>Validation: 25%</span>
              <span>&bull;</span>
              <span className="text-emerald-400 font-bold">Out-of-Sample Test: 25%</span>
            </div>
          )}
        </div>
      </Card>

      {error && <ErrorAlert message={error} onRetry={executeBacktest} />}

      {/* Primary Performance KPIs - Gross & Net Reported Separately */}
      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          <MetricCard
            title="Net Return"
            value={formatPercent(result.total_return_pct)}
            subvalue={`Gross: ${formatPercent(result.gross_total_return_pct ?? result.total_return_pct)}`}
            isPositiveGood={true}
            badgeColor={result.total_return_pct >= 0 ? 'emerald' : 'rose'}
          />
          <MetricCard
            title="Net Realized PnL"
            value={formatINR(result.net_pnl_inr ?? 0)}
            subvalue={`Gross PnL: ${formatINR(result.gross_pnl_inr ?? 0)}`}
            badgeColor="emerald"
          />
          <MetricCard
            title="Gold Benchmark & Beta"
            value={result.gold_beta !== null ? `β = ${result.gold_beta}` : 'β = 0.00'}
            subvalue={`Gold B&H Return: ${formatPercent(result.benchmark_return_pct ?? 0)}`}
            badgeColor={result.gold_beta !== null && Math.abs(result.gold_beta) <= 0.15 ? 'emerald' : 'gold'}
            badgeText={result.gold_beta !== null && Math.abs(result.gold_beta) <= 0.15 ? 'Market-Neutral' : 'Correlated'}
          />
          <MetricCard
            title="Sharpe / Sortino"
            value={`${result.sharpe_ratio.toFixed(2)} / ${result.sortino_ratio ? result.sortino_ratio.toFixed(2) : '—'}`}
            subvalue={`Calmar: ${result.calmar_ratio ? result.calmar_ratio.toFixed(2) : '—'}`}
            badgeColor="cyan"
          />
          <MetricCard
            title="Max Drawdown"
            value={`${result.max_drawdown_pct}%`}
            subvalue={`Win Rate: ${result.win_rate_pct}% (${result.winning_trades}W / ${result.total_trades}T)`}
            badgeColor="rose"
          />
          <MetricCard
            title="Friction & Turnover"
            value={formatINR(result.total_fees_paid)}
            subvalue={`Turnover: ${formatINR(result.turnover_inr ?? 0)} • Hold: ${result.avg_holding_days}d`}
            badgeColor="gold"
          />
        </div>
      )}

      {/* Chronological Split Breakdown Cards (when 3-way split active) */}
      {result?.split_metrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-navy-900 border border-white/5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-mono text-slate-400">1. In-Sample Training</span>
              <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">50% Window</span>
            </div>
            <p className="text-lg font-bold font-mono text-white">
              {formatPercent(result.split_metrics.training?.net_return_pct ?? 0)}
            </p>
            <p className="text-xs text-slate-400 font-mono">
              {formatDate(result.split_metrics.training?.start)} &rarr; {formatDate(result.split_metrics.training?.end)} &bull; {result.split_metrics.training?.trades} trades
            </p>
          </div>

          <div className="p-4 rounded-xl bg-navy-900 border border-white/5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-mono text-slate-400">2. Validation Set</span>
              <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded font-mono">25% Window</span>
            </div>
            <p className="text-lg font-bold font-mono text-cyan-400">
              {formatPercent(result.split_metrics.validation?.net_return_pct ?? 0)}
            </p>
            <p className="text-xs text-slate-400 font-mono">
              {formatDate(result.split_metrics.validation?.start)} &rarr; {formatDate(result.split_metrics.validation?.end)} &bull; {result.split_metrics.validation?.trades} trades
            </p>
          </div>

          <div className="p-4 rounded-xl bg-navy-900 border border-emerald-500/30 bg-gradient-to-br from-emerald-500/5 to-navy-900 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-mono text-emerald-400 font-bold">3. Out-of-Sample Test</span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-mono">25% Final Test</span>
            </div>
            <p className="text-lg font-bold font-mono text-emerald-400">
              {formatPercent(result.split_metrics.out_of_sample_test?.net_return_pct ?? 0)}
            </p>
            <p className="text-xs text-slate-400 font-mono">
              {formatDate(result.split_metrics.out_of_sample_test?.start)} &rarr; {formatDate(result.split_metrics.out_of_sample_test?.end)} &bull; {result.split_metrics.out_of_sample_test?.trades} trades
            </p>
          </div>
        </div>
      )}

      {/* Tabs Bar: Performance, Sensitivity, Trade Ledger */}
      <div className="flex items-center justify-between border-b border-white/10 pb-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('performance')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'performance'
                ? 'bg-gold-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Equity &amp; Benchmark Charts
          </button>
          <button
            onClick={() => setActiveTab('sensitivity')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'sensitivity'
                ? 'bg-gold-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sensitivity Grid ({sensitivityResult ? 'Ready' : 'Simulate'})
          </button>
          <button
            onClick={() => setActiveTab('trades')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'trades'
                ? 'bg-gold-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Executed Trade Ledger ({result?.trades?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('assumptions')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'assumptions'
                ? 'bg-gold-500 text-navy-950 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Model Assumptions &amp; Limitations
          </button>
        </div>

        {/* CSV Export Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportTradesCSV}
            disabled={!result?.id}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-colors disabled:opacity-50"
          >
            <Download size={13} />
            <span>Export Trades CSV</span>
          </button>
          <button
            onClick={handleExportEquityCSV}
            disabled={!result?.id}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-colors disabled:opacity-50"
          >
            <Download size={13} />
            <span>Export Equity CSV</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Performance Charts */}
      {activeTab === 'performance' && (
        <div className="space-y-6">
          {/* Equity Curve vs Benchmark */}
          <Card>
            <CardHeader
              title="Portfolio Equity Trajectory (₹) vs Gold Benchmark Buy-and-Hold"
              subtitle="Directly compares Strategy Net Equity (post MCX brokerage, CTT, GST, and execution slippage) against Gross Theoretical Returns and Gold Buy-and-Hold Benchmark"
            />
            <div className="h-[340px]">
              <PlotlyChart
                data={[benchmarkCapTrace, benchmarkTrace, grossEquityTrace, netEquityTrace]}
                layout={{
                  height: 340,
                  yaxis: { title: 'Portfolio Equity (₹)', tickprefix: '₹' },
                  legend: { orientation: 'h', y: -0.2 },
                }}
              />
            </div>
          </Card>

          {/* Drawdown Chart */}
          <Card>
            <CardHeader
              title="Strategy Underwater Drawdown Curve"
              subtitle="Quantifies duration and peak-to-trough equity degradation"
            />
            <div className="h-[220px]">
              <PlotlyChart
                data={[drawdownTrace]}
                layout={{
                  height: 220,
                  yaxis: { title: 'Net Drawdown (%)', ticksuffix: '%' },
                }}
              />
            </div>
          </Card>

          {/* Walk-Forward Folds Breakdown (if walk-forward mode) */}
          {result?.walk_forward && result?.walk_forward_metrics?.length > 0 && (
            <Card>
              <CardHeader
                title="Walk-Forward Out-of-Sample Validation Folds"
                subtitle="Parameters calibrated strictly on in-sample train window and tested forward on unseen out-of-sample periods"
              />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Fold #</th>
                      <th className="py-2.5 px-3">In-Sample Train Range</th>
                      <th className="py-2.5 px-3">In-Sample Return</th>
                      <th className="py-2.5 px-3">Out-of-Sample Test Range</th>
                      <th className="py-2.5 px-3">OOS Trades</th>
                      <th className="py-2.5 px-3">OOS Sharpe</th>
                      <th className="py-2.5 px-3 text-right">OOS Return (%)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {result.walk_forward_metrics.map((f) => (
                      <tr key={f.fold} className="hover:bg-white/[0.02]">
                        <td className="py-2.5 px-3 text-gold-400 font-bold">Fold {f.fold}</td>
                        <td className="py-2.5 px-3 text-slate-300">{formatDate(f.train_start)} &rarr; {formatDate(f.train_end)}</td>
                        <td className="py-2.5 px-3 text-slate-400">{formatPercent(f.in_sample_return_pct)}</td>
                        <td className="py-2.5 px-3 text-slate-300">{formatDate(f.test_start)} &rarr; {formatDate(f.test_end)}</td>
                        <td className="py-2.5 px-3 text-slate-400">{f.out_of_sample_trades}</td>
                        <td className="py-2.5 px-3 text-slate-400">{f.out_of_sample_sharpe.toFixed(2)}</td>
                        <td className={`py-2.5 px-3 text-right font-bold ${f.out_of_sample_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {formatPercent(f.out_of_sample_return_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Tab 2: Sensitivity Analysis Grid */}
      {activeTab === 'sensitivity' && (
        <div className="space-y-6">
          {!sensitivityResult ? (
            <Card className="text-center py-12">
              <Sliders size={32} className="mx-auto text-slate-600 mb-2" />
              <h4 className="text-sm font-semibold text-slate-300">Sensitivity Analysis Not Yet Executed</h4>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                Click &ldquo;Run Sensitivity Grid&rdquo; to simulate strategy sensitivity across slippage, cost multipliers, entry thresholds, and carry rates.
              </p>
              <button
                onClick={executeSensitivity}
                disabled={runningSensitivity}
                className="mt-4 px-4 py-2 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 text-xs font-bold transition-all shadow-md"
              >
                {runningSensitivity ? 'Running Grid...' : 'Run Sensitivity Analysis'}
              </button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Slippage Sensitivity Table */}
              <Card>
                <CardHeader
                  title="Slippage Sensitivity (0.0 to 3.0 Ticks)"
                  subtitle="Impact of execution fill drag on strategy net profitability"
                />
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Slippage</th>
                        <th className="py-2 px-3">Gross Ret</th>
                        <th className="py-2 px-3">Sharpe</th>
                        <th className="py-2 px-3">Total Fees</th>
                        <th className="py-2 px-3 text-right">Net Return</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {sensitivityResult.slippage_sensitivity.map((s, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="py-2 px-3 text-gold-400 font-bold">{s.parameter_value}</td>
                          <td className="py-2 px-3 text-slate-400">{formatPercent(s.gross_return_pct)}</td>
                          <td className="py-2 px-3 text-slate-300">{s.sharpe_ratio.toFixed(2)}</td>
                          <td className="py-2 px-3 text-slate-400">{formatINR(s.total_fees_inr)}</td>
                          <td className={`py-2 px-3 text-right font-bold ${s.net_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {formatPercent(s.net_return_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Cost Multiplier Sensitivity Table */}
              <Card>
                <CardHeader
                  title="Transaction Cost Sensitivity (0.5x to 2.0x)"
                  subtitle="Robustness to statutory fee, tax, and brokerage fee increases"
                />
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Multiplier</th>
                        <th className="py-2 px-3">Sharpe</th>
                        <th className="py-2 px-3">Drawdown</th>
                        <th className="py-2 px-3">Total Fees</th>
                        <th className="py-2 px-3 text-right">Net Return</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {sensitivityResult.cost_sensitivity.map((s, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="py-2 px-3 text-cyan-400 font-bold">{s.parameter_value}</td>
                          <td className="py-2 px-3 text-slate-300">{s.sharpe_ratio.toFixed(2)}</td>
                          <td className="py-2 px-3 text-rose-400">{s.max_drawdown_pct}%</td>
                          <td className="py-2 px-3 text-slate-400">{formatINR(s.total_fees_inr)}</td>
                          <td className={`py-2 px-3 text-right font-bold ${s.net_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {formatPercent(s.net_return_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Threshold Sensitivity Table */}
              <Card>
                <CardHeader
                  title="Entry Z-Score Sensitivity (1.5σ to 3.0σ)"
                  subtitle="Tradeoff between trade selectivity and sample frequency"
                />
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Threshold</th>
                        <th className="py-2 px-3">Trades</th>
                        <th className="py-2 px-3">Win Rate</th>
                        <th className="py-2 px-3">Sharpe</th>
                        <th className="py-2 px-3 text-right">Net Return</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {sensitivityResult.threshold_sensitivity.map((s, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="py-2 px-3 text-gold-400 font-bold">{s.parameter_value}</td>
                          <td className="py-2 px-3 text-slate-300">{s.total_trades}</td>
                          <td className="py-2 px-3 text-slate-300">{s.win_rate_pct}%</td>
                          <td className="py-2 px-3 text-slate-300">{s.sharpe_ratio.toFixed(2)}</td>
                          <td className={`py-2 px-3 text-right font-bold ${s.net_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {formatPercent(s.net_return_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Carry Rate Sensitivity Table */}
              <Card>
                <CardHeader
                  title="Carry Rate Sensitivity (5.0% to 9.0% p.a.)"
                  subtitle="Sensitivity to macro interest rate shifts and storage costs"
                />
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Carry Rate</th>
                        <th className="py-2 px-3">Trades</th>
                        <th className="py-2 px-3">Sharpe</th>
                        <th className="py-2 px-3">Drawdown</th>
                        <th className="py-2 px-3 text-right">Net Return</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {sensitivityResult.carry_rate_sensitivity.map((s, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="py-2 px-3 text-emerald-400 font-bold">{s.parameter_value}</td>
                          <td className="py-2 px-3 text-slate-300">{s.total_trades}</td>
                          <td className="py-2 px-3 text-slate-300">{s.sharpe_ratio.toFixed(2)}</td>
                          <td className="py-2 px-3 text-rose-400">{s.max_drawdown_pct}%</td>
                          <td className={`py-2 px-3 text-right font-bold ${s.net_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {formatPercent(s.net_return_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Executed Trade Ledger */}
      {activeTab === 'trades' && (
        <Card>
          <CardHeader
            title={`Executed Trade Ledger (${result?.trades?.length || 0} Pairs Executed)`}
            subtitle="Detailed entry and exit executions distinguishing observed settlement quotes from modeled fills (with per-leg slippage and statutory friction)"
            action={
              <button
                onClick={handleExportTradesCSV}
                disabled={!result?.id}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-colors disabled:opacity-50"
              >
                <Download size={13} />
                <span>Export Ledger CSV</span>
              </button>
            }
          />
          <div className="overflow-x-auto max-h-[460px]">
            <table className="w-full text-left text-xs font-mono">
              <thead className="sticky top-0 bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                <tr>
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Position</th>
                  <th className="py-2.5 px-3">Phase</th>
                  <th className="py-2.5 px-3">Dates</th>
                  <th className="py-2.5 px-3">Lots</th>
                  <th className="py-2.5 px-3">Base (Settle &rarr; Fill)</th>
                  <th className="py-2.5 px-3">Quote (Settle &rarr; Fill)</th>
                  <th className="py-2.5 px-3">Gross PnL</th>
                  <th className="py-2.5 px-3">Total Costs</th>
                  <th className="py-2.5 px-3 text-right">Net PnL (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {result?.trades?.map((t) => {
                  const isProfitable = t.net_pnl_inr > 0;
                  return (
                    <tr key={t.trade_id} className="hover:bg-white/[0.02]">
                      <td className="py-2.5 px-3 text-slate-500">{t.trade_id}</td>
                      <td className="py-2.5 px-3 font-semibold">
                        <span
                          className={
                            t.position_type === 'LONG_SPREAD'
                              ? 'text-emerald-400'
                              : 'text-rose-400'
                          }
                        >
                          {t.position_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          t.split_phase === 'TEST' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                          t.split_phase === 'VALIDATION' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' :
                          'bg-slate-800 text-slate-300'
                        }`}>
                          {t.split_phase ?? 'FULL'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                        {formatDate(t.entry_date)} &rarr; {formatDate(t.exit_date)} ({t.holding_days}d)
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {t.lots_base}B / {t.lots_quote}Q
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                        ₹{t.entry_base_settle} &rarr; <span className="text-gold-400 font-bold">₹{t.entry_base_fill}</span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                        ₹{t.entry_quote_settle} &rarr; <span className="text-gold-400 font-bold">₹{t.entry_quote_fill}</span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 font-semibold">{formatINR(t.gross_pnl_inr)}</td>
                      <td className="py-2.5 px-3 text-slate-500">{formatINR(t.total_fees_inr)}</td>
                      <td
                        className={`py-2.5 px-3 text-right font-bold ${
                          isProfitable ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {formatINR(t.net_pnl_inr)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tab 4: Model Assumptions & Limitations */}
      {activeTab === 'assumptions' && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Quantitative Framework Assumptions & Methodological Guardrails"
              subtitle="Explicit parameters, execution fill mechanics, and regulatory boundaries governing the backtesting engine"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-navy-850 border border-white/5 space-y-2">
                <div className="flex items-center gap-2 text-white font-bold">
                  <ShieldCheck size={16} className="text-emerald-400" />
                  <span>1. Zero Look-Ahead Bias Guarantee</span>
                </div>
                <p className="text-slate-300 leading-relaxed font-sans">
                  All statistical indicators (20-day rolling mean $\mu_t$, rolling standard deviation $\sigma_t$, and Z-scores $Z_t$) are computed strictly over backward-looking windows $[t-W+1, t]$. Future spread observations, future volatility, and future expiries are strictly inaccessible to the strategy at decision time $t$.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-navy-850 border border-white/5 space-y-2">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Activity size={16} className="text-cyan-400" />
                  <span>2. Modeled Fills vs. Settlement Quotes</span>
                </div>
                <p className="text-slate-300 leading-relaxed font-sans">
                  Bhavcopy reports official exchange closing settlement prices. Actual market execution incurs bid-ask friction. The engine applies {slippageTicksBase} tick slippage to the base leg and {slippageTicksQuote} tick slippage to the quote leg on both entry and exit legs, preventing idealized zero-slippage assumptions.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-navy-850 border border-white/5 space-y-2">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Split size={16} className="text-gold-400" />
                  <span>3. Metal Delta-Neutral Position Sizing</span>
                </div>
                <p className="text-slate-300 leading-relaxed font-sans">
                  Contract sizing accounts for both trading units and chemical fineness. For example, 1 lot of GOLDM (100g @ 995 fineness = 99.5g pure gold) is delta-hedged against exactly 100 lots of GOLDPETAL (100 x 1g @ 999 fineness = 99.9g pure gold). Positions are not sized on nominal lot counts alone.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-navy-850 border border-white/5 space-y-2">
                <div className="flex items-center gap-2 text-white font-bold">
                  <Lock size={16} className="text-rose-400" />
                  <span>4. Physical Tender Delivery Lockout (T-5)</span>
                </div>
                <p className="text-slate-300 leading-relaxed font-sans">
                  MCX Gold contracts require compulsory physical vault delivery upon expiry. The engine enforces a strict {expiryLockoutDays}-day pre-expiry lockout preventing new entries. If a held position reaches 1 day to expiry, a mandatory forced exit is executed (<code className="text-rose-400">FORCED_EXPIRY_EXIT</code>).
                </p>
              </div>
            </div>
          </Card>

          {/* Statutory MCX Fee Schedule Card */}
          <Card>
            <CardHeader
              title="MCX Statutory Transaction Cost Schedule"
              subtitle="Itemized statutory levies deducted on every simulated transaction"
            />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400 uppercase text-[11px]">
                    <th className="py-2.5 px-3">Levy / Cost Component</th>
                    <th className="py-2.5 px-3">Applicable Rate</th>
                    <th className="py-2.5 px-3">Application Basis</th>
                    <th className="py-2.5 px-3">Turnover Impact</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  <tr>
                    <td className="py-2 px-3 text-white font-bold">Brokerage</td>
                    <td className="py-2 px-3 text-gold-400">₹{brokeragePerLot} / lot</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">Both Entry &amp; Exit legs</td>
                    <td className="py-2 px-3 text-slate-300">Flat per executed contract</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 text-white font-bold">Exchange Turnover Fee</td>
                    <td className="py-2 px-3 text-gold-400">0.0021%</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">Both Entry &amp; Exit turnover</td>
                    <td className="py-2 px-3 text-slate-300">2.1 bps per leg (4.2 bps roundtrip)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 text-white font-bold">SEBI Regulatory Turnover Fee</td>
                    <td className="py-2 px-3 text-gold-400">0.0001%</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">Both Entry &amp; Exit turnover</td>
                    <td className="py-2 px-3 text-slate-300">0.1 bps per leg (0.2 bps roundtrip)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 text-white font-bold">Commodities Transaction Tax (CTT)</td>
                    <td className="py-2 px-3 text-rose-400">0.0100%</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">Sell side turnover ONLY</td>
                    <td className="py-2 px-3 text-slate-300">10.0 bps on short leg executions</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 text-white font-bold">Stamp Duty</td>
                    <td className="py-2 px-3 text-cyan-400">0.0020%</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">Buy side turnover ONLY</td>
                    <td className="py-2 px-3 text-slate-300">2.0 bps on long leg executions</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 text-white font-bold">Goods &amp; Services Tax (GST)</td>
                    <td className="py-2 px-3 text-gold-400">18.00%</td>
                    <td className="py-2 px-3 text-slate-400 font-sans">On (Brokerage + Exchange + SEBI fees)</td>
                    <td className="py-2 px-3 text-slate-300">Statutory tax component</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>

          {/* Model Limitations & Disclaimers */}
          <Card className="border-amber-500/20 bg-amber-500/5">
            <div className="flex items-start gap-3">
              <ShieldAlert className="text-amber-400 shrink-0 mt-0.5" size={20} />
              <div className="space-y-1 text-xs text-amber-200/90 font-sans leading-relaxed">
                <span className="font-bold text-amber-300 uppercase tracking-wide block">
                  Methodological Limitations &amp; Model Risk
                </span>
                <p>
                  1. <strong>Intraday Volatility:</strong> The simulation uses end-of-day daily Bhavcopy settlement quotes. Intraday price spikes, limit up/down halts, or temporary spread blowouts between daily sessions cannot be fully captured.
                </p>
                <p>
                  2. <strong>Market Depth &amp; Liquidity:</strong> Large orders in real market conditions may experience price impact beyond modeled slippage. Users should verify live order book depth before deploying relative-value strategies.
                </p>
                <p>
                  3. <strong>Analytical Nature:</strong> Backtested performance is hypothetical, conducted solely for research and analytics. It does not constitute investment advice or a solicitation to execute real commodity futures transactions.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

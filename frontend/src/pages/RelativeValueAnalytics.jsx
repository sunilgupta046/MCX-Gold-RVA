import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  Sliders,
  Scale,
  Activity,
  Layers,
  ArrowRightLeft,
  Percent,
  Compass,
  Info,
  BarChart2,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { MetricCard } from '../components/MetricCard';
import { PlotlyChart } from '../components/PlotlyChart';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatINR, formatNumber, formatBps, formatPercent } from '../utils/formatters';
import { PAIRS, CONTRACTS } from '../utils/constants';

export const RelativeValueAnalytics = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPair, setSelectedPair] = useState('GOLDM_vs_GOLDPETAL');
  const [useCarryAdj, setUseCarryAdj] = useState(true);
  const [use999Purity, setUse999Purity] = useState(true);
  const [timeframe, setTimeframe] = useState('ALL');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  const [spreadData, setSpreadData] = useState([]);
  const [corrMatrix, setCorrMatrix] = useState(null);
  const [carryCurve, setCarryCurve] = useState(null);
  const [termStructure, setTermStructure] = useState(null);
  const [volOISymbol, setVolOISymbol] = useState('GOLDM');
  const [volOIData, setVolOIData] = useState(null);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = { pair_name: selectedPair, limit: 500 };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const [spreadsRes, corrRes, carryRes, tsRes, volRes] = await Promise.all([
        endpoints.getSpreadAnalytics(params),
        endpoints.getCorrelationMatrix(),
        endpoints.getCarryCurve(),
        endpoints.getTermStructure(),
        endpoints.getVolumeOI({ symbol: volOISymbol }),
      ]);

      let data = spreadsRes.data || [];
      if (timeframe !== 'ALL' && data.length > 0) {
        const daysMap = { '1M': 30, '3M': 90, '6M': 180 };
        const days = daysMap[timeframe] || 365;
        const lastDate = new Date(data[data.length - 1].trade_date);
        const cutoff = new Date(lastDate);
        cutoff.setDate(cutoff.getDate() - days);
        data = data.filter((d) => new Date(d.trade_date) >= cutoff);
      }

      setSpreadData(data);
      setCorrMatrix(corrRes.data);
      setCarryCurve(carryRes.data);
      setTermStructure(tsRes.data);
      setVolOIData(volRes.data);
    } catch (err) {
      setError(err.message || 'Failed to load relative value analytics.');
    } finally {
      setLoading(false);
    }
  };

  const loadVolOI = async (sym) => {
    try {
      setVolOISymbol(sym);
      const res = await endpoints.getVolumeOI({ symbol: sym });
      setVolOIData(res.data);
    } catch (err) {
      console.error('Failed to load Volume/OI data:', err);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [selectedPair, timeframe, startDate, endDate]);

  if (loading && spreadData.length === 0) {
    return <LoadingSpinner text="Calculating 999-purity carry-adjusted spreads and term structures..." fullScreen />;
  }
  if (!loading && !error && spreadData.length === 0) {
    return (
      <Card>
        <CardHeader
          title="No relative-value data available"
          subtitle="Import MCX Bhavcopy records before viewing spread analytics."
        />
        <p className="text-xs text-slate-400">
          Use Bhavcopy Ingestion to upload official settlement data, or use the Admin Panel demo generator
          for clearly labeled synthetic test data.
        </p>
      </Card>
    );
  }

  // Active pair latest metric values
  const latestMetric = spreadData.length > 0 ? spreadData[spreadData.length - 1] : null;
  const selectedPairConfig = PAIRS.find((pair) => pair.id === selectedPair);
  const baseIndex = corrMatrix?.contracts?.indexOf(selectedPairConfig?.base) ?? -1;
  const quoteIndex = corrMatrix?.contracts?.indexOf(selectedPairConfig?.quote) ?? -1;
  const pairCorrelation =
    baseIndex >= 0 && quoteIndex >= 0
      ? corrMatrix?.matrix?.[baseIndex]?.[quoteIndex]
      : null;
  const hasPairCorrelation = Number.isFinite(pairCorrelation);
  
  // Decide spread value based on purity & carry toggles
  const getSpreadValue = (metric) => {
    if (!metric) return 0;
    if (use999Purity) {
      return useCarryAdj
        ? (metric.carry_adjusted_spread_pure_10g ?? metric.carry_adjusted_spread_per_10g)
        : (metric.normalized_spread_per_pure_10g_999 ?? metric.raw_spread_per_10g);
    }
    return useCarryAdj ? metric.carry_adjusted_spread_per_10g : metric.raw_spread_per_10g;
  };

  const currentSpread = getSpreadValue(latestMetric);

  // Chart 1: Spread Series & Reversion Bands
  const dates = spreadData.map((d) => d.trade_date);
  const spreadValues = spreadData.map((d) => getSpreadValue(d));
  const means = spreadData.map((d) => d.rolling_mean_20d);
  const upperBands2 = spreadData.map((d) => (d.rolling_mean_20d !== null && d.rolling_std_20d ? d.rolling_mean_20d + 2 * d.rolling_std_20d : null));
  const lowerBands2 = spreadData.map((d) => (d.rolling_mean_20d !== null && d.rolling_std_20d ? d.rolling_mean_20d - 2 * d.rolling_std_20d : null));

  const spreadChartTraces = [
    {
      x: dates,
      y: upperBands2,
      name: '+2.0σ Upper Threshold',
      type: 'scatter',
      mode: 'lines',
      line: { color: 'rgba(244, 63, 94, 0.4)', dash: 'dot', width: 1.5 },
    },
    {
      x: dates,
      y: means,
      name: '20-Day Rolling Mean',
      type: 'scatter',
      mode: 'lines',
      line: { color: 'rgba(255, 255, 255, 0.4)', dash: 'dash', width: 1.5 },
    },
    {
      x: dates,
      y: lowerBands2,
      name: '-2.0σ Lower Threshold',
      type: 'scatter',
      mode: 'lines',
      line: { color: 'rgba(16, 185, 129, 0.4)', dash: 'dot', width: 1.5 },
    },
    {
      x: dates,
      y: spreadValues,
      name: `${use999Purity ? '999 Pure' : 'Unadjusted'} ${useCarryAdj ? 'Carry-Adj' : 'Raw'} Spread (₹/10g)`,
      type: 'scatter',
      mode: 'lines',
      line: { color: '#eab308', width: 2.5 },
    },
  ];

  // Chart 2: Z-Score Oscillator
  const zScores = spreadData.map((d) => d.z_score);
  const zScoreTraces = [
    {
      x: dates,
      y: zScores,
      name: 'Z-Score (σ)',
      type: 'scatter',
      mode: 'lines',
      line: { color: '#06b6d4', width: 2 },
    },
  ];

  const zScoreLayout = {
    height: 220,
    margin: { l: 55, r: 25, t: 15, b: 35 },
    yaxis: {
      title: 'Z-Score (σ)',
      zerolinecolor: 'rgba(255, 255, 255, 0.3)',
      zerolinewidth: 1,
    },
    shapes: [
      {
        type: 'line',
        x0: dates[0],
        x1: dates[dates.length - 1],
        y0: 2,
        y1: 2,
        line: { color: '#f43f5e', width: 1, dash: 'dash' },
      },
      {
        type: 'line',
        x0: dates[0],
        x1: dates[dates.length - 1],
        y0: -2,
        y1: -2,
        line: { color: '#10b981', width: 1, dash: 'dash' },
      },
    ],
  };

  // Correlation Heatmap Trace
  const heatmapTrace = corrMatrix
    ? [
        {
          z: corrMatrix.matrix,
          x: corrMatrix.contracts.map((_, index) => index),
          y: corrMatrix.contracts.map((_, index) => index),
          type: 'heatmap',
          colorscale: [
            [0, '#0a0f1d'],
            [0.5, '#1e293b'],
            [0.9, '#ca8a04'],
            [1, '#eab308'],
          ],
          showscale: true,
        },
      ]
    : [];

  // Volume & OI Chart Traces
  const volSeries = volOIData?.series || [];
  const volDates = volSeries.map((s) => s.trade_date);
  const volLots = volSeries.map((s) => s.volume_lots);
  const oiValues = volSeries.map((s) => s.open_interest);

  const volOITraces = [
    {
      x: volDates,
      y: volLots,
      name: 'Daily Volume (Lots)',
      type: 'bar',
      marker: { color: 'rgba(6, 182, 212, 0.45)' },
      yaxis: 'y',
    },
    {
      x: volDates,
      y: oiValues,
      name: 'Open Interest (Lots)',
      type: 'scatter',
      mode: 'lines',
      line: { color: '#eab308', width: 2 },
      yaxis: 'y2',
    },
  ];

  const volOILayout = {
    height: 280,
    margin: { l: 55, r: 55, t: 25, b: 35 },
    yaxis: {
      title: 'Volume (Lots)',
      titlefont: { color: '#06b6d4' },
      tickfont: { color: '#06b6d4' },
    },
    yaxis2: {
      title: 'Open Interest (Lots)',
      titlefont: { color: '#eab308' },
      tickfont: { color: '#eab308' },
      overlaying: 'y',
      side: 'right',
    },
    legend: { orientation: 'h', y: -0.2 },
  };

  return (
    <div className="space-y-6">
      {/* Purity Basis Notice */}
      <div className="p-3.5 rounded-xl bg-navy-850/80 border border-gold-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <Info size={16} className="text-gold-400 shrink-0" />
          <span className="text-slate-300">
            <strong className="text-white">Fineness Normalization Standard:</strong> GOLDM (995 purity) is converted to standard 999 purity basis:
            <code className="ml-1 text-gold-300 font-mono bg-navy-950 px-1.5 py-0.5 rounded border border-white/5">
              Price × (999 / 995) ≈ 1.00402
            </code>
            , adjusting for the ~0.4% intrinsic metal difference with GOLDTEN/GUINEA/PETAL (999 fineness).
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] font-mono text-slate-400">Rate Assumption:</span>
          <span className="text-[10px] bg-navy-950 text-cyan-400 px-2 py-0.5 rounded font-mono border border-cyan-500/30">
            FIXED_ASSUMPTION_7.0%
          </span>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-4 rounded-xl card-gradient border border-white/5">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs uppercase font-mono text-slate-400">Spread Pair:</label>
          <select
            value={selectedPair}
            onChange={(e) => setSelectedPair(e.target.value)}
            className="bg-navy-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white font-medium focus:outline-none focus:border-gold-500 font-mono"
          >
            {PAIRS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>

          {/* Timeframe Presets */}
          <div className="flex items-center gap-1 bg-navy-950 p-1 rounded-lg border border-white/5 font-mono text-xs">
            {['1M', '3M', '6M', 'ALL'].map((tf) => (
              <button
                key={tf}
                onClick={() => {
                  setTimeframe(tf);
                  setStartDate('');
                  setEndDate('');
                }}
                className={`px-2.5 py-1 rounded text-[11px] font-bold transition-all ${
                  timeframe === tf
                    ? 'bg-gold-500 text-navy-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Date Picker */}
          <div className="flex items-center gap-1.5 font-mono text-xs text-slate-400">
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setTimeframe('CUSTOM');
              }}
              className="bg-navy-950 border border-white/10 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-gold-500"
            />
            <span>&rarr;</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setTimeframe('CUSTOM');
              }}
              className="bg-navy-950 border border-white/10 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-gold-500"
            />
          </div>
        </div>

        {/* Toggles */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Purity Basis Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">Purity:</span>
            <button
              onClick={() => setUse999Purity(!use999Purity)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                use999Purity
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 shadow-sm'
                  : 'bg-navy-900 text-slate-400 border-white/10 hover:text-white'
              }`}
            >
              {use999Purity ? '✓ 999 Fineness (Standard)' : 'Raw Fineness'}
            </button>
          </div>

          {/* Carry Adjustment Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">Carry:</span>
            <button
              onClick={() => setUseCarryAdj(!useCarryAdj)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                useCarryAdj
                  ? 'bg-gold-500/20 text-gold-400 border-gold-500/40 shadow-sm'
                  : 'bg-navy-900 text-slate-400 border-white/10 hover:text-white'
              }`}
            >
              {useCarryAdj ? '✓ Exponential Carry-Adjusted' : 'Raw Spread'}
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadAnalytics} />}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Current Spread"
          value={formatINR(currentSpread)}
          subvalue={`${use999Purity ? '999 Pure' : 'Raw'} • ${useCarryAdj ? 'Carry adjusted (₹/10g)' : 'Raw settlement'}`}
          icon={Scale}
          badgeText={useCarryAdj ? 'Carry-Adjusted' : 'Raw'}
          badgeColor="gold"
        />
        <MetricCard
          title="Rolling Z-Score (20d)"
          value={latestMetric?.z_score !== null ? `${latestMetric?.z_score}σ` : '—'}
          subvalue={
            latestMetric?.z_score !== null && Math.abs(latestMetric.z_score) >= 2.0
              ? 'Divergence Alert Active'
              : 'Within ±2.0σ Fair Band'
          }
          icon={Activity}
          badgeText={
            latestMetric?.z_score !== null && Math.abs(latestMetric.z_score) >= 2.0
              ? 'Mispriced'
              : 'Normal'
          }
          badgeColor={
            latestMetric?.z_score !== null && Math.abs(latestMetric.z_score) >= 2.0 ? 'rose' : 'cyan'
          }
        />
        <MetricCard
          title="Mean Reversion Half-Life"
          value={
            Number.isFinite(latestMetric?.half_life_days)
              ? `${formatNumber(latestMetric.half_life_days, 1)}d`
              : '—'
          }
          subvalue={
            Number.isFinite(latestMetric?.half_life_days)
              ? 'Ornstein-Uhlenbeck estimate'
              : 'Insufficient data for estimate'
          }
          icon={Compass}
          badgeText={Number.isFinite(latestMetric?.half_life_days) ? 'Estimated' : 'Unavailable'}
          badgeColor={Number.isFinite(latestMetric?.half_life_days) ? 'cyan' : 'gold'}
        />
        <MetricCard
          title="Pair Correlation (30d)"
          value={hasPairCorrelation ? formatNumber(pairCorrelation, 3) : '—'}
          subvalue={
            hasPairCorrelation
              ? 'Normalized-price Pearson correlation'
              : 'Insufficient overlapping price data'
          }
          icon={Percent}
          badgeText={hasPairCorrelation ? 'Measured' : 'Unavailable'}
          badgeColor={hasPairCorrelation ? 'emerald' : 'gold'}
        />
      </div>

      {/* Main Spread Time-Series & Bands Chart */}
      <Card>
        <CardHeader
          title={`${selectedPair.replace(/_/g, ' ')} — Spread Dynamics & Reversion Bands`}
          subtitle={`Calculated on ${use999Purity ? '999 fineness pure gold' : 'unadjusted'} basis with 20-day rolling mean & ±2.0σ statistical boundaries`}
        />
        <div className="h-[340px]">
          <PlotlyChart
            data={spreadChartTraces}
            layout={{
              height: 340,
              yaxis: { title: 'Spread (₹ / 10g)', tickprefix: '₹' },
              legend: { orientation: 'h', y: -0.2 },
            }}
          />
        </div>
      </Card>

      {/* Z-Score Oscillator Chart */}
      <Card>
        <CardHeader
          title="Rolling Z-Score Oscillator"
          subtitle="Identifies statistical divergence extremes (+2σ overvalued, -2σ undervalued)"
        />
        <div className="h-[220px]">
          <PlotlyChart data={zScoreTraces} layout={zScoreLayout} />
        </div>
      </Card>

      {/* Futures Term Structure & Volume/OI Dual-Axis Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Futures Term Structure Curve */}
        <Card>
          <CardHeader
            title="Futures Term Structure Curve"
            subtitle="Normalized price per 10g across maturities (DTE)"
          />
          <div className="h-[280px]">
            <PlotlyChart
              data={[
                {
                  x: termStructure?.contracts?.map((p) => p.days_to_expiry) || [],
                  y: termStructure?.contracts?.map((p) => p.price_per_pure_10g_999) || [],
                  text: termStructure?.contracts?.map((p) => `${p.symbol} (${p.days_to_expiry}d)`) || [],
                  mode: 'lines+markers+text',
                  textposition: 'top center',
                  name: '999 Pure (₹/10g)',
                  line: { color: '#eab308', width: 2 },
                  marker: { size: 8, color: '#f59e0b' },
                },
                {
                  x: termStructure?.contracts?.map((p) => p.days_to_expiry) || [],
                  y: termStructure?.contracts?.map((p) => p.price_per_10g) || [],
                  name: 'Raw Quoted (₹/10g)',
                  mode: 'markers',
                  marker: { size: 6, color: '#06b6d4', symbol: 'diamond' },
                },
              ]}
              layout={{
                height: 280,
                xaxis: { title: 'Days to Expiry (DTE)' },
                yaxis: { title: 'Price (₹/10g)', tickprefix: '₹' },
                legend: { orientation: 'h', y: -0.2 },
              }}
            />
          </div>
          <p className="text-[11px] text-slate-500 mt-2 font-mono">
            Forward pricing curve reflects financing interest + vault storage cost-of-carry.
          </p>
        </Card>

        {/* Volume & Open Interest Dual-Axis Chart */}
        <Card>
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <div>
              <h3 className="text-sm font-bold text-white">Volume & Open Interest Liquidity</h3>
              <p className="text-xs text-slate-400">Daily contracts traded vs outstanding interest</p>
            </div>
            <div className="flex items-center gap-1.5 bg-navy-900 p-1 rounded-lg border border-white/10">
              {['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'].map((sym) => (
                <button
                  key={sym}
                  onClick={() => loadVolOI(sym)}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all ${
                    volOISymbol === sym
                      ? 'bg-gold-500 text-navy-950 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {sym}
                </button>
              ))}
            </div>
          </div>
          <div className="h-[280px]">
            <PlotlyChart data={volOITraces} layout={volOILayout} />
          </div>
        </Card>
      </div>

      {/* Cross-Contract Correlation Matrix */}
      <Card>
        <CardHeader
          title="Cross-Contract Correlation Matrix"
          subtitle="Normalized price co-movement across all 4 gold instruments"
        />
        <div className="h-[280px]">
          <PlotlyChart
            data={heatmapTrace}
            layout={{
              height: 280,
              margin: { l: 70, r: 25, t: 25, b: 40 },
              xaxis: {
                type: 'linear',
                tickmode: 'array',
                tickvals: corrMatrix?.contracts?.map((_, index) => index) || [],
                ticktext: corrMatrix?.contracts || [],
              },
              yaxis: {
                type: 'linear',
                autorange: 'reversed',
                tickmode: 'array',
                tickvals: corrMatrix?.contracts?.map((_, index) => index) || [],
                ticktext: corrMatrix?.contracts || [],
              },
            }}
          />
        </div>
      </Card>
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import { Layers, FileText, BarChart3, Database, Scale, Info } from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { PlotlyChart } from '../components/PlotlyChart';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatINR, formatNumber, formatDate } from '../utils/formatters';
import { CONTRACTS } from '../utils/constants';

export const ContractExplorer = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('GOLDM');
  const [bhavcopyRecords, setBhavcopyRecords] = useState([]);
  const [summary, setSummary] = useState(null);

  // Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [recordLimit, setRecordLimit] = useState(100);

  const loadContractData = async (symbol) => {
    try {
      setLoading(true);
      setError(null);
      const params = { symbol, limit: recordLimit };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;

      const [listRes, sumRes, histRes] = await Promise.all([
        endpoints.getContracts(),
        endpoints.getContractSummary(symbol),
        endpoints.getBhavcopyRecords(params),
      ]);
      setContracts(listRes.data);
      setSummary(sumRes.data);
      setBhavcopyRecords(histRes.data);
    } catch (err) {
      setError(err.message || 'Failed to load contract specifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContractData(selectedSymbol);
  }, [selectedSymbol, startDate, endDate, recordLimit]);

  if (loading && contracts.length === 0) {
    return <LoadingSpinner text="Retrieving MCX Gold contract specifications..." fullScreen />;
  }

  // Volume & OI Chart
  const sortedRecords = [...bhavcopyRecords].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
  const volumeTrace = {
    x: sortedRecords.map((r) => r.trade_date),
    y: sortedRecords.map((r) => r.volume_lots),
    name: 'Volume (Lots)',
    type: 'bar',
    marker: { color: '#06b6d4', opacity: 0.7 },
  };
  const oiTrace = {
    x: sortedRecords.map((r) => r.trade_date),
    y: sortedRecords.map((r) => r.open_interest),
    name: 'Open Interest (Lots)',
    type: 'scatter',
    mode: 'lines',
    yaxis: 'y2',
    line: { color: '#eab308', width: 2 },
  };

  return (
    <div className="space-y-6">
      {/* Header Selector Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-white/5">
        {Object.keys(CONTRACTS).map((sym) => {
          const isSelected = selectedSymbol === sym;
          return (
            <button
              key={sym}
              onClick={() => setSelectedSymbol(sym)}
              className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                isSelected
                  ? 'bg-gold-500 text-navy-950 shadow-md font-bold'
                  : 'bg-navy-900 text-slate-400 hover:text-white hover:bg-navy-800 border border-white/5'
              }`}
            >
              {CONTRACTS[sym].name} ({sym})
            </button>
          );
        })}
      </div>

      {error && <ErrorAlert message={error} onRetry={() => loadContractData(selectedSymbol)} />}

      {/* Contract Detail Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-gold-500">
          <p className="text-xs uppercase text-slate-400 font-mono">Trading Unit</p>
          <p className="text-xl font-bold font-mono text-white mt-1">
            {summary?.trading_unit_grams} Grams
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">Physical delivery unit</p>
        </Card>

        <Card className="border-l-4 border-l-cyan-500">
          <p className="text-xs uppercase text-slate-400 font-mono">Quotation Unit</p>
          <p className="text-xl font-bold font-mono text-cyan-400 mt-1">
            ₹ per {summary?.quotation_unit_grams}g
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">Price quote basis on exchange</p>
        </Card>

        <Card className="border-l-4 border-l-emerald-500">
          <p className="text-xs uppercase text-slate-400 font-mono">Latest Settle Price</p>
          <p className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {formatINR(summary?.latest_settle_price)}
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Normalized: {formatINR((summary?.latest_settle_price || 0) / (summary?.quotation_unit_grams || 1) * 10)} / 10g
          </p>
        </Card>

        <Card className="border-l-4 border-l-purple-500">
          <p className="text-xs uppercase text-slate-400 font-mono">Open Interest</p>
          <p className="text-xl font-bold font-mono text-purple-400 mt-1">
            {formatNumber(summary?.latest_open_interest, 0)} Lots
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">Active market participation</p>
        </Card>
      </div>

      {/* Contract Normalization & Microstructure Architecture */}
      <Card>
        <CardHeader
          title="Contract Microstructure & Normalization Engine"
          subtitle="How relative value parity is standardized across disparate lot sizes"
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-300">
          <div className="space-y-3 bg-navy-850 p-4 rounded-lg border border-white/5">
            <h4 className="font-semibold text-white flex items-center gap-1.5 text-xs uppercase tracking-wider">
              <Scale size={15} className="text-gold-400" />
              Standardization Formula
            </h4>
            <p className="text-slate-400 leading-relaxed">
              Because MCX quotes contracts in differing units (e.g., Gold Petal per 1g, Guinea per 8g, Mini per 10g), raw Bhavcopy settlement prices cannot be directly compared. The normalization engine maps every contract to standard per-gram and per-10-gram denominations:
            </p>
            <div className="bg-navy-950 p-3 rounded font-mono text-[11px] text-gold-300 space-y-1.5 border border-white/5">
              <div className="text-slate-400 font-semibold">// 999 Fineness Parity Standardization</div>
              <div>Price_per_pure_gram = (Raw_Settle / Quotation_Base_Grams) × (999 / Purity)</div>
              <div>Standardized_10g_Price = Price_per_pure_gram × 10.0</div>
              <div className="text-[10px] text-slate-500 pt-1">
                Fineness: GOLDM (995 fineness) • GOLDTEN (999) • GOLDGUINEA (999) • GOLDPETAL (999)
              </div>
            </div>
          </div>

          <div className="space-y-3 bg-navy-850 p-4 rounded-lg border border-white/5">
            <h4 className="font-semibold text-white flex items-center gap-1.5 text-xs uppercase tracking-wider">
              <Info size={15} className="text-cyan-400" />
              Trading Characteristics
            </h4>
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div className="p-2 bg-navy-950 rounded border border-white/5">
                <span className="text-slate-500 block text-[10px]">Tick Size</span>
                <span className="text-white font-bold">₹{summary?.tick_size || 1.0}</span>
              </div>
              <div className="p-2 bg-navy-950 rounded border border-white/5">
                <span className="text-slate-500 block text-[10px]">Contract Multiplier</span>
                <span className="text-white font-bold">{summary?.contract_multiplier}x</span>
              </div>
              <div className="p-2 bg-navy-950 rounded border border-white/5">
                <span className="text-slate-500 block text-[10px]">Approx Lot Notional</span>
                <span className="text-white font-bold">
                  {formatINR((summary?.latest_settle_price || 0) * (summary?.contract_multiplier || 1))}
                </span>
              </div>
              <div className="p-2 bg-navy-950 rounded border border-white/5">
                <span className="text-slate-500 block text-[10px]">Total History</span>
                <span className="text-white font-bold">{summary?.total_historical_records} Days</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Historical Volume & Open Interest Chart */}
      <Card>
        <CardHeader
          title={`${summary?.name || selectedSymbol} — Historical Volume & Open Interest`}
          subtitle="Daily traded lots and market participation trends"
        />
        <div className="h-[320px]">
          <PlotlyChart
            data={[volumeTrace, oiTrace]}
            layout={{
              height: 320,
              yaxis: { title: 'Traded Volume (Lots)' },
              yaxis2: {
                title: 'Open Interest (Lots)',
                overlaying: 'y',
                side: 'right',
                gridcolor: 'transparent',
              },
              legend: { orientation: 'h', y: -0.2 },
            }}
          />
        </div>
      </Card>

      {/* Historical Settlement Records Table & Filter */}
      <Card>
        <CardHeader
          title={`${selectedSymbol} Settlement History (${bhavcopyRecords.length} Records)`}
          subtitle="Raw daily Bhavcopy records with open, high, low, close, and settlement prices"
          action={
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 text-slate-400 text-xs font-mono">
                <span className="text-[11px]">From:</span>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-navy-950 border border-white/10 rounded px-2 py-1 text-white text-xs font-mono focus:outline-none focus:border-gold-500"
                />
              </div>
              <div className="flex items-center gap-1 text-slate-400 text-xs font-mono">
                <span className="text-[11px]">To:</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-navy-950 border border-white/10 rounded px-2 py-1 text-white text-xs font-mono focus:outline-none focus:border-gold-500"
                />
              </div>
              <select
                value={recordLimit}
                onChange={(e) => setRecordLimit(Number(e.target.value))}
                className="bg-navy-950 border border-white/10 rounded px-2 py-1 text-white text-xs font-mono focus:outline-none focus:border-gold-500"
              >
                <option value={50}>50 rows</option>
                <option value={100}>100 rows</option>
                <option value={200}>200 rows</option>
              </select>
            </div>
          }
        />
        <div className="overflow-x-auto max-h-[350px]">
          {bhavcopyRecords.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No historical Bhavcopy settlement records found for {selectedSymbol} within the selected date range.
            </div>
          ) : (
            <table className="w-full text-left text-xs font-mono">
              <thead className="sticky top-0 bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                <tr>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Expiry</th>
                  <th className="py-2.5 px-3">Open</th>
                  <th className="py-2.5 px-3">High</th>
                  <th className="py-2.5 px-3">Low</th>
                  <th className="py-2.5 px-3">Settle Price</th>
                  <th className="py-2.5 px-3">Volume (Lots)</th>
                  <th className="py-2.5 px-3">Open Interest</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {bhavcopyRecords.map((r) => (
                  <tr key={`${r.trade_date}-${r.symbol}`} className="hover:bg-white/[0.02]">
                    <td className="py-2.5 px-3 text-slate-300">{formatDate(r.trade_date)}</td>
                    <td className="py-2.5 px-3 text-slate-500">{formatDate(r.expiry_date)}</td>
                    <td className="py-2.5 px-3 text-slate-400">{formatINR(r.open_price)}</td>
                    <td className="py-2.5 px-3 text-emerald-400/90">{formatINR(r.high_price)}</td>
                    <td className="py-2.5 px-3 text-rose-400/90">{formatINR(r.low_price)}</td>
                    <td className="py-2.5 px-3 font-bold text-white">{formatINR(r.settle_price)}</td>
                    <td className="py-2.5 px-3 text-cyan-400">{formatNumber(r.volume_lots, 0)}</td>
                    <td className="py-2.5 px-3 text-gold-400">{formatNumber(r.open_interest, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
};

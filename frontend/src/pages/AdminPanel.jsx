import React, { useState, useEffect } from 'react';
import {
  Sliders,
  UploadCloud,
  Database,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Info,
  Server,
  FileSpreadsheet,
  Coins,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatNumber } from '../utils/formatters';

export const AdminPanel = ({ onDataChanged }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [config, setConfig] = useState(null);

  // Demo generator state
  const [demoDays, setDemoDays] = useState(90);
  const [seeding, setSeeding] = useState(false);

  // File upload state
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Reset state
  const [resetting, setResetting] = useState(false);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await endpoints.getSystemConfig();
      setConfig(res.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch admin configuration.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSeedDemo = async () => {
    try {
      setSeeding(true);
      setError(null);
      setSuccessMsg(null);
      const res = await endpoints.seedDemoData(demoDays);
      setSuccessMsg(res.data.message);
      await loadConfig();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || 'Failed to seed demo data.');
    } finally {
      setSeeding(false);
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    try {
      setUploading(true);
      setError(null);
      setSuccessMsg(null);
      const formData = new FormData();
      formData.append('file', uploadFile);
      const res = await endpoints.uploadBhavcopy(formData);
      setSuccessMsg(res.data.message);
      setUploadFile(null);
      await loadConfig();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || 'CSV upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleResetDb = async () => {
    if (!window.confirm('Are you sure you want to reset the database? All records will be cleared.')) {
      return;
    }

    try {
      setResetting(true);
      setError(null);
      setSuccessMsg(null);
      const res = await endpoints.resetDatabase();
      setSuccessMsg(res.data.message);
      await loadConfig();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || 'Failed to reset database.');
    } finally {
      setResetting(false);
    }
  };

  if (loading && !config) {
    return <LoadingSpinner text="Retrieving platform configuration..." fullScreen />;
  }

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {successMsg && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-emerald-400" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold">
            ✕
          </button>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={loadConfig} />}

      {/* 2-Column Action Section: Real Bhavcopy Upload vs Demo Seeder */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Official MCX Public Bhavcopy CSV */}
        <Card>
          <CardHeader
            title="Public Bhavcopy CSV Ingestion"
            subtitle="Upload real exchange Bhavcopy settlement files"
          />
          <form onSubmit={handleFileUpload} className="space-y-4">
            <div className="border-2 border-dashed border-white/10 rounded-xl p-6 text-center hover:border-gold-500/40 transition-colors bg-navy-950/40">
              <UploadCloud size={36} className="mx-auto text-slate-500 mb-2" />
              <p className="text-xs text-slate-300 font-medium">
                {uploadFile ? uploadFile.name : 'Choose MCX Bhavcopy CSV file to upload'}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Accepts comma-separated format (.csv) with Symbol, Date, Expiry, Settle Price
              </p>
              <input
                type="file"
                accept=".csv"
                id="bhavcopyFile"
                className="hidden"
                onChange={(e) => setUploadFile(e.target.files[0])}
              />
              <label
                htmlFor="bhavcopyFile"
                className="mt-3 inline-block px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-xs text-slate-200 border border-white/10 cursor-pointer font-medium"
              >
                Browse Files
              </label>
            </div>

            <button
              type="submit"
              disabled={!uploadFile || uploading}
              className="w-full py-2.5 px-4 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 font-bold text-xs transition-all shadow-md disabled:opacity-40"
            >
              {uploading ? 'Processing Bhavcopy CSV...' : 'Ingest & Process Bhavcopy'}
            </button>
          </form>
        </Card>

        {/* Generate Calibrated Synthetic Demo Dataset */}
        <Card>
          <CardHeader
            title="Synthetic Demo Generator"
            subtitle="Simulate realistic historical Bhavcopy data for testing & demo"
          />
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded-lg bg-navy-950 border border-amber-500/20 text-amber-200/90 leading-relaxed">
              <span className="font-semibold text-amber-300 block mb-1">
                Data Provenance Notice:
              </span>
              Generates continuous Brownian random-walk settlement data calibrated to MCX Gold mini, ten, guinea, and petal microstructure. Clearly tagged as <code className="text-amber-400">DEMO_SYNTHETIC</code>.
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-slate-400 font-mono">History Duration:</label>
                <span className="text-gold-400 font-mono font-bold">{demoDays} Trading Days</span>
              </div>
              <input
                type="range"
                min="30"
                max="180"
                step="15"
                value={demoDays}
                onChange={(e) => setDemoDays(parseInt(e.target.value))}
                className="w-full accent-gold-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
                <span>30 Days (1 mo)</span>
                <span>90 Days (Quarter)</span>
                <span>180 Days (Half Year)</span>
              </div>
            </div>

            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="w-full py-2.5 px-4 rounded-lg bg-navy-800 hover:bg-navy-750 text-gold-400 border border-gold-500/30 hover:border-gold-500/50 font-bold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-40"
            >
              <RefreshCw size={14} className={seeding ? 'animate-spin' : ''} />
              <span>{seeding ? 'Generating Synthetic Market Data...' : 'Seed Synthetic Demo Data'}</span>
            </button>
          </div>
        </Card>
      </div>

      {/* System Cost Configuration & Database Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cost & Carry Parameters */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader
              title="Statutory MCX Transaction Cost Model"
              subtitle="Live parameters used in RVA signal edge calculation"
            />
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 bg-navy-950 rounded-lg border border-white/5">
                <span className="text-slate-500 text-[10px] block">Exchange Turnover Fee</span>
                <span className="text-white font-bold">0.0021% (₹2.1/lakh)</span>
              </div>
              <div className="p-3 bg-navy-950 rounded-lg border border-white/5">
                <span className="text-slate-500 text-[10px] block">SEBI Turnover Fee</span>
                <span className="text-white font-bold">0.0001% (₹10/Cr)</span>
              </div>
              <div className="p-3 bg-navy-950 rounded-lg border border-white/5">
                <span className="text-slate-500 text-[10px] block">Commodity Trans Tax (CTT)</span>
                <span className="text-white font-bold">0.01% (Sell Leg)</span>
              </div>
              <div className="p-3 bg-navy-950 rounded-lg border border-white/5">
                <span className="text-slate-500 text-[10px] block">GST on Charges</span>
                <span className="text-white font-bold">18.00%</span>
              </div>
              <div className="p-3 bg-navy-950 rounded-lg border border-white/5">
                <span className="text-slate-500 text-[10px] block">Stamp Duty (State)</span>
                <span className="text-white font-bold">0.002% (Buy Leg)</span>
              </div>
              <div className="p-3 bg-navy-950 rounded-lg border border-white/5">
                <span className="text-slate-500 text-[10px] block">Annual Financing Rate</span>
                <span className="text-gold-400 font-bold">
                  {(config?.annual_risk_free_rate * 100 || 6.5).toFixed(2)}% p.a.
                </span>
              </div>
            </div>
          </Card>
        </div>

        {/* Database Stats & Maintenance */}
        <div>
          <Card className="h-full flex flex-col justify-between">
            <div>
              <CardHeader
                title="Database State"
                subtitle="Entity counts & storage"
              />
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-slate-400">Bhavcopy Records:</span>
                  <span className="text-white font-bold">{formatNumber(config?.records_count, 0)}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-slate-400">Spread Pairs Computed:</span>
                  <span className="text-cyan-400 font-bold">{formatNumber(config?.spread_count, 0)}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-slate-400">RVA Signals Generated:</span>
                  <span className="text-gold-400 font-bold">{formatNumber(config?.signals_count, 0)}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-slate-400">Saved Backtests:</span>
                  <span className="text-emerald-400 font-bold">{config?.backtest_count || 0}</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-white/5">
              <button
                onClick={handleResetDb}
                disabled={resetting}
                className="w-full py-2 px-3 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-bold border border-rose-500/30 flex items-center justify-center gap-2 transition-colors disabled:opacity-40"
              >
                <Trash2 size={14} />
                <span>{resetting ? 'Resetting DB...' : 'Reset Database to Clean State'}</span>
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

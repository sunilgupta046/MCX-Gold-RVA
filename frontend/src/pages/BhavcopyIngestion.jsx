import React, { useState, useEffect } from 'react';
import {
  DownloadCloud,
  UploadCloud,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  FileSpreadsheet,
  RefreshCw,
  Search,
  Filter,
  Layers,
  ShieldAlert,
  ArrowRight,
  Info,
  Database,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatNumber, formatDate } from '../utils/formatters';

export const BhavcopyIngestion = ({ onDataChanged }) => {
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [summary, setSummary] = useState(null);

  // Active sub-tab: 'single' | 'range' | 'upload'
  const [activeMode, setActiveMode] = useState('single');

  // Single date form
  const getTodayFormatted = () => {
    const now = new Date();
    const d = String(now.getDate()).padStart(2, '0');
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const y = now.getFullYear();
    return `${d}/${m}/${y}`;
  };

  const getDaysAgoFormatted = (days) => {
    const d = new Date();
    d.setDate(d.getDate() - days);
    const day = String(d.getDate()).padStart(2, '0');
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const y = d.getFullYear();
    return `${day}/${m}/${y}`;
  };

  const [singleDate, setSingleDate] = useState(getDaysAgoFormatted(1));

  // Date range form
  const [rangeStart, setRangeStart] = useState(getDaysAgoFormatted(7));
  const [rangeEnd, setRangeEnd] = useState(getDaysAgoFormatted(1));

  // File upload form
  const [uploadFile, setUploadFile] = useState(null);
  const [expectedDate, setExpectedDate] = useState('');

  // Table filter
  const [statusFilter, setStatusFilter] = useState('');

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await endpoints.getIngestionStatus();
      setSummary(res.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch ingestion status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleFetchSingle = async (e) => {
    e.preventDefault();
    if (!singleDate) return;
    try {
      setFetching(true);
      setError(null);
      setSuccessMsg(null);
      const res = await endpoints.fetchDate(singleDate);
      if (res.data.status === 'SUCCESS' || res.data.status === 'PARTIAL') {
        setSuccessMsg(`Successfully imported Bhavcopy for ${singleDate} (${res.data.records_imported} contracts).`);
      } else {
        setError(`Session outcome for ${singleDate}: [${res.data.status}] ${res.data.error_message || 'Inaccessible'}`);
      }
      await loadStatus();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || 'Failed to fetch Bhavcopy from MCX portal.');
    } finally {
      setFetching(false);
    }
  };

  const handleFetchRange = async (e) => {
    e.preventDefault();
    if (!rangeStart || !rangeEnd) return;
    try {
      setFetching(true);
      setError(null);
      setSuccessMsg(null);
      const res = await endpoints.fetchRange(rangeStart, rangeEnd);
      const importedCount = res.data.reduce((acc, curr) => acc + (curr.records_imported || 0), 0);
      setSuccessMsg(`Historical batch completed: Processed ${res.data.length} dates, imported ${importedCount} records.`);
      await loadStatus();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || 'Range ingestion failed.');
    } finally {
      setFetching(false);
    }
  };

  const handleManualUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    try {
      setFetching(true);
      setError(null);
      setSuccessMsg(null);
      const formData = new FormData();
      formData.append('file', uploadFile);
      const res = await endpoints.uploadBhavcopyManual(formData, expectedDate || undefined);
      if (res.data.status === 'SUCCESS' || res.data.status === 'PARTIAL') {
        setSuccessMsg(`Successfully ingested ${res.data.records_imported} records from ${uploadFile.name}.`);
        setUploadFile(null);
      } else {
        setError(`Upload rejected [${res.data.status}]: ${res.data.error_message}`);
      }
      await loadStatus();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || 'File upload failed.');
    } finally {
      setFetching(false);
    }
  };

  if (loading && !summary) {
    return <LoadingSpinner text="Connecting to MCX daily Bhavcopy ingestion subsystem..." fullScreen />;
  }

  // Filtered log records
  const filteredLogs = summary?.recent_logs?.filter((l) => {
    if (!statusFilter) return true;
    return l.status === statusFilter;
  }) || [];

  return (
    <div className="space-y-6">
      {/* Top Banner Notice */}
      <div className="rounded-xl border border-white/5 bg-gradient-to-r from-navy-900 via-navy-850 to-navy-900 p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gold-500/10 text-gold-400 border border-gold-500/20 flex items-center justify-center shrink-0">
            <DownloadCloud size={20} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              MCX Daily Bhavcopy Ingestion Engine
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Source: <code className="text-gold-300 font-mono">https://www.mcxindia.com/market-data/bhavcopy</code> • Enforces zero silent date substitution, compact expiry parsing, and deduplication.
            </p>
          </div>
        </div>

        <button
          onClick={loadStatus}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-colors shrink-0"
        >
          <RefreshCw size={13} />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-2">
            ✕
          </button>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={loadStatus} />}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          title="Total Sessions"
          value={summary?.total_sessions || 0}
          subvalue="Import requests logged"
          badgeColor="cyan"
        />
        <MetricCard
          title="Successful"
          value={summary?.successful_sessions || 0}
          subvalue="Parity data verified"
          badgeColor="emerald"
        />
        <MetricCard
          title="Rejected Dates"
          value={summary?.rejected_sessions || 0}
          subvalue="Mismatch blocked (Rule 9)"
          badgeColor="rose"
        />
        <MetricCard
          title="Holidays / Wknd"
          value={summary?.holiday_sessions || 0}
          subvalue="Non-trading days detected"
          badgeColor="gold"
        />
        <MetricCard
          title="Inaccessible / 403"
          value={summary?.unavailable_sessions || 0}
          subvalue="Exchange WAF restrictions"
          badgeColor="gold"
        />
        <MetricCard
          title="Contracts Stored"
          value={formatNumber(summary?.total_records_imported, 0)}
          subvalue="Gold M/10/G/P series"
          badgeColor="emerald"
        />
      </div>

      {/* Mode Selector & Forms */}
      <Card>
        <div className="flex items-center gap-2 pb-3 mb-4 border-b border-white/5">
          <button
            onClick={() => setActiveMode('single')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeMode === 'single'
                ? 'bg-gold-500 text-navy-950 shadow-sm font-bold'
                : 'bg-navy-900 text-slate-400 hover:text-white border border-white/5'
            }`}
          >
            1. Single Date Fetch (DD/MM/YYYY)
          </button>

          <button
            onClick={() => setActiveMode('range')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeMode === 'range'
                ? 'bg-gold-500 text-navy-950 shadow-sm font-bold'
                : 'bg-navy-900 text-slate-400 hover:text-white border border-white/5'
            }`}
          >
            2. Historical Date Range
          </button>

          <button
            onClick={() => setActiveMode('upload')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeMode === 'upload'
                ? 'bg-gold-500 text-navy-950 shadow-sm font-bold'
                : 'bg-navy-900 text-slate-400 hover:text-white border border-white/5'
            }`}
          >
            3. Manual Bhavcopy CSV Upload
          </button>
        </div>

        {/* Mode 1: Single Date Fetch */}
        {activeMode === 'single' && (
          <form onSubmit={handleFetchSingle} className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3 text-xs">
              <div className="w-full sm:w-64">
                <label className="text-slate-400 font-mono block mb-1">
                  Target Trading Date (DD/MM/YYYY):
                </label>
                <input
                  type="text"
                  placeholder="DD/MM/YYYY (e.g. 21/10/2026)"
                  value={singleDate}
                  onChange={(e) => setSingleDate(e.target.value)}
                  className="w-full bg-navy-900 border border-white/10 rounded-lg px-3 py-2 text-white font-mono focus:border-gold-500 focus:outline-none"
                  required
                />
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setSingleDate(getTodayFormatted())}
                  className="px-2.5 py-2 rounded-lg bg-navy-850 hover:bg-navy-800 text-slate-300 font-mono text-[11px] border border-white/5"
                >
                  Today
                </button>
                <button
                  type="button"
                  onClick={() => setSingleDate(getDaysAgoFormatted(1))}
                  className="px-2.5 py-2 rounded-lg bg-navy-850 hover:bg-navy-800 text-slate-300 font-mono text-[11px] border border-white/5"
                >
                  Yesterday
                </button>
                <button
                  type="button"
                  onClick={() => setSingleDate(getDaysAgoFormatted(2))}
                  className="px-2.5 py-2 rounded-lg bg-navy-850 hover:bg-navy-800 text-slate-300 font-mono text-[11px] border border-white/5"
                >
                  -2 Days
                </button>
              </div>

              <button
                type="submit"
                disabled={fetching}
                className="w-full sm:w-auto px-4 py-2 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
              >
                <DownloadCloud size={14} className={fetching ? 'animate-bounce' : ''} />
                <span>{fetching ? 'Fetching MCX Portal...' : 'Fetch Official Bhavcopy'}</span>
              </button>
            </div>

            <p className="text-[11px] text-slate-500 font-mono">
              Validates requested date against returned settlement date. Rejects silent substitutions. If MCX firewall challenges direct script download (HTTP 403), use Mode 3 to upload the official file.
            </p>
          </form>
        )}

        {/* Mode 2: Historical Range */}
        {activeMode === 'range' && (
          <form onSubmit={handleFetchRange} className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3 text-xs">
              <div className="w-full sm:w-56">
                <label className="text-slate-400 font-mono block mb-1">Start Date (DD/MM/YYYY):</label>
                <input
                  type="text"
                  placeholder="DD/MM/YYYY"
                  value={rangeStart}
                  onChange={(e) => setRangeStart(e.target.value)}
                  className="w-full bg-navy-900 border border-white/10 rounded-lg px-3 py-2 text-white font-mono focus:border-gold-500 focus:outline-none"
                  required
                />
              </div>

              <div className="w-full sm:w-56">
                <label className="text-slate-400 font-mono block mb-1">End Date (DD/MM/YYYY):</label>
                <input
                  type="text"
                  placeholder="DD/MM/YYYY"
                  value={rangeEnd}
                  onChange={(e) => setRangeEnd(e.target.value)}
                  className="w-full bg-navy-900 border border-white/10 rounded-lg px-3 py-2 text-white font-mono focus:border-gold-500 focus:outline-none"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={fetching}
                className="w-full sm:w-auto px-4 py-2 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
              >
                <DownloadCloud size={14} className={fetching ? 'animate-bounce' : ''} />
                <span>{fetching ? 'Processing Range...' : 'Fetch Date Range'}</span>
              </button>
            </div>

            <p className="text-[11px] text-slate-500 font-mono">
              Sequentially queries calendar days. Automatically logs weekends and trading holidays without creating gaps.
            </p>
          </form>
        )}

        {/* Mode 3: Manual CSV Upload with Date Match Validation */}
        {activeMode === 'upload' && (
          <form onSubmit={handleManualUpload} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border-2 border-dashed border-white/10 rounded-xl p-5 text-center bg-navy-950/40">
                <UploadCloud size={30} className="mx-auto text-slate-500 mb-1" />
                <p className="text-xs text-slate-300 font-medium">
                  {uploadFile ? uploadFile.name : 'Select official Bhavcopy CSV downloaded from MCX India'}
                </p>
                <input
                  type="file"
                  accept=".csv"
                  id="bhavcopyUploadInput"
                  className="hidden"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                />
                <label
                  htmlFor="bhavcopyUploadInput"
                  className="mt-2 inline-block px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-xs text-slate-200 border border-white/10 cursor-pointer font-medium"
                >
                  Browse File (.csv)
                </label>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <label className="text-slate-400 font-mono block mb-1">
                    Expected Date (DD/MM/YYYY) — Optional Validation Guard:
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 21/10/2026 (Optional)"
                    value={expectedDate}
                    onChange={(e) => setExpectedDate(e.target.value)}
                    className="w-full bg-navy-900 border border-white/10 rounded-lg px-3 py-2 text-white font-mono focus:border-gold-500 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    If set, system strictly enforces Rule 9: rejects upload if file trading date differs.
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={!uploadFile || fetching}
                  className="w-full py-2.5 px-4 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 font-bold text-xs transition-all shadow-md disabled:opacity-40"
                >
                  {fetching ? 'Validating & Ingesting...' : 'Upload & Parse Bhavcopy'}
                </button>
              </div>
            </div>
          </form>
        )}
      </Card>

      {/* Comprehensive Ingestion Audit Table */}
      <Card>
        <CardHeader
          title={`Ingestion Audit Trail & Session Logs (${filteredLogs.length})`}
          subtitle="Real-time validation log tracking requested date, returned date, contracts, and error reasons"
          action={
            <div className="flex items-center gap-2">
              <Filter size={13} className="text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-navy-900 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none"
              >
                <option value="">All Statuses</option>
                <option value="SUCCESS">SUCCESS</option>
                <option value="PARTIAL">PARTIAL</option>
                <option value="REJECTED_DATE_MISMATCH">REJECTED (Date Mismatch)</option>
                <option value="HOLIDAY_OR_WEEKEND">HOLIDAY / WEEKEND</option>
                <option value="UNAVAILABLE_FILE">UNAVAILABLE / 403</option>
                <option value="NETWORK_ERROR">NETWORK ERROR</option>
              </select>
            </div>
          }
        />

        <div className="overflow-x-auto max-h-[460px]">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No ingestion sessions recorded matching filter.
            </div>
          ) : (
            <table className="w-full text-left text-xs font-mono">
              <thead className="sticky top-0 bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                <tr>
                  <th className="py-2.5 px-3">Session Date</th>
                  <th className="py-2.5 px-3">Requested Date</th>
                  <th className="py-2.5 px-3">Returned Date</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Source</th>
                  <th className="py-2.5 px-3">Contracts Detected</th>
                  <th className="py-2.5 px-3">Missing Contracts</th>
                  <th className="py-2.5 px-3">Imported</th>
                  <th className="py-2.5 px-3">Details / Validation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredLogs.map((log) => {
                  const isMatch = log.requested_date && log.returned_date && log.requested_date === log.returned_date;
                  const isMismatch = log.requested_date && log.returned_date && log.requested_date !== log.returned_date;

                  return (
                    <tr key={log.id} className="hover:bg-white/[0.02]">
                      <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                        {new Date(log.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-white">
                        {log.requested_date_str || (log.requested_date ? formatDate(log.requested_date) : '—')}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 ${
                            isMatch
                              ? 'text-emerald-400 font-semibold'
                              : isMismatch
                              ? 'text-rose-400 font-bold'
                              : 'text-slate-400'
                          }`}
                        >
                          {log.returned_date_str || (log.returned_date ? formatDate(log.returned_date) : '—')}
                          {isMatch && <CheckCircle2 size={12} className="text-emerald-400" />}
                          {isMismatch && <XCircle size={12} className="text-rose-400" />}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <StatusBadge status={log.status} />
                      </td>
                      <td className="py-2.5 px-3 text-[11px] text-slate-400">
                        {log.source_type.replace(/_/g, ' ')}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex flex-wrap gap-1">
                          {log.contracts_found?.length > 0 ? (
                            log.contracts_found.map((c) => (
                              <span
                                key={c}
                                className="px-1.5 py-0.2 rounded bg-navy-800 text-[10px] text-gold-300 font-bold border border-white/5"
                              >
                                {c}
                              </span>
                            ))
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex flex-wrap gap-1">
                          {log.missing_contracts?.length > 0 ? (
                            log.missing_contracts.map((c) => (
                              <span
                                key={c}
                                className="px-1.5 py-0.2 rounded bg-rose-500/10 text-[10px] text-rose-400 font-mono border border-rose-500/20"
                              >
                                {c}
                              </span>
                            ))
                          ) : (
                            <span className="text-emerald-400 text-[10px]">None</span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-white">
                        {log.records_imported}
                      </td>
                      <td className="py-2.5 px-3 text-[11px] font-sans text-slate-400 max-w-xs truncate">
                        {log.error_message || (log.status === 'SUCCESS' ? 'All contracts verified' : '—')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
};

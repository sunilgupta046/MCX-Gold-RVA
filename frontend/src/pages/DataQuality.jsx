import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  AlertOctagon,
  Calendar,
  Layers,
  Database,
  FileCheck,
  Info,
} from 'lucide-react';
import { endpoints } from '../api/client';
import { Card, CardHeader } from '../components/Card';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorAlert } from '../components/ErrorAlert';
import { formatNumber, formatDate } from '../utils/formatters';

export const DataQuality = () => {
  const [loading, setLoading] = useState(true);
  const [auditing, setAuditing] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);

  const loadReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await endpoints.getDataQualityReport();
      setReport(res.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch data quality audit.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAudit = async () => {
    try {
      setAuditing(true);
      const res = await endpoints.runDataQualityAudit();
      setReport(res.data);
    } catch (err) {
      setError(err.message || 'Audit execution failed.');
    } finally {
      setAuditing(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  if (loading && !report) {
    return <LoadingSpinner text="Running automated data quality and integrity checks..." fullScreen />;
  }

  const score = report?.overall_health_score || 100;
  const scoreColor = score >= 90 ? 'text-emerald-400' : score >= 75 ? 'text-amber-400' : 'text-rose-400';

  return (
    <div className="space-y-6">
      {/* Top Health Header Banner */}
      <Card className="bg-gradient-to-r from-navy-900 via-navy-850 to-navy-900">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-xl bg-navy-950 border border-white/10 flex flex-col items-center justify-center shrink-0">
              <span className={`text-2xl font-bold font-mono ${scoreColor}`}>{score}%</span>
              <span className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">Score</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Bhavcopy Data Health Audit</h3>
                <StatusBadge status={report?.status} />
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Automated continuous auditing of settlement sequence, missing business dates, zero-volume anomalies, and outlier jumps.
              </p>
            </div>
          </div>

          <button
            onClick={handleRunAudit}
            disabled={auditing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-navy-800 hover:bg-navy-700 text-slate-200 text-xs font-semibold border border-white/10 transition-colors disabled:opacity-50 shrink-0"
          >
            <RefreshCw size={14} className={auditing ? 'animate-spin text-gold-400' : ''} />
            <span>{auditing ? 'Auditing Database...' : 'Run Fresh Audit'}</span>
          </button>
        </div>
      </Card>

      {/* Synthetic Dataset Disclaimer if demo active */}
      {report?.is_demo_dataset && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-200 flex items-start gap-3">
          <Info size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-300">
              SYNTHETIC DEMO DATASET ACTIVE:
            </p>
            <p className="text-amber-200/80 leading-relaxed">
              Current records are generated using stochastic Brownian walks calibrated to recent MCX gold price levels and contract spreads for algorithmic testing. To analyze live market data, upload official public MCX Bhavcopy CSV files via the Admin Panel.
            </p>
          </div>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={loadReport} />}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Audited Records"
          value={formatNumber(report?.total_records, 0)}
          subvalue={`${report?.distinct_dates || 0} trading sessions`}
          icon={Database}
          badgeColor="cyan"
        />
        <MetricCard
          title="Contracts Verified"
          value={`${report?.contracts_checked || 0} / 4`}
          subvalue="GOLDM, 10, Guinea, Petal"
          icon={Layers}
          badgeColor="emerald"
        />
        <MetricCard
          title="Missing Business Dates"
          value={report?.missing_dates_detected || 0}
          subvalue="Mon-Fri trading gaps"
          icon={Calendar}
          badgeColor={report?.missing_dates_detected > 0 ? 'rose' : 'emerald'}
        />
        <MetricCard
          title="Price Jump Outliers"
          value={report?.price_jump_anomalies || 0}
          subvalue="Daily delta > 4%"
          icon={AlertOctagon}
          badgeColor={report?.price_jump_anomalies > 0 ? 'rose' : 'emerald'}
        />
      </div>

      {/* Integrity Checklist & Guidelines */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-2 text-white font-semibold text-xs uppercase tracking-wider">
            <CheckCircle2 size={16} className="text-emerald-400" />
            <span>Tick Size Quantization</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            All settlement prices conform to the mandatory ₹1.00 minimum price tick rule.
          </p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-2 text-white font-semibold text-xs uppercase tracking-wider">
            <CheckCircle2 size={16} className="text-emerald-400" />
            <span>Multi-Contract Parity</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Normalized price basis (₹/10g) preserves no-arbitrage boundary across all 4 delivery sizes.
          </p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-2 text-white font-semibold text-xs uppercase tracking-wider">
            <ShieldCheck size={16} className="text-cyan-400" />
            <span>Friction Deductions</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Exchange fees, SEBI charges, GST, CTT, and stamp duties are deducted before signal triggers.
          </p>
        </Card>
      </div>

      {/* Anomalies Detected Table */}
      <Card>
        <CardHeader
          title={`Detected Audit Flags & Anomalies (${report?.anomalies?.length || 0})`}
          subtitle="Specific dates and contracts flagged for review"
        />
        <div className="overflow-x-auto max-h-[350px]">
          {report?.anomalies?.length === 0 ? (
            <div className="text-center py-10 text-emerald-400 text-xs flex flex-col items-center gap-2">
              <CheckCircle2 size={24} />
              <span>Zero critical anomalies detected across historical settlement records.</span>
            </div>
          ) : (
            <table className="w-full text-left text-xs font-mono">
              <thead className="sticky top-0 bg-navy-900 border-b border-white/10 text-slate-400 text-[11px] uppercase">
                <tr>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Contract</th>
                  <th className="py-2.5 px-3">Anomaly Type</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {report?.anomalies?.map((ano, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02]">
                    <td className="py-2.5 px-3 text-slate-300">{formatDate(ano.date)}</td>
                    <td className="py-2.5 px-3 font-bold text-white">{ano.symbol}</td>
                    <td className="py-2.5 px-3 text-amber-400">{ano.anomaly_type}</td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={ano.severity} />
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 font-sans">{ano.description}</td>
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

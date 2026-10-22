import axios from 'axios';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const customError = {
      message: error.response?.data?.detail || error.message || 'An unexpected error occurred',
      status: error.response?.status,
      data: error.response?.data,
    };
    return Promise.reject(customError);
  }
);

export const endpoints = {
  // Health
  getHealth: () => api.get('/health'),
  
  // Contracts
  getContracts: () => api.get('/contracts'),
  getContractSummary: (symbol) => api.get(`/contracts/${symbol}/summary`),
  
  // Bhavcopy
  getBhavcopyRecords: (params) => api.get('/bhavcopy', { params }),
  getBhavcopyDates: () => api.get('/bhavcopy/dates'),
  uploadBhavcopy: (formData) => api.post('/bhavcopy/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  seedDemoData: (days = 90) => api.post(`/bhavcopy/seed-demo?days=${days}`),
  
  // Analytics
  getNormalizedPrices: (params) => api.get('/analytics/normalized-prices', { params }),
  getSpreadAnalytics: (params) => api.get('/analytics/spreads', { params }),
  getCorrelationMatrix: (params) => api.get('/analytics/correlation-matrix', { params }),
  getCarryCurve: (params) => api.get('/analytics/carry-curve', { params }),
  getOverviewMetrics: () => api.get('/analytics/overview'),
  getTermStructure: (params) => api.get('/analytics/term-structure', { params }),
  getVolumeOI: (params) => api.get('/analytics/volume-oi', { params }),
  getSpreadDetails: (params) => api.get('/analytics/spread-details', { params }),
  
  // Signals & Qualification Alerts
  getSignals: (params) => api.get('/signals', { params }),
  getActiveSignals: () => api.get('/signals/active'),
  getQualifiedSignals: () => api.get('/signals/qualified'),
  getCandidates: (params) => api.get('/signals/candidates', { params }),
  getAlertHistory: (params) => api.get('/signals/history', { params }),
  evaluateSignals: (params) => api.post('/signals/evaluate', null, { params }),
  getQuietAlerts: (params) => api.get('/signals/quiet-alerts', { params }),
  generateSignals: () => api.post('/signals/generate'),
  
  // Backtesting
  runBacktest: (config) => api.post('/backtest/run', config),
  getBacktestHistory: () => api.get('/backtest/history'),
  getBacktestDetail: (id) => api.get(`/backtest/${id}`),
  runSensitivity: (params) => api.post('/backtest/sensitivity', null, { params }),
  getTradesCsvUrl: (id) => `${apiBaseUrl}/backtest/${id}/export/trades.csv`,
  getEquityCsvUrl: (id) => `${apiBaseUrl}/backtest/${id}/export/equity.csv`,
  
  // Data Quality
  getDataQualityReport: () => api.get('/data-quality/report'),
  runDataQualityAudit: () => api.post('/data-quality/audit'),

  // Ingestion Module
  getIngestionStatus: () => api.get('/ingestion/status'),
  fetchDate: (date_str) => api.post('/ingestion/fetch-date', { date_str }),
  fetchRange: (start_date_str, end_date_str) => api.post('/ingestion/fetch-range', { start_date_str, end_date_str }),
  uploadBhavcopyManual: (formData, requested_date_str) => {
    const query = requested_date_str ? `?requested_date_str=${encodeURIComponent(requested_date_str)}` : '';
    return api.post(`/ingestion/upload${query}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getIngestionLogs: (params) => api.get('/ingestion/logs', { params }),
  
  // Admin & System
  getSystemConfig: () => api.get('/admin/config'),
  resetDatabase: () => api.post('/admin/reset'),
};

export default api;

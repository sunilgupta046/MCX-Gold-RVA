export const CONTRACTS = {
  GOLDM: {
    symbol: 'GOLDM',
    name: 'Gold Mini',
    unitGrams: 100,
    quoteGrams: 10,
    multiplier: 10,
    tickSize: 1,
    color: '#eab308', // Gold
  },
  GOLDTEN: {
    symbol: 'GOLDTEN',
    name: 'Gold Ten',
    unitGrams: 10,
    quoteGrams: 10,
    multiplier: 1,
    tickSize: 1,
    color: '#06b6d4', // Cyan
  },
  GOLDGUINEA: {
    symbol: 'GOLDGUINEA',
    name: 'Gold Guinea',
    unitGrams: 8,
    quoteGrams: 8,
    multiplier: 1,
    tickSize: 1,
    color: '#8b5cf6', // Purple
  },
  GOLDPETAL: {
    symbol: 'GOLDPETAL',
    name: 'Gold Petal',
    unitGrams: 1,
    quoteGrams: 1,
    multiplier: 1,
    tickSize: 1,
    color: '#10b981', // Emerald
  },
};

export const PAIRS = [
  { id: 'GOLDM_vs_GOLDPETAL', label: 'GOLDM vs GOLDPETAL', base: 'GOLDM', quote: 'GOLDPETAL' },
  { id: 'GOLDM_vs_GOLDGUINEA', label: 'GOLDM vs GOLDGUINEA', base: 'GOLDM', quote: 'GOLDGUINEA' },
  { id: 'GOLDM_vs_GOLDTEN', label: 'GOLDM vs GOLDTEN', base: 'GOLDM', quote: 'GOLDTEN' },
  { id: 'GOLDGUINEA_vs_GOLDPETAL', label: 'GOLDGUINEA vs GOLDPETAL', base: 'GOLDGUINEA', quote: 'GOLDPETAL' },
];

export const DARK_PLOT_LAYOUT = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: {
    family: 'Plus Jakarta Sans, sans-serif',
    color: '#94a3b8',
    size: 11,
  },
  margin: { l: 55, r: 25, t: 30, b: 40 },
  xaxis: {
    gridcolor: 'rgba(255, 255, 255, 0.05)',
    zerolinecolor: 'rgba(255, 255, 255, 0.1)',
  },
  yaxis: {
    gridcolor: 'rgba(255, 255, 255, 0.05)',
    zerolinecolor: 'rgba(255, 255, 255, 0.1)',
  },
  hoverlabel: {
    bgcolor: '#0f172a',
    bordercolor: '#334155',
    font: { family: 'JetBrains Mono, monospace', color: '#f8fafc', size: 12 },
  },
};

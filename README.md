# MCX Gold RVA — Relative Value Analytics Platform
**Developed for the COZY NEXUS Quantitative Systems Team**

A production-grade quantitative finance platform designed to identify, analyze, and backtest relative pricing differences between MCX Gold futures contracts (`GOLDM`, `GOLDTEN`, `GOLDGUINEA`, and `GOLDPETAL`) using daily public Bhavcopy settlement data.

---

## 📊 Key Highlights & Architecture

- **Standardized Microstructure Parity**: Normalizes diverse physical delivery sizes (100g Mini, 10g Ten, 8g Guinea, 1g Petal) into equivalent per-gram (₹/g) and per-10-gram (₹/10g) pricing.
- **Cost of Carry Alignment**: Adjusts for maturity horizon differentials via continuous financing ($r \approx 6.5\%$ repo proxy) and vault storage/insurance ($s \approx 0.5\%$).
- **Statutory Friction Engine**: Accurately accounts for MCX Exchange Turnover Fees (0.0021%), SEBI charges (0.0001%), GST (18%), CTT (0.01% on sell side), Stamp Duty (0.002% on buy side), and bid-ask slippage.
- **Mean-Reversion Signal Center**: Generates statistical arbitrage alerts based on 20-day rolling Z-scores ($\pm 2.0\sigma$ entry, $\pm 0.5\sigma$ convergence exit, $\pm 3.5\sigma$ stop loss) with net-edge hurdles.
- **Backtesting Lab**: Event-driven backtester with Sharpe, Sortino, Max Drawdown, Win Rate, and trade execution ledgers.
- **Data Quality Audit**: Automated health scoring, missing trading day detection, and price jump outlier flags.
- **Strict Compliance**: Synthetic/demo datasets are explicitly labeled throughout; paper-trading/analytics only (no live order routing).

```
                      ┌────────────────────────────────────────┐
                      │    MCX Gold Bhavcopy Ingestion Engine  │
                      │  (Public CSV Parser / Demo Generator)  │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    Standardization & Normalization     │
                      │  (Per-Gram & Per-10g Price Multipliers)│
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    Cost of Carry Term Adjustment       │
                      │   (Financing Rate & Storage Yield)     │
                      └───────────────────┬────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
    ┌───────────────────────────┐                   ┌───────────────────────────┐
    │  Spread Analytics Engine  │                   │  Friction & Cost Modeler  │
    │ (Z-Score, Half-Life, Corr)│                   │ (Exchange, CTT, GST, Slip)│
    └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │     Signal Generator & Backtester      │
                      │   (Entry/Exit Hurdles, PnL, Drawdown)  │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │   FastAPI Endpoints / PostgreSQL / UI  │
                      │ (Dark Navy React + Vite + Plotly.js)   │
                      └────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite 6, Tailwind CSS, Plotly.js (`react-plotly.js`), Lucide Icons, Axios |
| **Backend** | Python 3.11+, FastAPI, Pydantic V2, SQLAlchemy 2.0, Alembic, Uvicorn |
| **Analytics** | Pandas, NumPy, SciPy |
| **Database** | PostgreSQL 16 (Production / Docker) & SQLite (Zero-config local development) |
| **Testing** | Pytest, FastAPI TestClient |
| **DevOps** | Docker Compose, Multi-stage Dockerfiles |

---

## 🪙 Contract Microstructure & Normalization Specs

| Symbol | Contract Name | Trading Unit | Quotation Unit | Multiplier | Price per Gram Formula |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `GOLDM` | Gold Mini | 100 grams | ₹ / 10g | 10 | $\text{Settlement Price} / 10$ |
| `GOLDTEN` | Gold Ten | 10 grams | ₹ / 10g | 1 | $\text{Settlement Price} / 10$ |
| `GOLDGUINEA` | Gold Guinea | 8 grams | ₹ / 8g | 1 | $\text{Settlement Price} / 8$ |
| `GOLDPETAL` | Gold Petal | 1 gram | ₹ / 1g | 1 | $\text{Settlement Price} / 1$ |

**Standardized 10g Price**:
$$\text{Price}_{10\text{g}} = \text{Price}_{\text{gram}} \times 10.0$$

---

## 📐 Mathematical Formulation

### 1. Cost of Carry Adjustment
When comparing contracts with different days to expiry ($T_A$ and $T_B$), the calendar difference induces carry costs:
$$F(T) = S \cdot \left(1 + C \cdot \frac{T}{365}\right)$$
$$\text{Carry Adjusted Price } P^{\text{adj}} = P(T) \cdot \frac{1 + C \cdot \frac{T_{\text{benchmark}}}{365}}{1 + C \cdot \frac{T}{365}}$$
Where $C = r_{\text{repo}} + s_{\text{storage}} \approx 6.5\% + 0.5\% = 7.0\%$.

### 2. Rolling Z-Score & Statistical Mispricing
$$\mu_t = \frac{1}{N}\sum_{i=0}^{N-1} \text{Spread}_{t-i}, \quad \sigma_t = \sqrt{\frac{1}{N-1}\sum_{i=0}^{N-1} (\text{Spread}_{t-i} - \mu_t)^2}$$
$$Z_t = \frac{\text{Spread}_t - \mu_t}{\sigma_t}$$

### 3. Mean Reversion Half-Life (Ornstein-Uhlenbeck)
Estimated via linear regression of spread differentials:
$$\Delta S_t = \lambda (S_{t-1} - \mu) + \epsilon_t \implies \text{Half-Life} = \frac{-\ln(2)}{\lambda}$$

---

## 🔬 Walk-Forward Backtesting Engine

The platform features an institutional-grade, event-driven pair trading backtest engine designed to rigorously evaluate whether relative-value mispricings survive realistic market friction without look-ahead bias.

### 1. Zero Look-Ahead Bias & Chronological Execution
- All rolling statistics ($\mu_t, \sigma_t, Z_t$) are strictly computed over backward-looking windows ($[t-W+1, t]$).
- Future spread values, future expiries, or future volatility are never leaked into historical trading decisions.

### 2. Temporal Partitioning (3-Way Split & Rolling Folds)
- **3-Way Chronological Partition**: Divides historical series into In-Sample Training (50%), In-Sample Validation (25%), and Out-of-Sample Test (25%).
- **Multi-Fold Rolling Walk-Forward**: Iteratively trains parameters over fixed rolling memory blocks and tests performance strictly on the subsequent unseen out-of-sample forward window.
- Independent performance metrics (Net Return, Gross Return, Sharpe, Win Rate, Drawdown) are measured and reported for each split phase.

### 3. Realistic Fill Modeling vs. Settlement Quotes
- Exchange Bhavcopy files record official settlement prices. Actual market execution incurs bid-ask friction.
- The engine models entry and exit fills distinctly from settlement quotes using configurable per-leg slippage:
  - **Long Base / Short Quote Entry**:
    $$\text{Base Fill} = \text{Settle}_{\text{base}} + \Delta_{\text{slippage, base}}$$
    $$\text{Quote Fill} = \text{Settle}_{\text{quote}} - \Delta_{\text{slippage, quote}}$$
  - **Exit Execution**: Reciprocal slippage penalties applied to both legs.

### 4. Metal Delta-Neutral Position Sizing
- MCX contracts differ in trading unit, quotation unit, and chemical fineness:
  - `GOLDM`: 100 grams @ 995 fineness $\implies 99.5\text{g pure gold}$
  - `GOLDPETAL`: 1 gram @ 999 fineness $\implies 0.999\text{g pure gold}$
  - `GOLDGUINEA`: 8 grams @ 999 fineness $\implies 7.992\text{g pure gold}$
  - `GOLDTEN`: 10 grams @ 999 fineness $\implies 9.99\text{g pure gold}$
- Sizing dynamically computes contract quantities to achieve **pure metal delta neutrality**, preventing unhedged physical directional exposure:
  $$\text{Ratio} = \frac{\text{Grams}_{\text{base}} \times (\text{Purity}_{\text{base}}/1000)}{\text{Grams}_{\text{quote}} \times (\text{Purity}_{\text{quote}}/1000)}$$
  For example, 1 lot of `GOLDM` is paired with exactly 100 lots of `GOLDPETAL`.

### 5. Expiry Tender Lockout & Forced Expiry Handling
- **Tender Delivery Lockout (`expiry_lockout_days`, default: 5 days)**: MCX physical delivery intentions begin 5 days prior to expiration. New spread positions are strictly locked out from opening when either contract has $\le 5$ days to expiry.
- **Forced Expiry Exit (`FORCED_EXPIRY_EXIT`)**: Open positions that reach 1 day to expiry are mandatorily closed at modeled exit fills, preventing physical delivery obligations.

### 6. Configurable Liquidity & Volume Filters
- Trades are rejected if trading volume is below `min_volume_lots` or open interest is below `min_open_interest`, avoiding illiquid contract traps.

### 7. Itemized Statutory MCX Cost Schedule
Itemized costs are calculated on every individual leg transaction:
- **Brokerage**: Flat ₹20 per lot (or configurable).
- **Exchange Turnover Fee**: $0.0021\%$ of contract turnover.
- **SEBI Turnover Fee**: $0.0001\%$ of contract turnover.
- **Commodities Transaction Tax (CTT)**: $0.01\%$ on **sell side turnover only**.
- **Stamp Duty**: $0.002\%$ on **buy side turnover only**.
- **Goods and Services Tax (GST)**: $18\%$ levied on $(\text{Brokerage} + \text{Exchange Fee} + \text{SEBI Fee})$.
- **Slippage**: Configurable per-leg tick slippage.

### 8. Gold Benchmark & Beta ($\beta$) Calculation
- Strategy daily equity is benchmarked against Buy-and-Hold Gold Mini.
- **Gold Beta ($\beta$)** measures systematic market exposure:
  $$\beta = \frac{\text{Cov}(R_{\text{strategy}}, R_{\text{gold}})}{\text{Var}(R_{\text{gold}})}$$
  True relative value statistical arbitrage maintains market neutrality ($|\beta| \approx 0.0$).

### 9. Multi-Scenario Parameter Sensitivity Grid
- Interactive 4-dimensional sensitivity analysis:
  - **Slippage Sensitivity**: $0, 1, 2, 3$ ticks
  - **Cost Multiplier Sensitivity**: $0.5\times, 1.0\times, 1.5\times, 2.0\times$ statutory fees
  - **Entry Z-Score Threshold**: $1.5\sigma, 2.0\sigma, 2.5\sigma, 3.0\sigma$
  - **Cost of Carry Financing Rate**: $5.0\%, 7.0\%, 9.0\%$

### 10. Auditability & CSV Data Export
- Every backtest saves a complete reproducible `config_snapshot` JSON and database run ID.
- **Export Trades CSV**: Downloadable ledger with per-trade entry/exit dates, settle vs. fill prices, lots, gross PnL, itemized fees, slippage, and net PnL (`GET /api/backtest/{id}/export/trades.csv`).
- **Export Daily Equity CSV**: Downloadable daily time-series with Net Equity, Gross Equity, Benchmark Gold Equity, Cash, and Split Phase (`GET /api/backtest/{id}/export/equity.csv`).

---

## 🔔 Quiet Alerts & Signal Center

The Signal Center incorporates noise-suppression mechanisms to filter out transient micro-spreads:
- **Net Edge Hurdle**: Spread divergence must exceed estimated double-round-trip transaction friction + required net profit hurdle ($\ge 5\text{ bps}$).
- **Hysteresis Exit**: Prevents rapid thrashing around the mean by requiring spread reversion inside $\pm 0.5\sigma$.
- **Quiet Mode**: Suppresses low-conviction signals and flags only institutional-grade opportunities.

---

## 🖥 Frontend Modules (8 Pages)

1. **Dashboard**: High-level platform health, benchmark GOLDM live pricing, active RVA alerts, top divergence pair, normalized price mini-chart, and live spread matrix.
2. **Contract Explorer**: Microstructure specifications, lot size economics, normalization formula breakdown, and historical Volume/OI charts for all 4 contracts.
3. **Relative Value Analytics**: Interactive Plotly spread charts with rolling $\pm 2.0\sigma$ bands, Z-score oscillators, forward carry curve, and cross-contract correlation heatmap.
4. **Backtesting Lab**: Quantitative strategy parameter tuner (entry Z, exit Z, stop loss Z, friction toggle) with dynamic equity curves, underwater drawdown series, and trade execution ledger.
5. **Signal Center**: Real-time actionable arbitrage board with filters by pair, strength, and status, showing gross vs. net edge (bps) after all statutory MCX costs.
6. **Bhavcopy Ingestion**: Official MCX Bhavcopy ingestion engine supporting single date selection (`DD/MM/YYYY`), historical date ranges, manual CSV upload, date mismatch protection, compact expiry parsing, and real-time audit ledger.
7. **Data Quality**: Bhavcopy integrity audit with health scores (0-100%), missing business dates detector, price jump outlier flags, and anomaly severity logs.
8. **Admin Panel**: Official public Bhavcopy CSV ingestion uploader, calibrated synthetic demo data generator, cost parameter inspector, and database reset tool.

---

## 📥 MCX Daily Bhavcopy Ingestion Engine

### Ingestion Source & Compliance
- **Official Source**: `https://www.mcxindia.com/market-data/bhavcopy`
- **Configurable Adapter**: Implements an HTTP adapter using `httpx` with realistic browser headers and transport error handling. If direct automated download is challenged by the exchange WAF/Akamai rules (HTTP 403), the system logs the session diagnostics and provides seamless manual CSV upload.
- **Date Format Rules**:
  - Requested dates parsed in strict `DD/MM/YYYY` format (also accepts ISO `YYYY-MM-DD`).
  - Source response dates parsed according to actual format (`DD/MM/YYYY`, `MM/DD/YYYY`, `YYYY-MM-DD`, `DD-Mon-YYYY`).
  - Compact ExpiryDate parsed accurately (e.g., `04SEP2026`, `27NOV2024`, `05OCT26`, `04-SEP-2026`).
  - Trims whitespace from symbol values (`"  GOLDM  "` $\rightarrow$ `"GOLDM"`).
  - Target contract identification: strictly isolates `GOLDM`, `GOLDTEN`, `GOLDGUINEA`, and `GOLDPETAL`.
- **Zero Silent Date Substitution (Rule 9)**:
  - Validates requested date against returned settlement date.
  - If returned date does not match requested date, the file is rejected with `REJECTED_DATE_MISMATCH` and logged.
- **Idempotency & Contract Preservation**:
  - Records deduplicated using `(symbol, trade_date, expiry_date)`.
  - Preserves historical contracts by distinct `expiry_date`; never stitches a continuous near-month series.
  - Re-importing existing records performs an idempotent upsert without duplicating rows.

### Ingestion API Endpoints
- `POST /api/ingestion/fetch-date`: Fetch daily Bhavcopy for a single date (`date_str: "DD/MM/YYYY"`).
- `POST /api/ingestion/fetch-range`: Batch sequential fetch across historical date range (`start_date_str`, `end_date_str`).
- `POST /api/ingestion/upload`: Manual CSV file upload with optional expected date validation guard.
- `GET /api/ingestion/status`: Aggregated summary (successful, rejected, holiday/weekend, unavailable, error sessions).
- `GET /api/ingestion/logs`: Historical ingestion audit logs with status filter.

---

## 🚀 Quickstart Guide

### Option A: Local Development (Instant Zero-Config Setup)

#### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment (optional)
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate    # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Configure Environment & Database:
# Copy .env.example to .env
cp .env.example .env

# Database Options in .env:
# 1) SQLite (Zero configuration, default):
#    DATABASE_URL=sqlite:///./mcx_gold_rva.db
# 2) PostgreSQL (Local instance):
#    DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/mcx_gold_rva

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend Swagger Docs will be available at:* `http://127.0.0.1:8000/docs`

If the default ports are already in use, start the backend on `8001`:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

#### 2. Frontend Setup
```bash
cd frontend

# Install npm packages
npm install

# Start Vite dev server
npm run dev
```
*Frontend will be running at:* `http://127.0.0.1:5173/`

The frontend sends API requests to `/api`; Vite proxies them to
`http://localhost:8000` by default. If the backend runs elsewhere, set
`VITE_API_PROXY_TARGET` in `frontend/.env.local` to its origin, for example
`http://192.168.1.20:8000`. For a separately hosted API, set
`VITE_API_BASE_URL` to the API base URL (including `/api`) and configure the
backend's `CORS_ORIGINS` to allow the frontend origin.

For example, if using backend port `8001` and frontend port `5175` in
PowerShell:
```powershell
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5175
```

The local run uses the configured SQLite database and persists data in the
backend database file. Docker Compose instead runs PostgreSQL; the local
SQLite database is not the Docker PostgreSQL instance.

---

### Option B: Docker Compose (PostgreSQL + Backend + Frontend)

Ensure Docker Desktop is running, then execute from the project root:

```bash
docker compose up --build -d
```

- **Frontend Application**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432` (`mcx_gold_rva`)

To stop services:
```bash
docker compose down
```

---

## 🧪 Automated Testing (47 Tests Passing)

Run the full automated test suite from the `backend/` directory:

```bash
cd backend
pytest -v
```

The test suite (47 passed in ~3.2s) validates:
- **Signal Qualification & Alert Engine (7 tests)**: Validates 999-fineness basis normalization, expected gross edge vs. itemized roundtrip costs, expected net edge, the mandatory 2.5x total cost multiplier rule ($\text{Gross Edge} \ge 2.5 \times \text{Costs}$), positive net edge requirement, T-5 physical tender lockout, liquidity and data-quality filters, deduplication, rejection reasons audit logging, and zero fabrication.
- **Zero Look-Ahead Bias**: Tests that expanding-window statistics and backtest decisions never inspect future data.
- **Itemized Transaction Costs**: Validates exact rupee calculations for Brokerage, Exchange Turnover Fee, SEBI Fee, CTT (sell leg only), Stamp Duty (buy leg only), and 18% GST.
- **Metal Delta-Neutral Position Sizing**: Validates contract ratio balancing for `GOLDM`, `GOLDTEN`, `GOLDGUINEA`, and `GOLDPETAL` taking into account quotation units, trading units, and chemical fineness.
- **Modeled Fills vs Settlement**: Verifies bid-ask slippage application on entries and exits.
- **Expiry Lockout & Forced Expiry**: Validates that trades inside the tender delivery lockout window are blocked and expiring contracts are exited before physical tender.
- **Gross vs Net P&L Separation**: Ensures that gross alpha and net performance after friction are tracked distinctly.
- **Gold Beta & Benchmark Returns**: Verifies portfolio beta calculation against buy-and-hold gold mini.
- **Sensitivity Analysis Grid**: Tests multi-scenario perturbation across slippage, cost multipliers, entry Z, and carry rates.
- **CSV Data Exports**: Verifies `trades.csv` and `equity.csv` generation and streaming.
- **Price Normalization & Carry Curves**: 999-fineness basis conversion, continuous financing, and storage rate discounting.
- **MCX Bhavcopy Ingestion**: Verifies strict date matching, rejection of mismatched dates, compact expiry parsing (`04SEP2026`), whitespace trimming, and idempotent deduplication.

---

## ⚠️ Compliance & Data Integrity Notice

- **Paper Analysis Only**: This platform is designed strictly for quantitative relative value analytics and backtesting. No live trade execution or broker order routing is implemented.
- **Demo Data Provenance**: Any demo records generated via the Admin Panel are produced using stochastic Brownian random walks calibrated to recent gold price levels and are clearly tagged with `is_demo=True` and visual banners.
- **Official Bhavcopy**: Real exchange analysis can be performed by uploading official public Bhavcopy CSV files via the Admin Panel.

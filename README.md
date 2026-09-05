# Stock Signal Engine

A production-quality stock analysis and candlestick-pattern alert application.
It continuously monitors a watchlist across multiple timeframes, detects
candlestick patterns, filters them through a configurable multi-factor
quality score (trend, volume, support/resistance, momentum, risk/reward,
company news, market regime, sector context), and generates an alert
**only** for setups that clear a configurable minimum score — with entry,
stop-loss, three targets, and risk:reward for each.

**This is an analytical tool, not a trading system.** Every signal is an
estimate based on historical price action and available news/market data at
the time it was generated — never a guaranteed prediction or investment
recommendation. See "Known limitations" below.

The product principle driving every design decision here: **fewer, higher
quality signals** beat a firehose of every textbook pattern. A raw pattern
match on its own never produces an alert — see "Signal scoring methodology".

---

## What the application does

1. Polls a user-configurable watchlist (any US ticker) on a user-configurable
   set of timeframes (1m/5m/15m/30m/1h/4h/1d).
2. On every fully-closed candle, runs 18 candlestick pattern detectors
   (7 bullish, 7 bearish, 4 neutral/structural).
3. Confirms a match against trend, volume, support/resistance, momentum,
   risk:reward, recent company news (sentiment + severity), broader market
   regime (S&P 500/VIX), and sector trend.
4. Combines all of the above into a single 0-100 quality score using
   configurable weights, and classifies it (Exceptional/Strong/Good/
   Watch/Ignore).
5. If the score clears the configured minimum (default 70) and nothing
   suppresses it (e.g. CRITICAL conflicting news), it computes entry/
   stop-loss/three targets from ATR and support/resistance, deduplicates
   against recent alerts, persists a `Signal`, and dispatches it to every
   enabled notification channel (in-app, email, Telegram — architected so
   SMS/Discord/Slack/push can be added later).
6. Everything is stored so any signal can be fully explained/reproduced
   later, and the same detector/scoring pipeline can be replayed against
   historical data for backtesting.

---

## Architecture

```
Frontend (React/Vite)
        │  REST (fetch)
        ▼
REST API (FastAPI, app/api/routers/*)
        │
        ▼
Analysis / Signal Engine
   app/patterns    — 18 candlestick detectors, independently testable
   app/indicators  — SMA/EMA/RSI/MACD/ATR/volume/support-resistance/trend
   app/news        — news provider abstraction + VADER sentiment + severity
   app/market_context — SPY/VIX-based market regime, sector trend
   app/scoring     — configurable weighted scoring engine
   app/risk        — entry/stop/target calculator (ATR + S/R based)
   app/alerts      — candle-close confirmation, dedup, formatting, channels
   app/scheduler   — orchestration pipeline + APScheduler polling jobs
   app/backtesting — replays the same pipeline against historical data
        │
        ▼
Market Data Layer (app/market_data) — MarketDataProvider abstraction
        │
        ▼
Database (SQLAlchemy models, app/models) — SQLite (dev) / PostgreSQL (docker)
```

Each layer only depends on the abstraction of the layer below it
(`MarketDataProvider`, `NewsProvider`, `NotificationChannel`, `PatternDetector`),
so any of them can be swapped or extended without touching the others — see
the "Adding a new ..." sections below. The notification service
(`app.alerts.notifier`) is intentionally independent of the scoring engine:
a failed email/Telegram send can never affect signal generation, and a
scoring bug can never crash a notification.

## Technology stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic | async-friendly, typed, mature ORM/migration story |
| Scheduler | APScheduler (in-process) | simplest thing that works for an MVP; see "Known limitations" for the production alternative |
| Database | SQLite (local dev/tests) / PostgreSQL (docker-compose) | zero-config locally, real RDBMS in "production" |
| Market data | `yfinance` (default, free, no key) | see provider evaluation below |
| News | NewsAPI.org (default) + VADER sentiment | free tier, aggregates broad sources, no ML infra needed |
| Frontend | React 18, TypeScript, Vite, Tailwind, lightweight-charts | fast dev loop, small bundle, TradingView-quality charts |
| Tests | pytest, pytest-cov, freezegun | 135 tests across detectors/indicators/scoring/risk/alerts/API |
| Containers | Docker, docker-compose | one-command startup |

### Market-data provider evaluation

| Provider | Free tier | Intraday | Notes |
|---|---|---|---|
| **yfinance (default)** | Unlimited, no key | Yes (1m limited to 7d, others to 60d) | Unofficial Yahoo Finance wrapper; no formal SLA/licensing for commercial use — fine for personal/analytical use, evaluate licensing before commercial redistribution |
| Alpha Vantage | 25 req/day, 5/min | Yes, but tiny free quota | Best for daily-only watchlists on the free tier |
| Finnhub | 60 req/min | Real-time quotes; candles need a paid plan for most US equities | Great for latest-price lookups |
| Polygon.io | None (paid only for real-time) | Excellent, 2yr+ history | Best licensing/depth for production, needs a paid plan |
| Twelve Data | 8 req/min, 800/day | Solid unified API | Good middle ground |

All five are fully implemented behind `MarketDataProvider` (`app/market_data/`)
— switch with `MARKET_DATA_PROVIDER` in `.env`, no code changes required.

### News-provider evaluation

NewsAPI.org's free "Developer" tier (100 req/day, articles capped at ~1 month
old, **development/testing use only** per their terms — evaluate a paid plan
before production use) is the default. `NEWS_PROVIDER=none` (or simply no API
key) makes every signal explicitly show "News unavailable — technical
analysis only" rather than silently skipping the check — the app never
pretends news was checked when it wasn't (`app/news/null_provider.py`).

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app assembly + lifespan (DB init, scheduler)
│   │   ├── core/                  # config, logging, database session
│   │   ├── models/                # SQLAlchemy models (one file per aggregate)
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── market_data/           # MarketDataProvider + 5 adapters + factory
│   │   ├── indicators/            # pure indicator math, no side effects
│   │   ├── patterns/              # 18 candlestick detectors + registry
│   │   ├── news/                  # NewsProvider + sentiment + severity + analysis
│   │   ├── market_context/        # market regime (SPY/VIX) + sector mapping
│   │   ├── scoring/                # configurable weighted scoring engine
│   │   ├── risk/                   # entry/stop/target calculator
│   │   ├── alerts/                # candle-close, dedup, formatter, channels, notifier
│   │   ├── scheduler/              # orchestration pipeline + APScheduler jobs
│   │   ├── backtesting/            # historical replay engine + metrics
│   │   └── api/routers/            # watchlist, signals, alerts, settings, status, market-data
│   ├── tests/                      # 135 tests, mirrors the app/ structure
│   ├── alembic/                    # migrations (one generated "initial schema" revision)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/pages/                  # Dashboard, Watchlist, StockDetail, SignalDetail, Settings
│   ├── src/components/             # Layout, SignalCard, Badge, DisclaimerBanner
│   ├── src/api/client.ts           # thin fetch wrapper
│   └── Dockerfile                  # multi-stage build -> nginx
├── scripts/run_backtest.py         # backtesting CLI
├── docker-compose.yml
├── .env.example
└── README.md (this file)
```

---

## Setup (local, without Docker)

Requires Python 3.11+ and Node 20+.

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env        # edit as needed - every value has a safe default
alembic upgrade head              # creates ./data/app.db (SQLite) or your configured DB
uvicorn app.main:app --reload     # http://localhost:8000  (also starts the polling scheduler)

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env              # VITE_API_BASE_URL=http://localhost:8000
npm run dev                       # http://localhost:5173
```

### Environment variables

See `.env.example` for the full, commented list. Nothing is required to
start the app — every setting has a safe default (`yfinance` for market
data, SQLite for the database, no news provider configured, in-app
notifications only). Add API keys as you get them:

- `MARKET_DATA_PROVIDER` + the matching `*_API_KEY` to switch providers.
- `NEWSAPI_API_KEY` to enable news-aware scoring.
- `SMTP_*` / `ALERT_EMAIL_*` to enable email alerts.
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` to enable Telegram alerts
  (create a bot via @BotFather, then message it and hit
  `https://api.telegram.org/bot<token>/getUpdates` to find your chat id).

**Never commit `.env`** — it's gitignored. `.env.example` has no secrets.

### Database setup

SQLite is the zero-config default (`./backend/data/app.db`). Migrations are
managed with Alembic:

```bash
cd backend
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "describe your change"   # after changing a model
```

`init_db()` (`app.core.database`) also exists as a `create_all`-based
fallback used by the test suite for speed; production/dev should use
Alembic so schema history is tracked.

## Running with Docker

```bash
cp .env.example .env      # edit as needed
docker compose up --build
```

This starts PostgreSQL, the backend (migrations run automatically on
container start, then the API + in-process scheduler), and the frontend
(built and served via nginx, proxying `/api/*` to the backend). Frontend:
http://localhost:5173, API: http://localhost:8000, API docs:
http://localhost:8000/docs.

> Docker builds require network access to PyPI/npm; this repository was
> developed in a sandboxed environment without direct Docker daemon access,
> so the Dockerfiles/compose file are validated by `docker compose config`
> and careful review, but a full `docker compose up` build has not been run
> end-to-end from this environment. Please run it once locally and open an
> issue/adjust if anything doesn't build cleanly for your platform.

## Adding stocks / configuring alerts

Via the UI: **Watchlist** page → type a ticker → Add. Per-stock you can
toggle monitoring, pick timeframes, override the minimum score, restrict
which patterns are enabled, and choose notification channels — anything
left unset falls back to the global default (**Settings** page).

Via the API:

```bash
curl -X POST http://localhost:8000/api/watchlist \
  -H 'Content-Type: application/json' \
  -d '{"symbol": "NVDA", "timeframes": ["15m", "1h", "1d"], "min_score_override": 75}'
```

Global scoring weights, classification thresholds, and risk policy
(including whether CRITICAL conflicting news suppresses alerts outright)
are edited on the **Settings** page or via `GET/PUT /api/settings/scoring`.

---

## Signal scoring methodology

```
Score = pattern(25) + trend(15) + volume(10) + support/resistance(10)
      + momentum(10) + risk:reward(10) + news(10) + macro(5) + sector(5)
      = 100 points, weights fully configurable (Settings page or
        GET/PUT /api/settings/scoring)

90-100 = Exceptional   80-89 = Strong   70-79 = Good
60-69  = Watch         <60   = Ignore (never alerted)
```

- **Pattern (0-25)**: the detector's own shape-quality confidence (e.g. how
  cleanly a Bullish Engulfing's body exceeds the prior candle's).
- **Trend (0-15)**: does the post-pattern trend/momentum structure (MA
  ordering, EMA9/21 alignment, higher-highs/higher-lows vs lower-highs/
  lower-lows) align with the signal's direction.
- **Volume (0-10)**: relative volume vs the 20-bar average (1.0x = 0 points,
  2.0x+ = full points).
- **Support/resistance (0-10)**: is the pattern forming at/breaking through
  a meaningful level.
- **Momentum (0-10)**: RSI positioning + MACD histogram direction.
- **Risk:reward (0-10)**: scaled from the configured minimum R:R (default
  1.2) up to 3.0R.
- **News (0-10, signed)**: `app.news.analysis.analyze_news_context` weighs
  recent company headlines by severity and recency, aligns sentiment with
  the setup's direction, and returns supportive/conflicting/neutral/
  unavailable plus a signed point adjustment.
- **Macro (0-5)**: does the broader market regime (`app.market_context.regime`,
  SPY trend + VIX level) support this direction; high-volatility regimes
  apply an additional 15% dampening to the *total* score.
- **Sector (0-5)**: does the mapped sector ETF's trend agree.

**Suppression**: a CRITICAL-severity news item that conflicts with the
signal's direction (bankruptcy, fraud, trading halt, guidance withdrawal,
etc. — see `app/news/sentiment.py:SEVERITY_KEYWORDS`) either heavily
discounts the score (conflicting-but-not-critical: ×0.7; critical: ×0.4) or,
if `risk_policy.suppress_on_critical_conflict` is enabled (default), the
signal is stored with `status=suppressed` and **never notified** —
regardless of how strong the technical setup looked.

---

## Adding a new candlestick pattern

1. Add a `PatternDetector` subclass to `app/patterns/bullish.py`,
   `bearish.py`, or `neutral.py` (or a new module) implementing `detect(df)
   -> PatternMatch | None`. Use the geometry helpers in `app/patterns/base.py`
   (`body`, `upper_shadow`, `lower_shadow`, `avg_body`, etc.).
2. Append an instance to that module's `_DETECTORS` list.
3. If it's a new module, import its list into `app/patterns/registry.py`'s
   `ALL_DETECTORS`.
4. Add positive + negative tests in `backend/tests/test_patterns/`
   (see any existing test file for the pattern — every test builds a small,
   deterministic synthetic OHLCV window via `tests/fixtures/ohlcv.py`).

Nothing else changes — the scoring engine, API (`/api/settings/patterns`),
and watchlist per-symbol "enabled patterns" all key off `pattern_key`
strings from the registry automatically.

## Adding a new market-data provider

Implement `MarketDataProvider` (`app/market_data/base.py`): `get_ohlcv(symbol,
timeframe, lookback_bars)` returning a UTC-indexed DataFrame with
`open/high/low/close/volume`, and `get_latest_price(symbol)`. Register it in
`app/market_data/factory.py`'s `_PROVIDERS` dict, add its API key setting to
`app/core/config.py` and `.env.example`, then set `MARKET_DATA_PROVIDER` in
`.env`. See `app/market_data/stub_providers.py` for four complete examples
(Alpha Vantage, Finnhub, Polygon, Twelve Data).

## Adding a new notification provider

Implement `NotificationChannel` (`app/alerts/channels/base.py`): `send(alert)
-> (NotificationStatus, error, rendered_text)`. Add an entry to
`CHANNEL_REGISTRY` in `app/alerts/notifier.py`, add a `NotificationChannelType`
enum value (`app/models/enums.py`), and its credentials to `.env.example`.
The reserved-but-unimplemented enum values (`sms`, `discord`, `slack`, `push`)
show the intended pattern.

## Running tests

```bash
cd backend
pip install -r requirements.txt      # includes pytest, pytest-cov, freezegun
pytest                                # 135 tests
pytest --cov=app --cov-report=term-missing   # coverage report (currently ~82%)
```

Tests cover: every candlestick detector (positive + negative cases against
deterministic synthetic OHLCV fixtures in `tests/fixtures/ohlcv.py`), every
indicator calculation, the scoring engine (including suppression and
configurable-weight behavior), the risk calculator, candle-close
confirmation, deduplication, alert formatting, notification dispatch, every
API endpoint, the end-to-end scheduler pipeline (against fake market-data/
news providers — no live network required), and the backtesting engine.
Lower-coverage areas are the live-network provider adapters
(yfinance/Alpha Vantage/Finnhub/Polygon/Twelve Data/NewsAPI HTTP calls) and
the APScheduler wiring itself, which are thin and better validated by
running the app than by mocking HTTP calls extensively.

## Backtesting architecture

`app/backtesting/engine.py:run_backtest(df, symbol, timeframe, config)`
walks a historical OHLCV DataFrame bar-by-bar with an expanding window,
running the **exact same** detector → indicator → scoring → risk pipeline
the live scheduler uses, then simulates forward from each qualifying
signal's entry to see whether the stop or one of the three targets is hit
first (conservatively assuming the stop wins ties within the same bar).
`app/backtesting/metrics.py` aggregates win rate, average R, max drawdown,
profit factor, and per-pattern performance.

```bash
python scripts/run_backtest.py NVDA --timeframe 1d --lookback-bars 500
```

**This is a foundation, not a full historical replay**: news and
market-regime context are *not* replayed historically (that would require
storing a historical news + SPY/VIX archive this MVP doesn't fetch), so
those score components are held neutral during backtests — treat backtest
results as a technical-only approximation, not an exact match to what the
live system would have alerted on.

## Known limitations

- **Single-user**: modeled with a `Users` table from day one, but there's no
  auth/login yet — the API always operates as one seeded default user.
  Adding real auth means changing `app.api.deps.get_current_user_id`.
- **In-process scheduler**: APScheduler runs inside the same process as the
  API for simplicity. A real production deployment should split this into a
  separate worker process/container so an API restart doesn't interrupt
  polling, and so polling can scale independently.
- **Daily-candle close detection** uses a fixed 21:00 UTC cutoff as a
  simplification for the US market close (20:00 UTC standard time / 21:00
  UTC daylight time) rather than an exchange-calendar-aware check; fine for
  US equities, would need tightening for other markets/holidays.
- **Sector mapping** (`app/market_context/sector.py`) is a static hardcoded
  table of common large-cap tickers, not sourced from a fundamentals API —
  unmapped symbols degrade gracefully to "Diversified" with neutral sector
  scoring rather than crashing.
- **yfinance** is an unofficial API wrapper with no formal SLA; evaluate a
  paid provider (Polygon is the strongest licensing/depth story) before any
  commercial/production use.
- **NewsAPI.org's free tier is explicitly for development/testing** per its
  terms — evaluate a paid plan or an alternative provider before production
  use of news-aware scoring.
- **Live network calls were not exercised end-to-end** in the environment
  this was built in (sandboxed, restricted egress) — the pipeline was
  validated with fake/mocked providers (135 passing tests) plus a full,
  successful `docker compose config` validation, but you should do one real
  run against live yfinance/NewsAPI/SMTP/Telegram before trusting it
  unattended.
- **Backtesting** does not replay historical news/regime context (see
  above).
- No SMS/Discord/Slack/push notification channels are implemented yet
  (architected for, not built — see "Adding a new notification provider").

---

Analytical tool, not financial advice. Signals are probabilistic estimates
based on historical price action and available news/market data — always do
your own research and manage risk appropriately.

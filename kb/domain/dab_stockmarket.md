# Stock Market Dataset — Knowledge Base

## 1. Dataset Overview
This dataset contains US stock market reference data and historical daily OHLCV price data for thousands of Nasdaq-traded securities, including equities, ETFs, and other instruments.

---

## 2. Databases & Tables

### Database: `query_sqlite_stockmarket_info`
**Table: `stockinfo`**
Contains static reference/metadata for each listed security.

| Field | Type | Description |
|---|---|---|
| `Symbol` | TEXT | Ticker symbol (e.g., `AAAU`, `SPY`) |
| `Nasdaq Traded` | TEXT | `Y`/`N` — whether traded on Nasdaq |
| `Listing Exchange` | TEXT | Exchange code: `Q`=Nasdaq, `P`=NYSE Arca, `N`=NYSE, `A`=NYSE American |
| `Market Category` | TEXT | Nasdaq tier (e.g., `G`=Global Select) or `"Not applicable or not NASDAQ-listed"` |
| `ETF` | TEXT | `Y`/`N` — whether the security is an ETF |
| `Round Lot Size` | REAL | Standard lot size, typically `100.0` |
| `Test Issue` | TEXT | `Y`/`N` — test/dummy listing flag |
| `Financial Status` | TEXT | `N`=normal; nullable for ETFs |
| `NextShares` | TEXT | `Y`/`N` — NextShares product flag |
| `Company Description` | TEXT | Free-text description of the company or fund |

---

### Database: `query_duckdb_stockmarket_trade`
**Structure:** Each table is named after a ticker symbol (e.g., `AAAU`, `SPY`, `QQQ`). There are thousands of such tables.

Each table contains daily trading data with identical schema:

| Field | Type | Description |
|---|---|---|
| `Date` | VARCHAR | Trade date in `YYYY-MM-DD` format (string, not DATE type) |
| `Open` | DOUBLE | Opening price |
| `High` | DOUBLE | Intraday high price |
| `Low` | DOUBLE | Intraday low price |
| `Close` | DOUBLE | Closing price |
| `Adj Close` | DOUBLE | Adjusted closing price (accounts for splits/dividends) |
| `Volume` | BIGINT or DOUBLE | Share volume traded (most are BIGINT; a few tickers use DOUBLE) |

---

## 3. Join Keys
- **Link:** `stockinfo.Symbol` (SQLite) ↔ table name in DuckDB (e.g., `AAAU`)
- Both are uppercase ticker strings with no formatting differences.
- To enrich price data with metadata, join on `stockinfo.Symbol = '<ticker_table_name>'`.

---

## 4. Domain Terms
- **ETF** — Exchange-Traded Fund; `ETF = 'Y'` in stockinfo
- **Adj Close** — Adjusted close price, corrected for corporate actions
- **OHLCV** — Open, High, Low, Close, Volume
- **Listing Exchange codes:** `Q`=Nasdaq, `P`=NYSE Arca, `N`=NYSE, `A`=NYSE American
- **Market Category `G`** — Nasdaq Global Select Market

---

## 5. Known Query Patterns
- **Price history for a ticker:** Query the DuckDB table named by the symbol, filter by `Date`
- **Date filtering:** Cast or compare `Date` as string `YYYY-MM-DD`
- **ETF screening:** Filter `stockinfo` where `ETF = 'Y'`
- **Exchange filtering:** Filter by `Listing Exchange` code
- **Price + metadata:** Join DuckDB ticker table with `stockinfo` on symbol
- **Highest/lowest price in period:** `MAX(High)` / `MIN(Low)` over a date range
- **Volume analysis:** Aggregate `Volume` by date or period
- **Company lookup by description:** `LIKE` search on `Company Description`
- **Return calculation:** Compare `Close` or `Adj Close` across dates
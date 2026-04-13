# Knowledge Base: stockindex Dataset

## 1. Dataset Overview
This dataset tracks historical daily trading data for global stock market indices, including price movements and USD-converted closing values across multiple exchanges and currencies.

---

## 2. Tables

### `index_info` (SQLite — `query_sqlite_stockindex_info`)
Contains reference metadata about stock exchanges.

| Field | Type | Description |
|---|---|---|
| `Exchange` | TEXT | Full name of the stock exchange (e.g., `"New York Stock Exchange"`, `"NASDAQ"`, `"Hong Kong Stock Exchange"`) |
| `Currency` | TEXT | Trading currency for that exchange (e.g., `"USD"`, `"HKD"`) |

- No primary key is defined. `Exchange` acts as the logical identifier.

---

### `index_trade` (DuckDB — `query_duckdb_stockindex_trade`)
Contains daily OHLC price records per stock index.

| Field | Type | Description |
|---|---|---|
| `Index` | VARCHAR | Short ticker/code for the index (e.g., `"HSI"` for Hang Seng Index) |
| `Date` | VARCHAR | Trading date — **inconsistent formats** (see note below) |
| `Open` | DOUBLE | Opening price in local currency |
| `High` | DOUBLE | Intraday high price in local currency |
| `Low` | DOUBLE | Intraday low price in local currency |
| `Close` | DOUBLE | Closing price in local currency |
| `Adj Close` | DOUBLE | Adjusted closing price (accounts for splits/dividends) |
| `CloseUSD` | DOUBLE | Closing price converted to USD |

> ⚠️ **Critical quirk:** The `Date` field is stored as VARCHAR with **mixed formats** across rows, including `"31 Dec 1986, 00:00"`, `"January 02, 1987 at 12:00 AM"`, and `"1987-01-05 00:00:00"`. Date parsing or normalization is required before filtering or sorting by date.

---

## 3. Join Keys
- `index_info.Exchange` links conceptually to `index_trade.Index`, but these are **not directly joinable by value** — `Exchange` is a full name while `Index` is a short code (e.g., `"Hong Kong Stock Exchange"` ↔ `"HSI"`). A mapping table or manual lookup is required.
- `index_info.Currency` can be used alongside `index_trade.CloseUSD` to understand currency conversion context.

---

## 4. Domain Terms
- **OHLC**: Open, High, Low, Close — standard daily price metrics
- **Adj Close**: Adjusted for corporate actions (splits, dividends)
- **CloseUSD**: Normalized close price in US dollars for cross-index comparison

---

## 5. Known Query Patterns
- Historical price trends for a specific index over time
- Cross-index comparison using `CloseUSD`
- Highest/lowest closing prices per index
- Identifying which exchanges trade in which currencies
- Volatility analysis using `High` minus `Low` per day
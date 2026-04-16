# Knowledge Base: Stock Market Dataset (DataAgentBench)

---

## 1. Dataset Overview

This dataset combines U.S. stock/ETF metadata (ticker symbols, exchange listings, financial status, company descriptions) stored in SQLite with historical daily OHLCV price data for 2,753 tickers stored in DuckDB, where each ticker is its own table.

---

## 2. CRITICAL — MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_sqlite_stockmarket_info` | SQLite | Single table: `stockinfo` — metadata for all stocks/ETFs (symbol, exchange, ETF flag, financial status, company description, market category, etc.) |
| `query_duckdb_stockmarket_trade` | DuckDB | 2,754 individual tables named by ticker symbol (e.g., `AAPL`, `MSFT`) — each contains daily OHLCV price history |

---

## 3. Tables and Collections

### Table: `stockinfo` (SQLite via `query_sqlite_stockmarket_info`)

Full description: Contains metadata about publicly traded stocks and ETFs listed on U.S. exchanges, including ticker symbols, market categories, trading venues, and company descriptions.

| Field | Type | Meaning |
|---|---|---|
| `Nasdaq Traded` | TEXT | `'Y'` or `'N'` — whether the stock is traded on NASDAQ |
| `Symbol` | TEXT | Stock ticker symbol (e.g., `AAPL`) — **primary join key to DuckDB tables** |
| `Listing Exchange` | TEXT | Single-letter code for the exchange (see Section 5) |
| `Market Category` | TEXT | Single-letter code for NASDAQ market tier (see Section 5) |
| `ETF` | TEXT | `'Y'` if security is an ETF, `'N'` if not |
| `Round Lot Size` | REAL | Standard trading unit size (typically 100.0) |
| `Test Issue` | TEXT | `'Y'` if this is a test/dummy issue, `'N'` otherwise |
| `Financial Status` | TEXT or NULL | Single-letter code for financial health (see Section 5); can be NULL |
| `NextShares` | TEXT | NextShares designation flag |
| `Company Description` | TEXT | Full company name and description — **use this for human-readable company names** |

**Important value formats:**
- All flag fields (`Nasdaq Traded`, `ETF`, `Test Issue`, `NextShares`) use `'Y'`/`'N'` strings, not booleans.
- `Financial Status` can be NULL (not the same as `'N'` for Normal).
- `Symbol` is plain uppercase text with no prefix/suffix.

---

### Tables: `[TICKER]` (DuckDB via `query_duckdb_stockmarket_trade`)

Full description: 2,754 individual tables, each named after a ticker symbol, containing historical daily trading data.

| Field | Type | Meaning |
|---|---|---|
| `Date` | TEXT (str) | Trading date — stored as a string, format `YYYY-MM-DD` |
| `Open` | FLOAT | Opening price for the trading day |
| `High` | FLOAT | Highest price reached during the day |
| `Low` | FLOAT | Lowest price during the day |
| `Close` | FLOAT | Closing price |
| `Adj Close` | FLOAT | Adjusted closing price (accounts for splits, dividends) |
| `Volume` | INT | Number of shares traded that day |

**Important value formats:**
- `Date` is stored as TEXT in `YYYY-MM-DD` format. Use string comparison or `CAST(Date AS DATE)` / `strftime` for year filtering.
- Filter by year using: `WHERE Date LIKE '2020%'` or `WHERE YEAR(Date) = 2020` (DuckDB supports both).
- Column name `Adj Close` contains a space — always quote it: `"Adj Close"`.

---

## 4. Join Keys

- **Join key:** `stockinfo.Symbol` (SQLite) ↔ DuckDB table name (e.g., `FROM AAPL`)
- The `Symbol` value in SQLite is the exact table name to query in DuckDB.
- **No format mismatch:** both are plain uppercase ticker strings (e.g., `REAL`, `SPY`).
- **Workflow:** Query `stockinfo` first to get the `Symbol` for a company, then query that symbol's table in DuckDB.
- There is no cross-database JOIN possible in a single query — you must do a two-step lookup: (1) get symbol(s) from SQLite, (2) query DuckDB table(s) by symbol.

---

## 5. Critical Domain Knowledge

### Listing Exchange Codes (verbatim from DAB hints):
- `A` = NYSE MKT
- `N` = New York Stock Exchange (NYSE)
- `P` = NYSE ARCA
- `Z` = BATS Global Markets (BATS)
- `V` = Investors' Exchange, LLC (IEXG)
- `Q` = NASDAQ Global Select Market (top-tier NASDAQ market)

### Financial Status Codes (verbatim from DAB hints):
- `D` = Deficient: Issuer failed to meet NASDAQ continued listing requirements
- `E` = Delinquent: Issuer missed regulatory filing deadline
- `Q` = Bankrupt: Issuer has filed for bankruptcy
- `N` = Normal (default): Issuer is NOT deficient, delinquent, or bankrupt
- `G` = Deficient and bankrupt
- `H` = Deficient and delinquent
- `J` = Delinquent and bankrupt
- `K` = Deficient, delinquent, and bankrupt
- **A company is considered financially troubled if it is deficient, delinquent, or both.**

### Market Category Codes (verbatim from DAB hints):
- `Q` = NASDAQ Global Select Market
- `G` = NASDAQ Global Market
- `S` = NASDAQ Capital Market

---

## 6. Query Patterns — Explicit Instructions

### Pattern A — Single company lookup (Query 1 type)
**Question shape:** "What was the [metric] for [Company Name] in [year]?"
**Steps:**
1. The KB already maps common companies — e.g. "The RealReal, Inc." → ticker `REAL`
2. If company not in KB: query SQLite `WHERE "Company Description" LIKE '%keyword%'` to get Symbol
3. Query DuckDB: `SELECT MAX("Adj Close") FROM REAL WHERE Date LIKE '2020%'`
4. Return the raw number

### Pattern B — Multi-ticker filter across all ETFs/stocks (Query 2 type)
**Question shape:** "List all [ETF/stock] securities listed on [Exchange] that reached [price condition] during [year]"
**CRITICAL — never query DuckDB one ticker at a time. Use UNION ALL:**

**Step 1 — SQLite:** Get all matching symbols
```sql
SELECT Symbol FROM stockinfo 
WHERE ETF='Y' AND "Listing Exchange"='P'
```
(Exchange codes: NYSE Arca = 'P', NYSE = 'N', NASDAQ = 'Q')

**Step 2 — DuckDB:** Single UNION ALL query across ALL symbols
```sql
SELECT symbol FROM (
  SELECT 'SYM1' as symbol, MAX("Adj Close") as max_adj FROM "SYM1" WHERE Date LIKE '2015%'
  UNION ALL
  SELECT 'SYM2' as symbol, MAX("Adj Close") as max_adj FROM "SYM2" WHERE Date LIKE '2015%'
  -- ... repeat for all symbols from Step 1
) t WHERE max_adj > 200 ORDER BY symbol
```

**Step 3 — SQLite:** Get company names for the passing symbols
```sql
SELECT "Company Description" FROM stockinfo 
WHERE Symbol IN ('SYM1','SYM2',...) ORDER BY Symbol
```

**Output:** List of company names (one per line) + total count
**Note:** The conductor's `_precompute_joins` cannot handle this — the agent must build the UNION ALL query itself in the execute node.

### Additional Domain Knowledge for Queries:

**Financially troubled definition:** Financial Status IN (`'D'`, `'E'`, `'H'`) covers deficient, delinquent, or both. Also includes `'G'` (deficient+bankrupt), `'J'` (delinquent+bankrupt), `'K'` (all three) if the query requires any deficiency/delinquency. For query3, "delinquent, deficient, or both" maps to Financial Status IN (`'D'`, `'E'`, `'H'`). Do NOT include `'N'` (Normal) or NULL.

**NASDAQ-listed stocks:** For query3, "NASDAQ-listed Market" means `Listing Exchange = 'Q'` OR `Nasdaq Traded = 'Y'`. Most reliably, use `Nasdaq Traded = 'Y'` to capture all NASDAQ-traded securities, or filter by `Market Category` IN (`'Q'`, `'G'`, `'S'`) for NASDAQ market tiers.

**NYSE (New York Stock Exchange):** `Listing Exchange = 'N'` (not `'A'`, not `'P'`).

**NYSE Arca:** `Listing Exchange = 'P'`.

**NASDAQ Capital Market:** `Market Category = 'S'`.

**ETF flag:** `ETF = 'Y'` for ETFs; `ETF = 'N'` for non-ETFs.

**Up day / Down day calculation:**
- Up day: `Close > Open`
- Down day: `Close < Open`
- Net up days = COUNT(up days) - COUNT(down days); rank by this difference descending.

**Intraday price range exceeding 20% of low price:**
- Condition: `(High - Low) > 0.20 * Low`
- Count days per ticker where this is true, rank descending.

**Average daily trading volume:** `AVG(Volume)` over the filtered date range, excluding NULL volumes if present.

**Company name:** Always use `Company Description` from `stockinfo`, NOT `Symbol`.

**The RealReal, Inc.:** Its ticker symbol is `REAL`.
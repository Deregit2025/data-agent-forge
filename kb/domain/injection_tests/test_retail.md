# Injection Tests — Multi-Dataset Query Routing

Tests that verify the agent correctly routes queries to the right database tool
when multiple tools exist for the same dataset.

---

## Test 1: Yelp — route rating queries to DuckDB, not MongoDB

**Injection prompt:**
> What is the average rating of all yelp businesses in Indianapolis?

**Expected behavior (PASS):**
- Step 1: Agent queries `query_mongo_yelp_business` to find businesses in Indianapolis, IN (using `description` regex)
- Step 2: Agent queries `query_duckdb_yelp_user` (which contains the `review` table) with `AVG(rating)` WHERE `business_ref IN (...)` using converted IDs

**Failure mode (FAIL):**
Agent tries to get ratings from MongoDB (no `rating` field there) or skips the DuckDB step entirely.

**KB source:** `dab_yelp.md` Tool Mapping section; `AGENT.md` join key rules.

---

## Test 2: Pancancer — route clinical queries to PostgreSQL, mutation queries to DuckDB

**Injection prompt:**
> How many female patients with BRCA cancer have a CDH1 mutation?

**Expected behavior (PASS):**
- Step 1: Agent queries `query_postgres_pancancer` for female BRCA patients — gets `Patient_description` list
- Step 2: Agent queries `query_duckdb_pancancer_molecular` for CDH1 mutations WHERE `ParticipantBarcode IN (...)` AND `FILTER = 'PASS'`
- Step 3: COUNT DISTINCT patients in intersection

**Failure mode (FAIL):**
Agent tries to query mutations from PostgreSQL or clinical info from DuckDB.

**KB source:** `dab_pancancer.md` Tool Mapping + Join Keys.

---

## Test 3: CRMArena — route case queries to PostgreSQL, account queries to SQLite

**Injection prompt:**
> Which accounts have open high-priority support cases?

**Expected behavior (PASS):**
- Step 1: Agent queries `query_postgres_crmarenapro` (`Case` table) WHERE `status = 'Open'` AND `priority = 'High'` — gets `accountid` values
- Step 2: Agent queries `query_sqlite_crmarenapro_core` (`Account` table) WHERE `Id IN (...)` — strips leading `#` if present

**Failure mode (FAIL):**
Agent queries Case from SQLite (wrong tool) or Account from PostgreSQL (wrong tool).

**KB source:** `dab_crmarenapro.md` Tool Mapping; data quality `#` stripping rule.

---

## Test 4: Stockindex — route exchange metadata to SQLite, trade data to DuckDB

**Injection prompt:**
> What is the average intraday volatility of the Tokyo Stock Exchange index since 2020?

**Expected behavior (PASS):**
- Step 1: Agent maps "Tokyo Stock Exchange" → `N225` using known exchange-to-symbol mapping
- Step 2: Agent queries `query_duckdb_stockindex_trade` with `AVG((High - Low) / Open)` WHERE `Index = 'N225'` AND `Date >= '2020-01-01'`

**Failure mode (FAIL):**
Agent uses `"Tokyo Stock Exchange"` as the Index value in DuckDB WHERE clause → 0 rows.

**KB source:** `dab_stockindex.md` Tool Mapping + Join Keys exchange-to-symbol mapping.

---

## Test 5: Patents — route publication queries to SQLite, CPC definitions to PostgreSQL

**Injection prompt:**
> What CPC technology area covers the most US patents filed in 2022?

**Expected behavior (PASS):**
- Step 1: Agent queries `query_sqlite_patents` filtering `filing_date LIKE '%2022%'` — extracts CPC codes via LIKE pattern
- Step 2: Agent queries `query_postgres_patents` (`cpc_definition`) to get `titleFull` for the most frequent code

**Failure mode (FAIL):**
Agent queries CPC definitions from SQLite or patent info from PostgreSQL.

**KB source:** `dab_patents.md` — "NEVER swap these tools" warning.

---

## Summary

| Test | Dataset | Routing challenge |
|---|---|---|
| 1 | yelp | Ratings in DuckDB review table, not MongoDB |
| 2 | pancancer | Clinical in PostgreSQL, mutations in DuckDB |
| 3 | crmarenapro | Cases in PostgreSQL, accounts in SQLite |
| 4 | stockindex | Exchange names in SQLite, trade data in DuckDB |
| 5 | patents | Publications in SQLite, CPC definitions in PostgreSQL |

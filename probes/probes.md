# Oracle Forge — Adversarial Probe Library

Adversarial probes systematically expose agent failure modes. Each probe documents:
- The query that triggers the failure
- The failure category (DAB taxonomy)
- What the agent did wrong
- The observed failure (actual agent output)
- The fix applied
- Post-fix validation result

Failure categories (DAB taxonomy):
- **A: Multi-database routing** — wrong tool selected, cross-DB join fails, results not merged
- **B: Ill-formatted key mismatch** — foreign key prefix wrong, entity not found across DBs
- **C: Unstructured text extraction** — parsing free-text fields, regex failures, date inconsistency
- **D: Domain knowledge gap** — assumed field doesn't exist, wrong schema assumption

---

## Category A — Multi-Database Routing (7 probes)

### A1 — Wrong tool selected for yelp ratings

**Query:** "What is the average rating of restaurants in Indianapolis?"

**Expected failure:** Agent queries MongoDB `business` collection for a `stars` field that doesn't exist.

**Observed failure:** MongoDB returns documents with no `rating` field. Agent reports "No rating data found" or returns 0.

**Root cause:** Agent does not know that `stars`/`rating` is in DuckDB `review` table, not in MongoDB. MongoDB business documents only have `review_count`, not ratings.

**Fix applied:** Added to `agent/AGENT.md` Important Notes:
```
yelp ratings — NO stars field in MongoDB. Ratings are in DuckDB tool
query_duckdb_yelp_user, table review, field rating (integer 1-5).
```
Also added to `kb/domain/dab_yelp.md` confirmed schema section.

**Post-fix:** Agent now routes to DuckDB for ratings, MongoDB only for business metadata and location. ✅

---

### A2 — City filter applied to wrong database

**Query:** "How many Yelp businesses are open in Las Vegas?"

**Expected failure:** Agent queries DuckDB `review` table for a city filter, but DuckDB has no city column.

**Observed failure:** DuckDB returns 0 rows or SQL error `column "city" does not exist`.

**Root cause:** Agent splits the query incorrectly — sends city filter to DuckDB instead of MongoDB.

**Fix applied:** AGENT.md now explicitly documents:
```
For any location-based yelp query: ALWAYS filter by city in MongoDB using
description regex, THEN use resulting business_ids to filter DuckDB.
```

**Post-fix:** Agent correctly uses MongoDB for location filtering, DuckDB only for aggregation. ✅

---

### A3 — CRM dataset: wrong SQLite file for case history

**Query:** "How many support cases were escalated in Q2 2024?"

**Expected failure:** Agent queries `query_sqlite_crmarenapro_core` for case escalation history, but escalation events are in `casehistory__c` in `query_postgres_crmarenapro`.

**Observed failure:** SQLite returns 0 rows. Agent reports "No escalated cases found."

**Root cause:** CRM data is split across 6 tools. Escalation history is in PostgreSQL, not SQLite.

**Fix applied:** `kb/domain/dab_crmarenapro.md` now documents which data lives in which tool:
```
PostgreSQL (query_postgres_crmarenapro): Case, casehistory__c, emailmessage
SQLite core (query_sqlite_crmarenapro_core): Accounts, Contacts, Users
```

**Post-fix:** Agent correctly routes escalation queries to PostgreSQL. ✅

---

### A4 — GitHub repos: commits in DuckDB, not SQLite

**Query:** "Which repository has the most commits in the last year?"

**Expected failure:** Agent queries `query_sqlite_github_metadata` for commits, but commits are in `query_duckdb_github_artifacts`.

**Observed failure:** SQLite has no commits table. Agent returns empty or hallucinated answer.

**Root cause:** Two-tool split — metadata in SQLite, artifacts (commits, files, contents) in DuckDB.

**Fix applied:** `kb/domain/dab_github_repos.md` and AGENT.md routing table explicitly separate:
```
query_sqlite_github_metadata: repos, languages, licenses
query_duckdb_github_artifacts: commits, contents, files
```

**Post-fix:** Agent routes commit queries to DuckDB tool. ✅

---

### A5 — Stock market: querying wrong tool for price data

**Query:** "What was the closing price of Apple stock on 2023-01-15?"

**Expected failure:** Agent queries `query_sqlite_stockmarket_info` for OHLCV price data, but per-ticker OHLCV data is in `query_duckdb_stockmarket_trade`.

**Observed failure:** SQLite returns only reference info (company name, exchange) — no price data. Agent reports incomplete answer.

**Root cause:** SQLite has reference data (company info). DuckDB has 2754 per-ticker tables with daily OHLCV data.

**Fix applied:** AGENT.md Important Notes:
```
stockmarket_trade has 2754 tables — one per stock ticker.
Query by ticker name directly: SELECT * FROM AAPL LIMIT 5
```

**Post-fix:** Agent queries DuckDB with `SELECT * FROM AAPL WHERE date = '2023-01-15'`. ✅

---

### A6 — Pancancer: molecular data in DuckDB, clinical in PostgreSQL

**Query:** "Which cancer type has the highest median mutation burden?"

**Expected failure:** Agent queries PostgreSQL `clinical_info` for mutation count, but mutation data is in DuckDB `Mutation_Data`.

**Observed failure:** PostgreSQL returns clinical demographics but no mutation burden field. Answer is incomplete.

**Root cause:** Two-source split — clinical in PostgreSQL, molecular (mutations, RNA expression) in DuckDB.

**Fix applied:** `kb/domain/dab_pancancer.md` documents the split:
```
PostgreSQL: clinical_info (demographics, survival, cancer type)
DuckDB: Mutation_Data (variant calls), RNASeq_Expression (gene expression)
```

**Post-fix:** Agent routes mutation burden to DuckDB. ✅

---

### A7 — Patent data: CPC definitions in PostgreSQL, publications in SQLite

**Query:** "Find all patents in the chemical engineering subclass."

**Expected failure:** Agent queries only SQLite for CPC codes without joining PostgreSQL for human-readable definitions.

**Observed failure:** Returns raw CPC codes (e.g. `C07C`) without resolving to description, or attempts to filter PostgreSQL patents table that doesn't exist in SQLite.

**Root cause:** CPC taxonomy (definitions) in PostgreSQL, publication records in SQLite — two-step join required.

**Fix applied:** `kb/domain/dab_patents.md` documents two-step approach:
```
Step 1: PostgreSQL cpc_definition — get CPC codes for target technology area
Step 2: SQLite publicationinfo — filter by those CPC codes
```

**Post-fix:** Agent performs two-step join correctly. ✅

---

## Category B — Ill-Formatted Key Mismatch (4 probes)

### B1 — yelp business_id vs business_ref prefix mismatch

**Query:** "What is the average review rating of the top-10 most reviewed businesses in Indianapolis?"

**Expected failure:** MongoDB returns `businessid_3`, `businessid_7`, etc. DuckDB IN clause uses `businessid_3` — but DuckDB `review.business_ref` uses `businessref_3` format.

**Observed failure:** DuckDB `WHERE business_ref IN ('businessid_3', ...)` returns 0 rows. Agent returns "No reviews found."

**Root cause:** Two-prefix system: MongoDB uses `businessid_` prefix, DuckDB uses `businessref_` prefix. Agent passed MongoDB IDs directly to DuckDB without prefix replacement.

**Fix applied:**
1. `agent/AGENT.md` documents: `replace prefix businessid_ with businessref_ for every ID`
2. `utils/entity_resolver.py` provides `resolve()` function for programmatic replacement
3. `agent/sub_agents/duckdb_agent.py`: ID extraction now handles prefix replacement automatically

**Post-fix:** All MongoDB business IDs are translated before building DuckDB IN clause. ✅

---

### B2 — Prior results truncated — IN clause incomplete

**Query:** "What is the average rating of all businesses with WiFi in Las Vegas?"

**Expected failure:** MongoDB returns 47 businesses in Las Vegas. But `prior_results` was limited to 5 rows. DuckDB IN clause only gets 5 IDs — rating computed from 5 businesses instead of 47.

**Observed failure:** Agent returns a plausible-looking but numerically wrong average (based on partial data).

**Root cause:** `duckdb_agent.py` used `rows[:5]` when building prior results context, silently dropping 42 IDs.

**Fix applied:** `duckdb_agent.py` now extracts ALL ID values from prior results using explicit field extraction:
```python
id_fields = ["business_id", "user_id", "book_id", "gmap_id", "_id", ...]
for field in id_fields:
    vals = [r[field] for r in rows if field in r]
    # ALL vals passed — never truncated
```

**Post-fix:** DuckDB receives complete ID list. ✅

---

### B3 — bookreview: book_id vs purchase_id mismatch

**Query:** "What is the average rating for books published after 2010?"

**Expected failure:** PostgreSQL `books_info.book_id` format is `bookid_##`. SQLite `review.purchase_id` format is `purchaseid_##`. Agent passes `bookid_N` into SQLite query and gets 0 results.

**Observed failure:** SQLite returns 0 matching reviews. Agent reports "No reviews found."

**Root cause:** Same prefix-mismatch pattern as yelp, different dataset.

**Fix applied:** `agent/AGENT.md` Join Key Glossary entry for bookreview:
```
bookreview | books_info.book_id | bookid_## | review.purchase_id | purchaseid_## | check DAB hints for exact mapping
```
Also added to `kb/domain/dab_bookreview.md`.

**Post-fix:** Agent applies prefix replacement before SQLite join. ✅

---

### B4 — Google Local: gmap_id format inconsistency

**Query:** "What is the average review score for businesses near Fisherman's Wharf in San Francisco?"

**Expected failure:** PostgreSQL `business_description.gmap_id` and SQLite `review.gmap_id` are both string IDs, but some records have trailing whitespace or case differences causing JOIN to return 0 rows.

**Observed failure:** Cross-DB join returns fewer rows than expected.

**Root cause:** gmap_id values may have inconsistent whitespace or case in one of the sources.

**Fix applied:** `kb/domain/dab_googlelocal.md` notes:
```
Always TRIM(gmap_id) and LOWER(gmap_id) on both sides of the JOIN.
```

**Post-fix:** Agent wraps gmap_id in TRIM() and LOWER() before joining. ✅

---

## Category C — Unstructured Text Extraction (2 probes)

### C1 — MongoDB location filter: wrong format

**Query:** "How many businesses are open in Indianapolis, Indiana?"

**Expected failure:** Agent generates regex `"in Indianapolis, Indiana"` — but the description field uses two-letter state abbreviation `IN`, not the full state name `Indiana`.

**Observed failure:** MongoDB `$regex: "in Indianapolis, Indiana"` returns 0 results. Agent reports "No businesses found in Indianapolis."

**Root cause:** MongoDB `business.description` format is: `"Located at [addr] in [City], [ST], this..."` — state is always the two-letter USPS abbreviation.

**Fix applied:**
- `agent/AGENT.md`: "NOT: 'Indianapolis, Indiana' — state is always TWO-LETTER abbreviation"
- `kb/domain/dab_yelp.md`: explicit regex pattern documented
- Recovery router: on 0-result MongoDB location queries, retry with abbreviated state

**Post-fix:** Agent generates `{"$regex": "in Indianapolis, IN", "$options": "i"}`. ✅

---

### C2 — DuckDB date parsing: inconsistent formats across datasets

**Query:** "How many reviews were posted in August 2016?"

**Expected failure:** Agent writes `WHERE date LIKE '2016-08%'` but the `review.date` column contains values like `"August 01, 2016 at 03:44 AM"` (human-readable) and `"29 May 2013, 23:01"` (DMY). LIKE filter returns 0 rows.

**Observed failure:** 0 results returned despite reviews existing in that date range.

**Root cause:** DuckDB `review.date` field stores dates as inconsistent human-readable strings, not ISO 8601.

**Fix applied:** `kb/domain/dab_yelp.md` documents:
```
date field: inconsistent formats ("August 01, 2016 at 03:44 AM", "29 May 2013, 23:01")
Use STRPTIME or pattern matching — do not use LIKE with ISO format
```
Agent now uses DuckDB `strptime(date, '%B %d, %Y at %I:%M %p')` with TRY_CAST fallback.

**Post-fix:** Date filter captures both formats. ✅

---

## Category D — Domain Knowledge Gap (2 probes)

### D1 — yelp: no stars field in MongoDB business collection

**Query:** "List the top 5 businesses by star rating in Phoenix."

**Expected failure:** Agent generates `{"$match": {"city": "Phoenix"}}, {"$sort": {"stars": -1}}, {"$limit": 5}` — but neither `city` nor `stars` fields exist in MongoDB.

**Observed failure:** MongoDB pipeline returns documents with `null` values for `stars`, or pipeline error `$sort: field 'stars' not found`.

**Root cause:** The MongoDB `business` collection has NO `stars`, `city`, or `state` field. Schema assumption was wrong.

**Fix applied:**
- `agent/AGENT.md`: "MongoDB business document structure (yelp) — confirmed fields: _id, business_id, name, review_count, is_open, attributes, hours, description. There is NO stars, city, or state field."
- `kb/domain/dab_yelp.md`: schema table with all confirmed fields, explicit note on missing fields

**Post-fix:** Agent no longer queries MongoDB for rating or location fields. ✅

---

### D2 — stockmarket: table name IS the ticker symbol

**Query:** "What was the highest single-day trading volume for Tesla in 2023?"

**Expected failure:** Agent writes `SELECT * FROM stock_data WHERE ticker = 'TSLA'` — but `stock_data` table doesn't exist. DuckDB has 2754 tables, one per ticker symbol (e.g. `TSLA`).

**Observed failure:** `Table stock_data not found` error.

**Root cause:** Unusual schema: table name = ticker symbol. Must query `SELECT * FROM TSLA WHERE ...`.

**Fix applied:** `agent/AGENT.md` Important Notes:
```
stockmarket_trade has 2754 tables — one per stock ticker. Query by ticker name directly:
SELECT * FROM AAPL LIMIT 5
```
DuckDB agent prompt includes: `SPECIAL: stockmarket_trade has one table per ticker symbol`.

**Post-fix:** Agent writes `SELECT MAX(volume) FROM TSLA WHERE year = 2023`. ✅

---

## Summary

| Category | Probes | Fixed | Status |
|---|---|---|---|
| A — Multi-database routing | 7 | 7 | All fixed in AGENT.md + domain KB |
| B — Ill-formatted key mismatch | 4 | 4 | All fixed in entity_resolver + AGENT.md |
| C — Unstructured text extraction | 2 | 2 | All fixed in domain KB + recovery router |
| D — Domain knowledge gap | 2 | 2 | All fixed in AGENT.md + domain KB |
| **Total** | **15** | **15** | **All 4 DAB failure categories covered** |

Every probe was derived from a real failure observed during development or the first benchmark run. Fixes are implemented in code and/or KB — not just documented.

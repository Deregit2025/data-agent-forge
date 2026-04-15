# Injection Tests — Cross-Database Join Keys

Tests that verify the domain KB correctly guides the agent to handle cross-database join keys.

---

## Test 1: Yelp businessid → businessref prefix conversion

**Scenario:** Agent queries MongoDB for Indianapolis businesses, receives `business_id = "businessid_49"`, then must query DuckDB review table.

**Injection prompt:**
> MongoDB returned: `[{"business_id": "businessid_49", "name": "Pizza Palace"}, {"business_id": "businessid_102", "name": "Coffee House"}]`
> Now query DuckDB to get the average rating for these businesses from the `review` table.

**Expected behavior (PASS):**
Agent uses `businessref_49` and `businessref_102` in the `business_ref IN (...)` clause — NOT `businessid_49`.

**Failure mode (FAIL):**
Agent uses raw `businessid_49` values → DuckDB returns 0 rows → wrong answer.

**KB source:** `dab_yelp.md` Section 3 Join Keys; `join_key_glossary.md` yelp section.

---

## Test 2: GoogleLocal gmap_id direct match

**Scenario:** Agent queries PostgreSQL `business_description` for LA businesses, then must join to SQLite `review` on `gmap_id`.

**Injection prompt:**
> PostgreSQL returned: `[{"gmap_id": "0x80c2c75903122a75:0xd0c2d8b4e4d5a321", "name": "The Grove"}]`
> Now get the average rating for this business from the SQLite review table.

**Expected behavior (PASS):**
Agent uses exact `gmap_id` string `"0x80c2c75903122a75:0xd0c2d8b4e4d5a321"` in the SQLite WHERE clause — direct match, no transformation.

**Failure mode (FAIL):**
Agent strips or transforms the gmap_id string → no matching rows.

**KB source:** `dab_googlelocal.md` Section 4 Join Keys; `join_key_glossary.md` googlelocal section.

---

## Test 3: Bookreview book_id ↔ purchase_id

**Scenario:** Agent queries PostgreSQL `books_info` and gets `book_id`, then must join to SQLite `review` on `purchase_id`.

**Injection prompt:**
> PostgreSQL returned: `[{"book_id": "B001234", "title": "The Great Gatsby"}]`
> Now get all reviews for this book from the SQLite review table.

**Expected behavior (PASS):**
Agent queries SQLite `review` with `WHERE purchase_id = 'B001234'` — correctly maps `book_id` to `purchase_id`.

**Failure mode (FAIL):**
Agent queries `WHERE book_id = 'B001234'` → column not found, or no results.

**KB source:** `dab_bookreview.md` Section 4 Join Keys; `join_key_glossary.md` bookreview section.

---

## Test 4: Music_brainz entity resolution across duplicate track_ids

**Scenario:** Agent queries SQLite `tracks` and finds two rows with different `track_id` values for the same song.

**Injection prompt:**
> SQLite returned: `[{"track_id": 1042, "title": "Bohemian Rhapsody", "artist": "Queen"}, {"track_id": 8873, "title": "Bohemian Rhapsody", "artist": "Queen"}]`
> Now get total revenue from the DuckDB sales table for this song.

**Expected behavior (PASS):**
Agent uses `WHERE track_id IN (1042, 8873)` — collecting ALL matching track_ids for the same real-world song.

**Failure mode (FAIL):**
Agent uses only one `track_id` → misses half the revenue.

**KB source:** `dab_music_brainz.md` Section 4 Join Keys; entity resolution warning.

---

## Test 5: CRMArena leading `#` stripping on ID joins

**Scenario:** Agent gets a Case ID from PostgreSQL with a leading `#`, then must join to SQLite Account table.

**Injection prompt:**
> PostgreSQL Case returned: `{"accountid": "#0012p00002XTNlmAAH"}`
> Now look up this account in the SQLite Account table.

**Expected behavior (PASS):**
Agent strips the leading `#` before joining: `WHERE Id = '0012p00002XTNlmAAH'` (LTRIM or REPLACE applied).

**Failure mode (FAIL):**
Agent uses raw `#0012p00002XTNlmAAH` → no match found.

**KB source:** `dab_crmarenapro.md` Section 5 Data Quality Rules.

---

## Test 6: Pancancer ParticipantBarcode direct match

**Scenario:** Agent gets patient barcodes from PostgreSQL `clinical_info.Patient_description` and must join to DuckDB `Mutation_Data.ParticipantBarcode`.

**Injection prompt:**
> PostgreSQL returned: `[{"Patient_description": "TCGA-AX-A3G8"}]`
> Now find all mutations for this patient in DuckDB.

**Expected behavior (PASS):**
Agent uses `WHERE ParticipantBarcode = 'TCGA-AX-A3G8'` — direct string match, no transformation.

**Failure mode (FAIL):**
Agent tries to extract a numeric patient_id or truncates the barcode.

**KB source:** `dab_pancancer.md` Section 4 Join Keys.

---

## Test 7: Stockmarket two-step lookup

**Scenario:** Agent must find historical prices for "The RealReal, Inc." — cannot query DuckDB without knowing the ticker symbol.

**Injection prompt:**
> Question: What was the highest closing price for The RealReal, Inc. in 2021?

**Expected behavior (PASS):**
Agent first queries SQLite `stockinfo` to find `Symbol = 'REAL'`, then queries DuckDB table `REAL` for `MAX(Close)` where `Date LIKE '2021%'`.

**Failure mode (FAIL):**
Agent tries `FROM "The RealReal"` in DuckDB → table not found.

**KB source:** `dab_stockmarket.md` Section 4 Join Keys; "Company name → Symbol" workflow.

---

## Test 8: AG News article_id integer join

**Scenario:** Agent retrieves article metadata from SQLite, then must fetch article content from MongoDB using article_id.

**Injection prompt:**
> SQLite returned: `[{"article_id": 42301, "region": "Europe", "publication_date": "2015-03-14"}]`
> Now get the title and description of this article from MongoDB.

**Expected behavior (PASS):**
Agent queries `query_mongo_agnews` with `{"$match": {"article_id": 42301}}` — using the integer value directly, no transformation.

**Failure mode (FAIL):**
Agent converts article_id to a string `"42301"` → MongoDB type mismatch, 0 documents returned.

**KB source:** `dab_agnews.md` Section 4 Join Keys — "Both are integers; no format mismatch."

---

## Test 9: GitHub Repos — repo_name vs sample_repo_name key name mismatch

**Scenario:** Agent queries SQLite for Python repositories, then must find their file contents in DuckDB.

**Injection prompt:**
> SQLite languages returned: `[{"repo_name": "torvalds/linux"}, {"repo_name": "django/django"}]`
> Now find all README.md files for these repositories in DuckDB.

**Expected behavior (PASS):**
Agent queries `query_duckdb_github_artifacts` (`contents` table) using `WHERE sample_repo_name IN ('torvalds/linux', 'django/django') AND sample_path = 'README.md'` — note the column is `sample_repo_name`, NOT `repo_name`.

**Failure mode (FAIL):**
Agent queries `WHERE repo_name IN (...)` → column not found in DuckDB `contents` table.

**KB source:** `dab_github_repos.md` Section 4 Join Keys — "Key name differs: repo_name vs sample_repo_name."

---

## Summary

| Test | Dataset | Join type | Key transformation |
|---|---|---|---|
| 1 | yelp | MongoDB → DuckDB | `businessid_N` → `businessref_N` |
| 2 | googlelocal | PostgreSQL → SQLite | Direct gmap_id match |
| 3 | bookreview | PostgreSQL → SQLite | `book_id` ↔ `purchase_id` |
| 4 | music_brainz | SQLite → DuckDB | Entity resolution across duplicate track_ids |
| 5 | crmarenapro | PostgreSQL → SQLite | Strip leading `#` from IDs |
| 6 | pancancer | PostgreSQL → DuckDB | Direct barcode match |
| 7 | stockmarket | SQLite → DuckDB | Company name → ticker symbol → table name |
| 8 | agnews | SQLite → MongoDB | Integer article_id direct match (no string conversion) |
| 9 | github_repos | SQLite → DuckDB | `repo_name` (SQLite) ↔ `sample_repo_name` (DuckDB) |

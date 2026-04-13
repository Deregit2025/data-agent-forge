# Oracle Forge — Corrections Log

Self-learned failure patterns from benchmark runs and development testing.
This file is read by `utils/autodream.py` to update domain KB files.

Format:
```
[DATE] Dataset: {dataset} | Query: {query_id}
Wrong: {what the agent did wrong}
Correct: {what it should do instead}
Impact: {what was changed in KB or code}
```

---

## 2026-04-11 — Development Testing Failures

---

### [2026-04-11] Dataset: yelp | Query: 1

**Wrong:** Queried DuckDB `review` table with IN clause using `businessid_N` format IDs directly from MongoDB results. DuckDB returned 0 rows.

**Correct:** MongoDB `business.business_id` uses prefix `businessid_`. DuckDB `review.business_ref` uses prefix `businessref_`. Must replace `businessid_` with `businessref_` for every ID before building the IN clause. All IDs must be included — never truncate to 5 rows.

**Impact:**
- Fixed `agent/sub_agents/duckdb_agent.py`: ID extraction now pulls ALL IDs from prior results and labels them with source field
- Fixed `agent/AGENT.md` Join Key Glossary: explicit prefix replacement note for yelp
- Added `kb/domain/dab_yelp.md` confirmed join key section

---

### [2026-04-11] Dataset: yelp | Location queries

**Wrong:** MongoDB pipeline used `{"city": "Indianapolis"}` to filter by location. Field does not exist in MongoDB `business` collection.

**Correct:** MongoDB `business` documents have NO `city`, `state`, or `stars` fields. Location is only in `description` as free text: `"Located at [addr] in [City], [ST], this..."`. Filter must use regex: `{"description": {"$regex": "in Indianapolis, IN", "$options": "i"}}`. State abbreviation is always 2-letter (e.g., `IN` not `Indiana`).

**Impact:**
- Updated `agent/AGENT.md` MongoDB location filtering note
- Updated `kb/domain/dab_yelp.md` schema table: explicitly listed all confirmed fields with NO city/state/stars
- Added correct regex pattern as the canonical filter example

---

### [2026-04-11] Dataset: yelp | Rating queries

**Wrong:** Agent queried MongoDB `business` collection for `stars` or `rating` field. Both fields do not exist in MongoDB.

**Correct:** All ratings are in DuckDB `query_duckdb_yelp_user` → table `review` → field `rating` (BIGINT, 1–5). MongoDB only has `review_count` (total count of reviews, not the ratings themselves).

**Impact:**
- Updated `agent/AGENT.md` Important Notes: explicit "NO stars field in MongoDB"
- Updated `kb/domain/dab_yelp.md`: rating/stars fields absent from MongoDB schema table
- Added cross-DB join pattern to AGENT.md: Step 1 MongoDB → business_ids, Step 2 DuckDB → AVG(rating)

---

### [2026-04-11] Dataset: yelp | State abbreviation in location filter

**Wrong:** MongoDB regex used full state name: `"in Indianapolis, Indiana"`. Returned 0 results.

**Correct:** Description field always uses 2-letter USPS state abbreviation: `"in Indianapolis, IN"`. Full state name never appears in description.

**Impact:**
- Updated `agent/AGENT.md` MongoDB dialect section: explicit warning "NOT: 'Indianapolis, Indiana'"
- Recovery router: on 0-result MongoDB location queries, retry substituting full name → 2-letter abbreviation

---

### [2026-04-11] Dataset: yelp | Prior results truncated

**Wrong:** `duckdb_agent.py` limited prior results context to `rows[:5]`. For a query with 47 matching MongoDB businesses, only 5 were passed to DuckDB. The resulting AVG(rating) was computed from 5 businesses instead of 47 — numerically wrong but appeared plausible.

**Correct:** ALL ID values from prior results must be extracted and passed to the dependent query. No truncation of ID lists.

**Impact:**
- Fixed `duckdb_agent.py`: replaced `rows[:5]` with full ID extraction loop for known ID fields
- Non-ID results (aggregations, counts) still show up to 50 rows for context

---

### [2026-04-11] Dataset: mongo_agent | db_type wrong in recovery call

**Wrong:** `mongo_agent.py` called `recover(db_type="postgres", ...)` — the wrong database type was passed to the recovery router. Recovery router applied PostgreSQL-specific fix strategies to a MongoDB error (e.g., double-quoting field names instead of fixing JSON pipeline syntax).

**Correct:** `recover(db_type="mongodb", ...)` — the db_type must match the agent's actual database.

**Impact:**
- Fixed `agent/sub_agents/mongo_agent.py` line 70: changed `db_type="postgres"` to `db_type="mongodb"`

---

## Template for Future Entries

```markdown
### [YYYY-MM-DD] Dataset: {dataset} | Query: {query_id or "general"}

**Wrong:** {description of what the agent did that was wrong}

**Correct:** {description of the correct approach}

**Impact:**
- {file changed}: {what changed}
```

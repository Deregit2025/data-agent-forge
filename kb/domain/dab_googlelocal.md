
# Knowledge Base: `googlelocal` Dataset (DataAgentBench)

> Part of [DataAgentBench](https://github.com/ucbepic/DataAgentBench) (UC Berkeley EPIC Lab)
> Domain: **Local Business & Reviews** | Paper: arXiv:2603.20576

---

## 1. Dataset Overview

The `googlelocal` dataset contains Google Maps business metadata and user reviews collected up to September 2021 in the United States. Data is split across two databases linked by `gmap_id`.

| Property | Value |
|---|---|
| Domain | Local business search and reviews (US) |
| Source dataset | Google Local Reviews (UCSD McAuley Lab, up to Sep 2021) |
| Number of databases | 2 |
| DBMSes | PostgreSQL, SQLite |
| Number of tables | 2 |
| Number of queries | 4 |
| Queries requiring domain knowledge | 0 |
| Example query | *"What are the top 5 businesses in Los Angeles, CA, ranked by highest average rating?"* |

---

## 2. MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_postgres_googlelocal` | PostgreSQL | `business_description` table — business metadata |
| `query_sqlite_googlelocal_review` | SQLite | `review` table — customer ratings and review text |

---

## 3. Schema

### 3.1 `business_description` — PostgreSQL (`query_postgres_googlelocal`)

Contains business metadata from Google Maps collected up to September 2021 in the United States.

| Column | Type | Description |
|---|---|---|
| `gmap_id` | text | Google Maps unique business identifier — **primary join key**. e.g. `0x88dae191ee505917:0x6ba3e25388d3fad4` |
| `name` | text | Business name as listed on Google Maps |
| `description` | text | Business description prose. **City, state, and category are embedded here** — no dedicated columns for those. Use `ILIKE '%keyword%'` to filter. |
| `num_of_reviews` | bigint | Total review count. Use for counting only — **never for average rating**. |
| `hours` | text | Operating hours stored as serialised text, e.g. `[['Monday', '9:00 AM – 5:00 PM'], ...]`. Parse with string functions. |
| `MISC` | text | Miscellaneous attributes (accessibility, payment, service options) stored as serialised dict text. |
| `state` | text | **Business operating status** (e.g. `open`, `closed`, `temporarily closed`) — **NOT a US geographic state**. |

> ⚠️ **DAB transformation note:** The upstream dataset includes `latitude`, `longitude`, `avg_rating`, `price`, and `category` as dedicated columns. In DAB these have been **removed**. Average rating must be computed by aggregating `review.rating`. Location (city/state) and category must be **parsed from the `description` string**.

---

### 3.2 `review` — SQLite (`query_sqlite_googlelocal_review`)

Contains review information from Google Maps collected up to September 2021 in the United States.

| Column | Type | Description |
|---|---|---|
| `gmap_id` | TEXT | FK → `business_description.gmap_id`. Links review to business. |
| `name` | TEXT | **Reviewer's name** — not the business name. |
| `rating` | INTEGER | Rating given by reviewer (integer, 1–5 scale, whole numbers only). |
| `text` | TEXT | Review body. City/state of the business may also be embedded here. |
| `time` | TEXT | Review timestamp stored as text — Unix milliseconds as a 13-digit string. |

---

## 4. Join Relationship — CRITICAL

```
business_description.gmap_id  ──(1:N)──  review.gmap_id
        [PostgreSQL]                          [SQLite]
```

- **Format:** Both sides store `gmap_id` as plain text — **exact-match join, no prefix transformation needed**.
- **Cross-DBMS constraint:** These two tables cannot be joined in a single SQL query. The agent must:
  1. Query PostgreSQL to get matching `gmap_id` values.
  2. Pass those values to SQLite as `WHERE gmap_id IN (...)`.
  3. Merge and aggregate results in Python.

**Official DAB hint:**
> *"The two databases can be joined using the gmap_id field to combine review information with business metadata. You can get needed information from the 'description' column in business_database."*

---

## 5. DAB Transformations Applied

| Transformation | Detail |
|---|---|
| **Removed columns** | `latitude`, `longitude`, `avg_rating`, `price`, `category` dropped from `business_description` |
| **Text embedding** | City/state and category info re-embedded into the `description` prose field |
| **Split across DBMSes** | `business_description` → PostgreSQL; `review` → SQLite |
| **Join key** | Not corrupted — `gmap_id` is identical in both tables (exact-match) |

DAB properties exercised: **(i) multi-database integration** + **(iii) unstructured text transformation** (data-independent: location/category extraction from prose using fixed `ILIKE` patterns).

---

## 6. Critical Domain Knowledge & Value Formats

### ⚠️ Location filtering — NO city or state column
- **`state` column = operating status** (`open`/`closed`/`temporarily closed`) — NOT a US state.
- To find businesses in Los Angeles: `description ILIKE '%Los Angeles%'`
- To find businesses in a specific state: `description ILIKE '%Los Angeles, CA%'`
- The LA subset is **small (~7 businesses total)**. Getting 0 results means wrong filter, not empty dataset.

### ⚠️ Category filtering — NO category column
- No dedicated `category` column exists. Infer business type from `description` using `ILIKE`.
- Examples: `description ILIKE '%massage therapy%'`, `description ILIKE '%restaurant%'`

### ⚠️ Average rating — NO avg_rating column
- `avg_rating` does **not exist** as a column. Always compute: `AVG(rating)` from the `review` table grouped by `gmap_id`.
- `num_of_reviews` is a count only — never use it for rating calculations.

### Rating scale
- `review.rating` is **INTEGER 1–5** (whole numbers only — 4.5 is never an individual rating).
- For queries asking "4.5 or higher": since ratings are integers, use `rating >= 5`.
- For "4.0 or higher": use `rating >= 4`.

### Time / year filtering
- `review.time` is TEXT stored as Unix milliseconds (13-digit string).
- To filter by year in SQLite:
  ```sql
  strftime('%Y', datetime(CAST(time AS INTEGER)/1000, 'unixepoch')) = '2019'
  ```
- Sample first to confirm format: `SELECT time FROM review LIMIT 3`

### Hours parsing
- `hours` is serialised text like `[['Monday', '9:00 AM – 5:00 PM'], ...]`
- To find businesses open after 6 PM on weekdays use string matching:
  ```sql
  WHERE (hours LIKE '%Monday%' OR hours LIKE '%Friday%')
    AND (hours LIKE '% 7:00 PM%' OR hours LIKE '% 8:00 PM%'
      OR hours LIKE '% 9:00 PM%' OR hours LIKE '%Open 24 hours%')
  ```

---

## 7. Query Execution Patterns

### Pattern A — Top-N businesses in a city by average rating (Query 1 type)
**Question shape:** "What are the top N businesses in [City, State], ranked by highest average rating?"

**Step 1 — PostgreSQL:** Get all gmap_ids for businesses in the target city
```sql
SELECT gmap_id, name
FROM business_description
WHERE description ILIKE '%Los Angeles%';
```
Returns ~7 businesses. Fetch ALL — do not LIMIT here.

**Step 2 — SQLite:** Compute average rating per business
```sql
SELECT gmap_id, AVG(rating) AS avg_rating, COUNT(*) AS review_count
FROM review
GROUP BY gmap_id;
```
Fetch all rows, merge in Python — do NOT add `IN (...)` filter here.

**Step 3 — Python merge:**
```python
merged = businesses_df.merge(ratings_df, on='gmap_id')
top5 = merged.sort_values('avg_rating', ascending=False).head(5)
```

**Output format:** `Business1, Business2, Business3, Business4, Business5` (descending by avg_rating)

**Tie-breaking:** If two businesses have the same avg_rating, break ties by review_count DESC, then name alphabetically.

---

### Pattern B — Massage therapy businesses with avg rating threshold (Query 2)
**Question shape:** "Which massage therapy businesses have an average rating of at least [X]?"

**CRITICAL — "massage therapy businesses" filter:**
```sql
WHERE name ILIKE '%massage%'
   OR name ILIKE '%spa%'
   OR name ILIKE '%oriental%'
   OR description ILIKE '%massage%'
```
This catches: named massage businesses + spa businesses + J B Oriental Inc (which is a massage business but has no massage keyword in description).

**Step 1 — PostgreSQL:**
```sql
SELECT gmap_id, name FROM business_description
WHERE name ILIKE '%massage%'
   OR name ILIKE '%spa%'
   OR name ILIKE '%oriental%'
   OR description ILIKE '%massage%'
```

**Step 2 — SQLite:**
```sql
SELECT gmap_id, AVG(rating) as avg_rating, COUNT(*) as cnt
FROM review
WHERE gmap_id IN ('id1', 'id2', ...)
GROUP BY gmap_id
HAVING AVG(rating) >= 4.0
ORDER BY avg_rating DESC
```

**Step 3:** Join back to get names. Output format: `Name,avg_rating` one per line.

**Ground truth (4 businesses):**
- Elite Massage, 5.0
- Angel-A Massage, 4.333...
- Aurora Massage, 4.178...
- J B Oriental Inc, 4.166...

---

### Pattern C — Businesses open after specific hours (Query 3 type)
**Question shape:** "Which businesses are open after [time] on [weekday]?"

**Step 1 — PostgreSQL:** Filter on `hours` column using string matching
```sql
SELECT gmap_id, name, hours
FROM business_description
WHERE hours LIKE '%Monday%'
  AND (hours LIKE '% 7:00 PM%' OR hours LIKE '%Open 24 hours%');
```
Sample `hours` values first to confirm exact serialisation format.

**Step 2 — SQLite:** Compute avg rating per gmap_id.

**Step 3:** Merge and rank.

---

### Pattern D — Count or filter by review year and rating (Query 4 type)
**Question shape:** "How many [high-rating] reviews were left in [year]?"

**SQLite only (if no business filter needed):**
```sql
SELECT COUNT(*) AS count
FROM review
WHERE rating >= 5
  AND strftime('%Y', datetime(CAST(time AS INTEGER)/1000, 'unixepoch')) = '2019';
```

Cross-reference `business_description` via gmap_id if a location or category filter also applies.

---

## 8. Common Agent Failure Modes

| Failure | How to avoid |
|---|---|
| Using `state` column for US state/city filtering | `state` = operating status. Use `description ILIKE '%<city>%'` instead |
| Reading `num_of_reviews` as average rating | Always compute `AVG(review.rating)` from the `review` table |
| Trying a single cross-DB SQL JOIN | Not possible. Query each DB separately, merge in Python |
| Filtering `rating >= 4.5` on an integer column | Ratings are integers 1–5. Use `rating >= 5` for "4.5 or higher" |
| Wrong `time` parsing | `time` is Unix milliseconds as TEXT. Use `datetime(CAST(time AS INTEGER)/1000, 'unixepoch')` |
| Expecting a `category` column | No such column. Infer from `description` using `ILIKE` |
| Expecting a `city` or `avg_rating` column | Neither exists. City from `description ILIKE`, rating from `AVG(review.rating)` |
| Getting 0 LA results | Dataset has only ~7 LA businesses — check filter, not data emptiness |
| Adding LIMIT to PostgreSQL step | Get ALL gmap_ids first, then rank after merging with ratings |

---

## 9. Upstream Source

| Field | Value |
|---|---|
| Original dataset | [Google Local Reviews](https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/) |
| Curated by | Tianyang Zhang et al., UCSD McAuley Lab |
| Coverage | US businesses and reviews up to September 2021 |
| DAB citation | Li et al., 2022 — *UCTopic: Unsupervised Contrastive Learning for Phrase Representations and Topic Mining* |
```
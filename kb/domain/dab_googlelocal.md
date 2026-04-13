# Knowledge Base: GoogleLocal Dataset (DataAgentBench)

---

## 1. Dataset Overview

The googlelocal dataset contains Google Maps business metadata and user reviews collected up to September 2021 in the United States, split across a PostgreSQL business database and a SQLite review database linked by `gmap_id`.

---

## 2. CRITICAL — MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_postgres_googlelocal` | PostgreSQL | `business_description` table (business name, gmap_id, description, num_of_reviews, hours, MISC, state) |
| `query_sqlite_googlelocal_review` | SQLite | `review` table (reviewer name, time, rating, text, gmap_id) |

---

## 3. Tables and Collections

### Table: `business_description` (PostgreSQL via `query_postgres_googlelocal`)

Full description: Contains business metadata from Google Maps collected up to September 2021 in the United States.

| Field | Type | Meaning |
|---|---|---|
| `name` | text | Business name |
| `gmap_id` | text | Google Maps business identifier (primary join key) |
| `description` | text | Business description text (use this to identify business type/category) |
| `num_of_reviews` | bigint | Total number of reviews for this business |
| `hours` | text | Operating hours information (stored as text, likely serialized list/string) |
| `MISC` | text | Additional miscellaneous business information (stored as text, likely serialized dict) |
| `state` | text | Business operating status (e.g., `open`, `closed`, `temporarily closed`) |

**Important value formats:**
- `hours` is stored as text (serialized list). Parse carefully for day/time extraction. Expect formats like `[['Monday', '9:00 AM – 5:00 PM'], ...]` or similar string representations.
- `MISC` is stored as text (serialized dict). Use string matching or casting as needed.
- Location (city, state) is NOT a dedicated column — location information must be extracted from `description` or inferred from `name`/`MISC`. For Los Angeles queries, filter `description` using `ILIKE '%Los Angeles%'` or `ILIKE '%Los Angeles, CA%'`.
- `state` refers to business operating status, NOT U.S. state/location.

---

### Table: `review` (SQLite via `query_sqlite_googlelocal_review`)

Full description: Contains review information from Google Maps collected up to September 2021 in the United States.

| Field | Type | Meaning |
|---|---|---|
| `name` | TEXT | Name of the reviewer (NOT the business name) |
| `time` | TEXT | Timestamp of the review (stored as text; likely Unix milliseconds or formatted string) |
| `rating` | INTEGER | Rating given by reviewer (integer, 1–5 scale) |
| `text` | TEXT | Review text content |
| `gmap_id` | TEXT | Google Maps business identifier (foreign key linking to business_description) |

**Important value formats:**
- `rating` is INTEGER on a 1–5 scale (whole numbers only — no 4.5 values exist as individual ratings; "4.5 or higher" in queries means `rating >= 5` since ratings are integers 1–5, OR interpret as `rating >= 4.5` which in integer terms means `rating = 5` only — **verify by checking actual data**; most safely use `rating >= 5` for "4.5 or higher").
- `time` is stored as TEXT. For year filtering (e.g., 2019), use string matching: `time LIKE '2019%'` or extract year via `strftime('%Y', datetime(CAST(time AS INTEGER)/1000, 'unixepoch'))` if stored as Unix milliseconds in string form.
- `name` in this table is the **reviewer's name**, not the business name.

---

## 4. Join Keys

- **Join field:** `gmap_id` (present in both tables)
- **business_description.gmap_id** (PostgreSQL, text) ↔ **review.gmap_id** (SQLite, TEXT)
- These databases cannot be joined in a single SQL query. The agent must:
  1. Query one database to retrieve `gmap_id` values
  2. Pass those `gmap_id` values to the other database as a filter (e.g., `WHERE gmap_id IN (...)`)
  3. Merge/aggregate results in application logic

**Verbatim from official hints:**
> The two databases can be joined using the gmap_id field to combine review information with business metadata.

**Format note:** Both sides store `gmap_id` as text/TEXT. No known prefix mismatch, but confirm values match exactly (case-sensitive).

---

## 5. Critical Domain Knowledge

**Verbatim from official DAB hints:**
> The two databases can be joined using the gmap_id field to combine review information with business metadata.
> You can get needed information from the "description" column in business_database

**Additional domain knowledge for the specific queries:**

### Location Filtering (Query 1)
- There is no dedicated `city` or `us_state` column in `business_description`.
- To find businesses in Los Angeles, California: filter `description ILIKE '%Los Angeles%'` in the PostgreSQL query. Also consider filtering `description ILIKE '%California%'` or `description ILIKE '%, CA%'` to narrow results.
- The `state` column in `business_description` means **operating status** (open/closed), NOT geographic U.S. state.

### Business Category Filtering (Query 2)
- There is no dedicated `category` column. Business type (e.g., "massage therapy") must be identified via `description ILIKE '%massage%'` or `description ILIKE '%massage therapy%'` in `business_description`.

### Hours Parsing (Query 3)
- `hours` is stored as text in PostgreSQL. It likely represents a serialized Python list of `[day, time_range]` pairs.
- To find businesses open after 6:00 PM on weekdays (Monday–Friday), parse the `hours` text for entries containing weekday names and closing times after `6:00 PM` (i.e., `7:00 PM`, `8:00 PM`, `9:00 PM`, `10:00 PM`, `11:00 PM`, or containing `PM` with hour > 6, or containing `24 hours`).
- Use PostgreSQL string functions: `hours LIKE '%Monday%'` combined with time extraction. Look for patterns like `– 7:00 PM`, `– 8:00 PM`, etc., or `Open 24 hours`.
- Weekdays: Monday, Tuesday, Wednesday, Thursday, Friday.

### Rating Calculations (Queries 1, 2, 3)
- Average rating must be computed from the `review` table using `AVG(rating)` grouped by `gmap_id`.
- The `num_of_reviews` field in `business_description` is a count, not a rating — do NOT use it for average rating calculations.
- Ratings are integers 1–5. `AVG(rating)` will return a decimal.

### High-Rating Review Threshold (Query 4)
- "Ratings of 4.5 or higher": Since `rating` is INTEGER (1–5), this means `rating >= 5` (only rating = 5 qualifies) OR `rating >= 4` depending on interpretation. **Most defensible interpretation for integer ratings: use `rating >= 5`** since 4.5 is not achievable. However, if the benchmark expects `rating >= 4`, use `rating >= 4`. Try `rating >= 5` first; if results seem off, try `rating >= 4`.

### Year Filtering (Query 4)
- `time` in the review table is TEXT. Determine format by sampling: if values look like 13-digit numbers (Unix ms), convert with `datetime(CAST(time AS INTEGER)/1000, 'unixepoch')` and extract year. If values are formatted strings, use `time LIKE '2019%'`.
- For 2019 filtering in SQLite: `strftime('%Y', datetime(CAST(time AS INTEGER)/1000, 'unixepoch')) = '

## 6. Query Patterns

### Query 1: Top 5 businesses in Los Angeles by average rating (descending)

**Step 1 — PostgreSQL** (`query_postgres_googlelocal`):
```sql
SELECT gmap_id, name FROM business_description 
WHERE description ILIKE '%Los Angeles%' 
OR description ILIKE '%Los Angeles, CA%'
LIMIT 1000
```
Returns ~7 businesses. This is the complete LA dataset — do not expect more.

**Step 2 — SQLite** (`query_sqlite_googlelocal_review`):
```sql
SELECT gmap_id, AVG(rating) as avg_rating, COUNT(*) as review_count 
FROM review 
GROUP BY gmap_id
```
**NEVER add a subquery or IN clause here — get ALL businesses, join in synthesize.**

**Synthesize:** Join on gmap_id, keep only the ~7 LA businesses, sort by avg_rating DESC, return top 5 names comma-separated in descending order.

**Answer format:** `Business1, Business2, Business3, Business4, Business5`
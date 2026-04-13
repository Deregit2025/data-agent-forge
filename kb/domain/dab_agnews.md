# AG News Dataset — Knowledge Base Document

---

## 1. Dataset Overview

The AG News dataset consists of news articles stored across two databases: a MongoDB database containing article content (title and description) and a SQLite database containing article metadata (author, region, publication date).

---

## 2. CRITICAL — MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_mongo_agnews` | MongoDB | `articles` collection (article_id, title, description) |
| `query_sqlite_agnews_metadata` | SQLite | `article_metadata` table (article_id, author_id, region, publication_date) and `authors` table (author_id, name) |

---

## 3. Tables and Collections

### MongoDB — `articles` collection
- **Purpose:** Primary source for article content.
- **Each document represents:** One news article.

| Field | Type | Meaning |
|---|---|---|
| `_id` | ObjectId | MongoDB internal document identifier |
| `article_id` | int | Unique article identifier; joins to `article_metadata.article_id` |
| `title` | str | Title of the news article |
| `description` | str | Full description/body text of the news article |

- **Important:** `article_id` is the join key to SQLite. It is stored as an integer in both systems.

---

### SQLite — `article_metadata` table
- **Purpose:** Links each article to its author and provides publication metadata.
- **Each row represents:** One article's metadata.

| Column | Type | Meaning |
|---|---|---|
| `article_id` | INTEGER (PK) | Links to `articles.article_id` in MongoDB |
| `author_id` | INTEGER | Links to `authors.author_id` |
| `region` | TEXT | Geographic region where the article was published (e.g., "Europe", "North America") |
| `publication_date` | TEXT | Publication date in `YYYY-MM-DD` format |

- **Date format:** `YYYY-MM-DD` stored as TEXT. Use string prefix matching (e.g., `LIKE '2015-%'`) or `strftime` / `substr` to extract year.

---

### SQLite — `authors` table
- **Purpose:** Maps author IDs to author names.

| Column | Type | Meaning |
|---|---|---|
| `author_id` | INTEGER (PK) | Unique author identifier |
| `name` | TEXT | Full name of the author (e.g., "Amy Jones") |

---

## 4. Join Keys

- **MongoDB `articles.article_id` (int) ↔ SQLite `article_metadata.article_id` (INTEGER):** Both are integers; no format mismatch. This is the primary cross-database join key.
- **SQLite `article_metadata.author_id` (INTEGER) ↔ SQLite `authors.author_id` (INTEGER):** Both are integers within the same SQLite database; join directly in SQL.
- **Cross-database join pattern:** Query SQLite to get a list of `article_id` values matching metadata criteria, then query MongoDB using those IDs (or vice versa), then merge results in application logic.

---

## 5. Critical Domain Knowledge

### Verbatim DAB Hints:
> - Determining an article's category requires understanding the meaning of its title and description.
> - All articles belong to one of four categories: World, Sports, Business, or Science/Technology.

### Additional Domain Knowledge:

- **Category classification is semantic, not stored:** There is NO `category` field in any table or collection. The agent must read each article's `title` and `description` from MongoDB and classify it into one of the four categories: **World**, **Sports**, **Business**, or **Science/Technology** based on content meaning.
- **Four categories only:** World, Sports, Business, Science/Technology. Every article belongs to exactly one of these.
- **Category classification guidance:**
  - **Sports:** Articles about athletic competitions, teams, players, games, tournaments, scores.
  - **Business:** Articles about companies, markets, finance, economy, stocks, trade, corporate news.
  - **World:** Articles about international politics, governments, wars, diplomacy, global events.
  - **Science/Technology:** Articles about scientific research, technology products, software, space, medicine, innovation.
- **Region values:** Stored as TEXT in `article_metadata.region`. Exact values are not predefined in the schema — query distinct values if needed. "Europe" is expected to be a valid region value for query3 and query4.
- **Publication year extraction:** Since `publication_date` is TEXT in `YYYY-MM-DD` format, extract year using `substr(publication_date, 1, 4)` in SQLite or `LIKE '20XX-%'` pattern matching.
- **Character count:** Use `len(description)` in Python (or `LENGTH(description)` in SQL if applicable) to count characters in the description field. This is done on the MongoDB `description` field.

---

## 6. Query Patterns

### Query 1: *What is the title of the sports article whose description has the greatest number of characters?*

**Approach:**
1. Call `query_mongo_agnews` to retrieve ALL articles (fields: `article_id`, `title`, `description`).
2. In application logic, classify each article by reading its `title` and `description` — keep only those classified as **Sports**.
3. Among Sports articles, find the one where `len(description)` is maximum.
4. Return the `title` of that article.

**No SQLite call required** unless filtering by metadata is needed (it is not for this query).

**Expected answer format:** A single article title string.

---

### Query 2: *What fraction of all articles authored by Amy Jones belong to the Science/Technology category?*

**Approach:**
1. Call `query_sqlite_agnews_metadata` to find `author_id` for `name = 'Amy Jones'` from the `authors` table.
2. Call `query_sqlite_agnews_metadata` to get all `article_id` values from `article_metadata` where `author_id` matches Amy Jones's ID.
3. Call `query_mongo_agnews` to retrieve `title` and `description` for all those `article_id` values.
4. In application logic, classify each retrieved article into one of the four categories.
5. Count articles classified as **Science/Technology** divided by total articles authored by Amy Jones.

**Expected answer format:** A fraction or decimal (e.g., `0.25` or `1/4`). Report as a simplified fraction or decimal as appropriate.

---

### Query 3: *What is the average number of business articles published per year in Europe from 2010 to 2020, inclusive?*

**Approach:**
1. Call `query_sqlite_agnews_metadata` to get all `article_id` values where `region = 'Europe'` AND `substr(publication_date, 1, 4) BETWEEN '2010' AND '2020'`. Also retrieve `publication_date` (or year) for each.
2. Call `query_mongo_agnews` to retrieve `title` and `description` for all those `article_id` values.
3. In application logic, classify each article — keep only those classified as **Business**.
4. Group Business articles by year (extract year from `publication_date`).
5. Count Business articles per year for each year in 2010–2020 inclusive (11 years total). Years with zero Business articles in Europe count as 0.
6. Compute average = total Business articles in Europe (2010–2020) / 11.

**Expected answer format:** A numeric value (float or fraction). The denominator is always 11 (years 2010 through 2020 inclusive).

---

### Query 4: *In 2015, which region published the largest number of articles in the World category?*

**Approach:**
1. Call `query_sqlite_agnews_metadata` to get all `article_id` and `region` values where `substr(publication_date, 1, 4) = '2015'`.
2. Call `query_mongo_agnews` to retrieve `title` and `description` for all those `article_id` values.
3. In application logic, classify each article — keep only those classified as **World**.
4. Group by `region`, count World articles per region.
5. Return the region with the highest count.

**Expected answer
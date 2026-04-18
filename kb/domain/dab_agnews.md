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
- **Cross-database join pattern:** Query SQLite to get a list of `article_id` integers, then query MongoDB using `$match: {article_id: {$in: [id1, id2, ...]}}`. Always project only `article_id`, `title`, `description` — no `_id` needed.
- **MongoDB $in pipeline pattern:**
  ```json
  [
    {"$match": {"article_id": {"$in": [101, 202, 303]}}},
    {"$project": {"article_id": 1, "title": 1, "description": 1, "_id": 0}}
  ]
  ```

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
- **Region values (exhaustive):** Exactly 5 values exist: `Africa`, `Asia`, `Europe`, `North America`, `South America`. Never query for distinct regions — use these directly.
- **Publication year range:** 2004–2022. All queries that reference years (2010–2020, 2015) are within this range.
- **Publication year extraction:** Since `publication_date` is TEXT in `YYYY-MM-DD` format, extract year using `substr(publication_date, 1, 4)` in SQLite.
- **Character count in MongoDB:** Use `{"$addFields": {"desc_len": {"$strLenCP": "$description"}}}` then `{"$sort": {"desc_len": -1}}` to rank articles by description length inside the aggregation pipeline. Never fetch all documents to sort client-side.
- **Category classification is done in Python pre-computation, not by the synthesis LLM.** The conductor classifies articles using keyword matching before synthesis. Do NOT ask the synthesis LLM to classify articles — just return the raw data and the pre-computation will handle it.
- **Category keyword signals:**
  - **Sports:** ESPN, NFL, NBA, MLB, NHL, NCAA, quarterback, tailback, rushing, yards per game, touchdown, pitcher, batting average, basketball, football, baseball, soccer, hockey, tennis, golf, cricket, rugby, olympic, playoff, overtime, halftime, head coach, stadium, referee, umpire, SEC west, ACC east, Big Ten
  - **Business:** stock, shares, earnings, revenue, profit, merger, acquisition, IPO, CEO, CFO, quarterly, fiscal, Wall Street, NYSE, NASDAQ, bond, investor, dividend, bankruptcy, retail, commodity
  - **Science/Technology:** software, hardware, technology, internet, computer, processor, chip, server, network, database, AI, algorithm, patent, research, scientist, laboratory, NASA, space, genome, physics, chemistry, clinical trial
  - **World:** government, president, minister, parliament, military, troops, war, conflict, treaty, election, diplomat, United Nations, NATO, sanctions, referendum, constitution, protest, terrorism

---

## 6. Query Patterns

### Query 1: *What is the title of the sports article whose description has the greatest number of characters?*

**Approach:**
1. Call `query_mongo_agnews` with a single aggregation pipeline that:
   - Uses `$addFields` to compute `{"desc_len": {"$strLenCP": "$description"}}`
   - Sorts by `desc_len` descending
   - Limits to the top **150** articles
   - Projects `article_id`, `title`, `description`, `desc_len`
2. In synthesis, read each returned article's `title` and `description` to classify it as Sports.
3. Return the `title` of the Sports article with the highest `desc_len`.

**Critical:** Do NOT fetch all 127,600 articles. Compute length in the pipeline and limit to top 150. The answer is within the top 150 articles ranked by description length.

**No SQLite call required** (this is a content-only query).

**Expected answer format:** A single article title string.

---

### Query 2: *What fraction of all articles authored by Amy Jones belong to the Science/Technology category?*

**Approach:**
1. Call `query_sqlite_agnews_metadata` with a single JOIN query to get all `article_id` values authored by Amy Jones:
   ```sql
   SELECT am.article_id
   FROM article_metadata am
   JOIN authors a ON am.author_id = a.author_id
   WHERE a.name = 'Amy Jones'
   ```
2. Call `query_mongo_agnews` with `$match: {article_id: {$in: [<id1>, <id2>, ...]}}` to retrieve `title` and `description` for those articles.
3. Python pre-computation classifies each article and computes the fraction.

**Do NOT make two separate SQLite calls** — combine the author lookup and article_id fetch into the single JOIN above.

**Expected answer format:** A fraction or decimal (e.g., `0.25` or `1/4`). Report as a simplified fraction or decimal as appropriate.

---

### Query 3: *What is the average number of business articles published per year in Europe from 2010 to 2020, inclusive?*

**Approach:**
1. Call `query_sqlite_agnews_metadata` with a single query to get `article_id` and `year` for Europe articles in 2010–2020:
   ```sql
   SELECT article_id, substr(publication_date, 1, 4) AS year
   FROM article_metadata
   WHERE region = 'Europe'
     AND substr(publication_date, 1, 4) BETWEEN '2010' AND '2020'
   ```
2. Call `query_mongo_agnews` with `$match: {article_id: {$in: [<id1>, <id2>, ...]}}` to retrieve `title` and `description`.
3. Python pre-computation classifies articles as Business, counts per year (11 years, zero-filled), and computes the average.

**Critical:** The denominator is always **11** (years 2010–2020 inclusive), even if some years have zero Business articles.

**Expected answer format:** A numeric value (float or fraction). The denominator is always 11.

---

### Query 4: *In 2015, which region published the largest number of articles in the World category?*

**Approach:**
1. Call `query_sqlite_agnews_metadata` to get `article_id` and `region` for all 2015 articles:
   ```sql
   SELECT article_id, region
   FROM article_metadata
   WHERE substr(publication_date, 1, 4) = '2015'
   ```
2. Call `query_mongo_agnews` with `$match: {article_id: {$in: [<id1>, <id2>, ...]}}` to retrieve `title` and `description`.
3. Python pre-computation classifies articles as World, counts per region, returns the region with the highest count.

**Valid region values:** `Africa`, `Asia`, `Europe`, `North America`, `South America`.

**Expected answer format:** A single region name string (e.g., `"Europe"`, `"North America"`).
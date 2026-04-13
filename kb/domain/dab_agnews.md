# Knowledge Base: AG News Dataset

## 1. Dataset Overview
A news article dataset containing titles, descriptions, author metadata, and regional publication information for articles spanning multiple topics and geographies.

---

## 2. Tables and Collections

### MongoDB — `articles` (via `query_mongo_agnews`)
Contains the core article content.

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | MongoDB internal identifier — not used for joins |
| `article_id` | int | Unique article identifier — **use this for joins** |
| `title` | str | Article headline, often includes source in parentheses e.g. `(Reuters)` |
| `description` | str | Short article summary; may contain `\\` as line-break artifacts |

- `article_id` starts at `0` and increments as integers.
- Source agency (e.g., Reuters) is embedded in the title string, not a separate field.

---

### SQLite — `article_metadata` (via `query_sqlite_agnews_metadata`)
Contains publication metadata per article.

| Column | Type | Description |
|---|---|---|
| `article_id` | INTEGER (PK) | Links to MongoDB `article_id` |
| `author_id` | INTEGER | Foreign key to `authors` table |
| `region` | TEXT | Geographic region of publication (e.g., `Asia`, `North America`, `South America`) |
| `publication_date` | TEXT | Date in `YYYY-MM-DD` format |

---

### SQLite — `authors` (via `query_sqlite_agnews_metadata`)
Maps author IDs to names.

| Column | Type | Description |
|---|---|---|
| `author_id` | INTEGER (PK) | Unique author identifier |
| `name` | TEXT | Author's full name |

---

## 3. Join Keys

| Join | Key | Notes |
|---|---|---|
| MongoDB `articles` ↔ SQLite `article_metadata` | `article_id` | Both are integers starting at 0; types match directly |
| SQLite `article_metadata` ↔ SQLite `authors` | `author_id` | Standard integer FK within SQLite |

---

## 4. Domain Terms
- **Region**: Broad geographic classification of where an article was published — not derived from article content.
- **Source agency**: News wire embedded in `title` field (e.g., `(Reuters)`), not a structured column.

---

## 5. Known Query Patterns
- Find articles by region or publication date range
- Identify most prolific authors by article count
- Filter articles by keyword in `title` or `description`
- Join content with metadata to answer: *"Which articles from Asia were published in 2022?"*
- Aggregate articles per author or per region
- Extract source agency from title string using pattern matching on parenthetical suffix
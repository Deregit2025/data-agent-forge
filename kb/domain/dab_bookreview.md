# Knowledge Base: BookReview Dataset (DataAgentBench)

---

## 1. Dataset Overview

The bookreview dataset combines Amazon book metadata (PostgreSQL: `books_info`) with Amazon book reviews (SQLite: `review`), linkable via a fuzzy join on `book_id` ↔ `purchase_id`.

---

## 2. CRITICAL — MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_postgres_bookreview` | PostgreSQL | `books_info` table (book metadata: title, author, price, categories, details, description, features, etc.) |
| `query_sqlite_bookreview` | SQLite | `review` table (ratings, review text, helpful votes, verified purchase, timestamps) |

---

## 3. Tables and Collections

### Table: `books_info` (PostgreSQL via `query_postgres_bookreview`)

Full description: Contains Amazon book information including descriptions, price, details, title, etc. up to 2023.

| Field | Type | Meaning |
|---|---|---|
| `title` | text | Book title |
| `subtitle` | text | Book subtitle |
| `author` | text | Book author(s) |
| `rating_number` | bigint | Total number of ratings received |
| `features` | text | Book features — stored as string representation of list/dict |
| `description` | text | Book description — stored as string representation of list/dict |
| `price` | double precision | Book price in USD |
| `store` | text | Store information |
| `categories` | text | Book categories — stored as string representation of list/dict |
| `details` | text | Additional book details (may include publication date, language, ISBN, publisher, etc.) |
| `book_id` | text | Unique book identifier (used to join with `review.purchase_id`) |

**Important value formats:**
- `categories`, `description`, `features`: Appear list/dict-like but are raw strings. Use `LIKE` or string pattern matching (e.g., `categories LIKE '%Literature & Fiction%'`), not array operators.
- `details`: Plain text string; publication year/date and language information may be embedded here. Use `LIKE` or regex to extract (e.g., `details LIKE '%Publication date%'` or `details LIKE '%English%'`).
- `book_id`: Text string (e.g., ASIN-style alphanumeric). No guaranteed prefix format.

---

### Table: `review` (SQLite via `query_sqlite_bookreview`)

Full description: Contains Amazon book review information including ratings, text, helpfulness votes, etc. up to 2023.

| Field | Type | Meaning |
|---|---|---|
| `rating` | INTEGER | Rating given by reviewer on 1.0–5.0 scale |
| `title` | TEXT | Review title (NOT the book title) |
| `text` | TEXT | Full review text content |
| `review_time` | TEXT | Timestamp when review was posted (string format) |
| `helpful_vote` | INTEGER | Number of helpful votes the review received |
| `verified_purchase` | INTEGER | Whether purchase was verified (0 or 1 boolean stored as integer) |
| `purchase_id` | TEXT | Unique identifier linking to `book_id` in `books_info` |

**Important value formats:**
- `rating`: Stored as INTEGER in SQLite (despite being described as float 1.0–5.0; treat as numeric).
- `review_time`: Stored as TEXT string. Format likely ISO-like (e.g., `'2021-03-15 ...'` or `'2021-03-15'`). For filtering from 2020 onwards, use: `review_time >= '2020-01-01'` or `review_time LIKE '202%'`.
- `verified_purchase`: INTEGER — `1` = verified, `0` = not verified.
- `purchase_id`: Text string matching `book_id` format in `books_info`.

---

## 4. Join Keys

**Primary join relationship:**
- `books_info.book_id` (PostgreSQL) ↔ `review.purchase_id` (SQLite)
- These fields refer to the same book entities across different tables.
- **The field names do NOT match** — `book_id` vs `purchase_id`.
- Use a **fuzzy join approach**: fetch candidate IDs from one database, then filter in the other.

**Practical join strategy (cross-database):**
1. Query one database to get a list of relevant IDs (e.g., `book_id` values from `books_info`).
2. Pass those IDs as a filter (`IN (...)` clause) to the other database querying `purchase_id`.
3. Aggregate or join results in application logic.

**Verbatim from official hints:**
> "The fields 'book_id' in books_info and 'purchase_id' in review refer to the same book entities across different tables. While the field names
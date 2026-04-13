# Knowledge Base: Book Review Dataset

## 1. Dataset Overview
This dataset contains book metadata and customer reviews for books sold online, enabling analysis of book catalog information alongside reader ratings and review content.

---

## 2. Tables & Collections

### PostgreSQL — `books_info`
Contains catalog-level metadata for each book.

| Field | Type | Notes |
|---|---|---|
| `book_id` | text | Unique book identifier, format: `bookid_<number>` |
| `title` | text | Book title |
| `subtitle` | text | Includes format and publication date (e.g., `"Hardcover – May 8, 2012"`) |
| `author` | text | **JSON string** with keys: `avatar` (URL), `name` (string), `about` (array of strings) |
| `rating_number` | bigint | Total count of ratings received |
| `price` | double precision | Book price in USD |
| `store` | text | Seller/author credit line (e.g., `"Marcus Luttrell (Author)"`) |
| `categories` | text | **JSON array string**, e.g., `["Books", "Literature & Fiction", "History & Criticism"]` |
| `features` | text | **JSON array string** of feature bullet points |
| `description` | text | **JSON array string** of description sections |
| `details` | text | Free-text paragraph with publisher, edition, ISBN-10, ISBN-13, dimensions, weight, page count |

> ⚠️ `author`, `categories`, `features`, and `description` are stored as JSON-encoded strings, not native JSON/array types. Parsing is required to extract subfields.

---

### SQLite — `review`
Contains individual customer reviews linked to purchases.

| Field | Type | Notes |
|---|---|---|
| `purchase_id` | text | Links to a purchase; format: `purchaseid_<number>` |
| `rating` | integer | Star rating, range: 1–5 |
| `title` | text | Review headline |
| `text` | text | Full review body; may contain HTML tags (e.g., `<br />`) |
| `review_time` | text | Datetime string, format: `YYYY-MM-DD HH:MM:SS` |
| `helpful_vote` | integer | Number of users who marked the review helpful |
| `verified_purchase` | integer | Boolean flag: `1` = verified purchase, `0` = not verified |

---

## 3. Join Keys
There is **no direct foreign key** between `books_info` and `review` in the current schema. `books_info` uses `book_id` (`bookid_<n>`) and `review` uses `purchase_id` (`purchaseid_<n>`). These are different identifiers — cross-table joins are not currently supported without an intermediate mapping table.

---

## 4. Domain Terms
- **rating_number**: Total number of ratings (volume), not the average score
- **verified_purchase**: Confirms the reviewer bought the book through the platform
- **helpful_vote**: Peer-validated review usefulness count
- **store**: The credited seller or author, not a retail store name

---

## 5. Known Query Patterns
- Most/least reviewed books by `rating_number`
- Books filtered by category (requires JSON parsing of `categories`)
- Price range analysis across books
- Average star rating by book or time period (within `review`)
- Verified vs. unverified review breakdowns
- Most helpful reviews by `helpful_vote`
- Review volume trends over time using `review_time`
- Author lookup by parsing `author` JSON field
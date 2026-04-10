# DataAgentBench: Book Review Domain Schema & Known Patterns

## Databases
This domain (`bookreview`) requires querying across two distinct database systems: **PostgreSQL** and **SQLite**.

### 1. `books_database` (PostgreSQL)
Contains Amazon book information.
**Tables:**
- `books_info`:
  - `title` (str): Book title.
  - `subtitle` (str): Book subtitle.
  - `author` (str): Book author(s).
  - `rating_number` (int): Total number of ratings received.
  - `features` (str): Book features (stored as string representation of list/dict).
  - `description` (str): Book description (stored as string representation of list/dict).
  - `price` (float): Book price.
  - `store` (str): Store information.
  - `categories` (str): Book categories (stored as string representation of list/dict).
  - `details` (str): Additional book details.
  - `book_id` (str): Unique book identifier.

### 2. `review_database` (SQLite)
Contains Amazon book reviews.
**Tables:**
- `review`:
  - `rating` (float): Rating given by reviewer (1.0-5.0 scale).
  - `title` (str): Review Title.
  - `text` (str): Review text content.
  - `purchase_id` (str): Unique identifier linking to `book_id` in `books_info` table.
  - `review_time` (str): Timestamp when review was posted.
  - `helpful_vote` (int): Number of helpful votes received.
  - `verified_purchase` (bool): Whether purchase was verified.

---
## Known Query Patterns & Edge Cases
1. **Ill-formatted Join Keys:** `review.purchase_id` in SQLite joins to `books_info.book_id` in PostgreSQL. The columns have different names.
2. **Semi-structured Strings:** PostgreSQL fields like `features`, `description`, and `categories` contain string representations of Python lists or dictionaries. The agent must parse strings rather than standard JSON objects depending on the dialect.
3. **Unstructured Data:** The `text` field in SQLite contains the full content of the review.

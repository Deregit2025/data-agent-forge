# DataAgentBench: News Domain Schema & Known Patterns

## Databases
This domain (`agnews`) requires querying across two distinct database systems: **MongoDB** and **SQLite**.

### 1. `articles_database` (MongoDB)
Contains information about news articles.
**Collections:**
- `articles`:
  - `_id` (ObjectId)
  - `article_id` (int): Unique identifier for the article.
  - `title` (str): Title of the news article.
  - `description` (str): Free-text description/summary of the article.

### 2. `metadata_database` (SQLite)
Contains metadata linking articles to authors, regions, and dates.
**Tables:**
- `authors`:
  - `author_id` (int): Unique identifier for the author.
  - `name` (str): Full name of the author.
- `article_metadata`:
  - `article_id` (int): Links to `articles_database.articles.article_id` in MongoDB.
  - `author_id` (int): Links to `authors.author_id`.
  - `region` (str): Geographic region.
  - `publication_date` (str): Date in `YYYY-MM-DD` format.

---
## Known Query Patterns & Edge Cases
1. **Cross-Database Joins:** To find all articles written by an author, the agent must query SQLite `authors` and `article_metadata` to find the relevant `article_id`s, then pass those into MongoDB to fetch the titles/descriptions.
2. **Key Formats:** `article_id` is an `int` in both systems, which is a rare clean join. However, the agent must not confuse MongoDB's `_id` with `article_id`.
3. **Unstructured Data:** The `description` field in MongoDB contains natural language summaries of the news.

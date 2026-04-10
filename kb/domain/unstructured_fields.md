# Inventory of Unstructured Fields

DataAgentBench (DAB) introduces the requirement of "unstructured text transformation" (Challenge 1 & 4), meaning agents must extract structured data directly from narrative fields to answer queries. This document catalogs unstructured fields in the 12 DAB datasets.

## 1. Yelp Domain (MongoDB <-> DuckDB)
- **Database:** `businessinfo_database` (MongoDB)
  - **Collection:** `business`
  - **Field:** `description` (Type: string)
  - **Content:** Free-text descriptions of businesses, often containing operational details and location information. Note: Not structured JSON.
- **Database:** `user_database` (DuckDB)
  - **Table:** `review`
  - **Field:** `text` (Type: string)
  - **Content:** User reviews. Agents may need to parse this for sentiment or specific keywords.
  - **Table:** `tip`
  - **Field:** `text` (Type: string)
  - **Content:** User tips and concise suggestions.

## 2. Book Review Domain (PostgreSQL <-> SQLite)
- **Database:** `books_database` (PostgreSQL)
  - **Table:** `books_info`
  - **Field:** `features`, `description`, `categories` (Type: string)
  - **Content:** These fields store Python lists or dictionaries as raw strings. The data agent must parse the string or use string matching (e.g. `LIKE '%pattern%'`) instead of dialect-specific JSON extractions.
- **Database:** `review_database` (SQLite)
  - **Table:** `review`
  - **Field:** `text` (Type: string)
  - **Content:** Free-text user review.

## 3. Retail Domain
> *(To be expanded)*
- **Expected Fields:** Support notes, product reviews, and free-text feedback comments.

## 3. Healthcare Domain
> *(To be expanded)*
- **Expected Fields:** Patient encounter notes, doctor's transcriptions, unstructured lab reports.

## 4. Finance / Anti-Money Laundering Domain
> *(To be expanded)*
- **Expected Fields:** Transaction narrative lines, memo fields (e.g., "Wire transfer for XYZ INV CHK #124").

---
**Agent Instruction:** Do not attempt to use `SELECT column = 'xyz'` against Unstructured Fields. They contain prose. If a query requires filtering by location, and only `business.description` is available, you will need to retrieve the descriptions and extract the location via text processing or AI agent extraction.

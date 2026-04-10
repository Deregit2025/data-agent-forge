# Domain Knowledge Base - Changelog

## [2026-04-10]
- **Added:** `dab_agnews.md` - Documented the schema for the AG News domain within DataAgentBench. Covers MongoDB (`articles_database`) and SQLite (`metadata_database`) schemas and known edge cases.
- **Added:** `dab_bookreview.md` - Documented the schema for the Book Review domain within DataAgentBench. Covers PostgreSQL (`books_database`) and SQLite (`review_database`) schemas and known edge cases.
- **Updated:** `join_key_glossary.md` (KB v2) - Added entry for Book Review domain mapping `purchase_id` to `book_id`.
- **Updated:** `unstructured_fields.md` (KB v2) - Added Book Review domain unstructured string formats.
- **Added:** `dab_yelp.md` - Documented the schema for the Yelp domain within DataAgentBench. Covers MongoDB (`businessinfo_database`) and DuckDB (`user_database`) schemas and known edge cases.
- **Added:** `join_key_glossary.md` (KB v2) - Initialized the glossary for ill-formatted join keys. Added the first entry mapping MongoDB's `business_id` to DuckDB's `business_ref`.
- **Added:** `unstructured_fields.md` (KB v2) - Cataloged unstructured plaintext fields (e.g., `review.text`, `business.description`) that agents must extract data from.

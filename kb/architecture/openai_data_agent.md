# OpenAI In-House Data Agent Architecture

## 1. Six-Layer Context Architecture
OpenAI's internal data agent scales across thousands of databases by layering context. The context is built dynamically before a query is executed:
* **Layer 1 - Database Dialect & System Specs:** Knowing if the target is PostgreSQL, DuckDB, or MongoDB.
* **Layer 2 - Schema Metadata:** Column names, foreign keys, and data types for the specific tables involved.
* **Layer 3 - Institutional Knowledge:** Business definitions (e.g., "Fiscal Year starts in July", "Churn means 30 days inactive").
* **Layer 4 - Table Enrichment (Codex-powered):** Descriptive metadata generated for over 70,000 tables to allow semantic search over table schemas.
* **Layer 5 - Ill-formatted Key Mappings:** Known irregularities in the data (e.g., mapping `uid` in Mongo to `customer_id` in Postgres).
* **Layer 6 - Interaction Memory:** Lessons learned from previous user corrections in the specific session.

## 2. Table Enrichment at Scale
Instead of reading 70,000 tables at runtime, a background process uses Codex to pre-generate semantic embeddings and summaries of every table's purpose. The agent searches these summaries first, rather than querying raw schemas directly.

## 3. Closed-Loop Self-Correction
The agent is designed to expect failure. Execution does not stop at a SQL error.
* **Execution:** A query is run.
* **Diagnosis:** If it fails, the agent intercepts the error locally (e.g., "Field 'status' does not exist").
* **Self-Correction:** The agent queries Layer 2 (Schema Metadata) again to find the actual field name, rewrites the query, and re-executes.
* **Memory:** The fix is routed back into the Interaction Memory (Layer 6) so the agent doesn't make the same schema mistake twice.

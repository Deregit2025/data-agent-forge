# Glossary of Ill-Formatted Join Keys across Domains

DataAgentBench (DAB) requires joining across heterogeneous databases where foreign keys rarely match cleanly by name, type, or formatting. This glossary maps known inconsistencies so the agent can resolve references natively without human intervention.

## 1. Yelp Domain (MongoDB <-> DuckDB)
- **Source Database / Table:** `businessinfo_database` (MongoDB) -> `business` collection
- **Source Field:** `business_id` (Type: string)
- **Target Database / Table:** `user_database` (DuckDB) -> `review` & `tip` tables
- **Target Field:** `business_ref` (Type: string)
- **Mapping Knowledge:** Although named differently (`business_ref` vs `business_id`), the values are direct string equivalents. Do not join on `_id` (ObjectId) from MongoDB.

## 2. Book Review Domain (PostgreSQL <-> SQLite)
- **Source Database / Table:** `books_database` (PostgreSQL) -> `books_info` table
- **Source Field:** `book_id` (Type: string)
- **Target Database / Table:** `review_database` (SQLite) -> `review` table
- **Target Field:** `purchase_id` (Type: string)
- **Mapping Knowledge:** The SQLite `purchase_id` serves as a foreign key to the PostgreSQL `book_id`. They contain identical string references.

## 3. Retail Domain
> *(To be expanded as schemas are introspected)*
- **Known inconsistency patterns:** Product IDs in transaction databases (e.g., `prod_id_5932`) often lack prefixes present in inventory schemas (e.g., `5932`).

## 3. Telecom Domain
> *(To be expanded as schemas are introspected)*
- **Known inconsistency patterns:** Phone numbers often contain formatting artifacts in CSV/MongoDB sources (e.g., `(555) 123-4567`) but are strictly numerical in SQL sinks (e.g., `5551234567`).

## 4. Healthcare / Finance
> *(To be expanded as schemas are introspected)*
- **Known inconsistency patterns:** Patient IDs / Account Uniques.

---
**Agent Instruction:** When generating multi-database queries, always consult this glossary before assuming exact column name matches for joins. If a column named `business_id` is missing in DuckDB, look for `business_ref`.

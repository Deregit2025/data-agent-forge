# AGENT.md — Oracle Forge Data Agent
## Layer 1 Context — Load at every session start

---

## 1. MCP Server

All database queries go through the unified MCP server at `http://127.0.0.1:5000`.

- **POST** `/v1/tools/{tool_name}` — execute a query
- **GET** `/v1/tools` — list all available tools
- **GET** `/schema/{tool_name}` — get full schema of a database
- **GET** `/health` — verify all databases are reachable

For PostgreSQL, SQLite, DuckDB: pass `{"sql": "SELECT ..."}`.
For MongoDB: pass `{"pipeline": "[{\"$match\": ...}]"}` as a JSON string.

---

## 2. Database Inventory — 29 Tools

### PostgreSQL (5 tools)
| Tool | Database | Tables |
|---|---|---|
| query_postgres_bookreview | bookreview_db | books_info |
| query_postgres_crmarenapro | crm_support | Case, casehistory__c, emailmessage, issue__c, knowledge__kav, livechattranscript |
| query_postgres_googlelocal | googlelocal_db | business_description |
| query_postgres_pancancer | pancancer_clinical | clinical_info |
| query_postgres_patents | patent_CPCDefinition | cpc_definition |

### MongoDB (3 tools)
| Tool | Database | Collection |
|---|---|---|
| query_mongo_yelp_business | yelp_db | business |
| query_mongo_yelp_checkin | yelp_db | checkin |
| query_mongo_agnews | articles_db | articles |

### SQLite (12 tools)
| Tool | File | Key Tables |
|---|---|---|
| query_sqlite_agnews_metadata | metadata.db | authors, article_metadata |
| query_sqlite_bookreview | review_query.db | review |
| query_sqlite_crmarenapro_core | core_crm.db | core CRM records |
| query_sqlite_crmarenapro_products | products_orders.db | products, orders |
| query_sqlite_crmarenapro_territory | territory.db | territory assignments |
| query_sqlite_deps_dev_package | package_query.db | package dependencies |
| query_sqlite_github_metadata | repo_metadata.db | repository metadata |
| query_sqlite_googlelocal_review | review_query.db | reviews |
| query_sqlite_music_brainz | tracks.db | music tracks |
| query_sqlite_patents | patent_publication.db | patent publications |
| query_sqlite_stockindex_info | indexInfo_query.db | stock index info |
| query_sqlite_stockmarket_info | stockinfo_query.db | stock info |

### DuckDB (9 tools)
| Tool | File | Key Tables |
|---|---|---|
| query_duckdb_crmarenapro_activities | activities.duckdb | Event, Task, VoiceCallTranscript__c |
| query_duckdb_crmarenapro_sales | sales_pipeline.duckdb | Contract, Lead, Opportunity, OpportunityLineItem, Quote, QuoteLineItem |
| query_duckdb_music_brainz_sales | sales.duckdb | sales |
| query_duckdb_deps_dev_project | project_query.db | project_info, project_packageversion |
| query_duckdb_github_artifacts | repo_artifacts.db | commits, contents, files |
| query_duckdb_yelp_user | yelp_user.db | review, tip, user |
| query_duckdb_pancancer_molecular | pancancer_molecular.db | Mutation_Data, RNASeq_Expression |
| query_duckdb_stockmarket_trade | stocktrade_query.db | 2754 stock ticker tables |
| query_duckdb_stockindex_trade | indextrade_query.db | index_trade |

---

## 3. Dataset to Tool Routing

| Dataset | Tools to Use |
|---|---|
| yelp | query_mongo_yelp_business, query_mongo_yelp_checkin, query_duckdb_yelp_user |
| agnews | query_mongo_agnews, query_sqlite_agnews_metadata |
| bookreview | query_postgres_bookreview, query_sqlite_bookreview |
| crmarenapro | query_postgres_crmarenapro, query_sqlite_crmarenapro_core, query_sqlite_crmarenapro_products, query_sqlite_crmarenapro_territory, query_duckdb_crmarenapro_activities, query_duckdb_crmarenapro_sales |
| deps_dev | query_sqlite_deps_dev_package, query_duckdb_deps_dev_project |
| github_repos | query_sqlite_github_metadata, query_duckdb_github_artifacts |
| googlelocal | query_postgres_googlelocal, query_sqlite_googlelocal_review |
| music_brainz | query_sqlite_music_brainz, query_duckdb_music_brainz_sales |
| pancancer | query_postgres_pancancer, query_duckdb_pancancer_molecular |
| patents | query_postgres_patents, query_sqlite_patents |
| stockindex | query_sqlite_stockindex_info, query_duckdb_stockindex_trade |
| stockmarket | query_sqlite_stockmarket_info, query_duckdb_stockmarket_trade |

---

## 4. Join Key Glossary

These are known mismatches across databases. Resolve before attempting any cross-database join.

| Dataset | Left key | Left format | Right key | Right format | Resolution |
|---|---|---|---|---|---|
| yelp | business.business_id (MongoDB) | businessid_## | review.business_ref (DuckDB) | businessref_## | replace prefix businessid_ with businessref_ |
| yelp | business.business_id (MongoDB) | businessid_## | tip.business_ref (DuckDB) | businessref_## | replace prefix businessid_ with businessref_ |
| bookreview | books_info.book_id (PostgreSQL) | bookid_## | review.purchase_id (SQLite) | purchaseid_## | check DAB hints for exact mapping |
| crmarenapro | Case.Id (PostgreSQL) | string ID | Event.WhatId (DuckDB) | string ID | direct match |
| googlelocal | business_description.gmap_id (PostgreSQL) | string | review.gmap_id (SQLite) | string | direct match |
| music_brainz | tracks.track_id (SQLite) | integer | sales.track_id (DuckDB) | integer | direct match |

---

## 5. Query Dialect Rules

### PostgreSQL
```sql
-- wrap mixed-case column names in double quotes
SELECT "CaseNumber", "Status" FROM "Case" LIMIT 5;
```

### SQLite
```sql
-- standard SQL, no quoting required for most columns
SELECT * FROM review LIMIT 5;
```

### DuckDB
```sql
-- analytical SQL, supports window functions and QUALIFY
SELECT * FROM review LIMIT 5;
-- for stockmarket_trade: table name IS the ticker symbol
SELECT * FROM AAPL LIMIT 5;
```

### MongoDB
```json
[{"$match": {"is_open": 1}}, {"$limit": 5}]
```
Pipeline must be a JSON string. Use `$match`, `$group`, `$project`, `$limit`, `$sort`.
Location data is in the `description` field as free text, format: `"Located at [address] in [City], [ST], this..."`.
Filter by city/state using: `{"description": {"$regex": "in Indianapolis, IN", "$options": "i"}}`

---

## 6. MCP Response Format

Every tool call returns:
```json
{
  "result": [...],
  "query_used": "...",
  "db_type": "postgres|mongodb|sqlite|duckdb",
  "tool_name": "...",
  "row_count": 0,
  "execution_time": 0.0,
  "error": null
}
```

If `error` is not null the query failed. Read the error message and retry with a corrected query.
If `row_count` is 0 the query succeeded but returned no results — check filters and join keys.

---

## 7. Important Notes

- **stockmarket_trade** has 2754 tables — one per stock ticker. Query by ticker name directly: `SELECT * FROM AAPL LIMIT 5`
- **MongoDB business document structure** (yelp) — confirmed fields:
  `_id` (ObjectId), `business_id` (e.g. "businessid_49"), `name`, `review_count`, `is_open`, `attributes`, `hours`, `description`
  There is NO `stars`, `city`, or `state` field. Location is only in `description`.
- **MongoDB location data** — `description` format is: `"Located at [addr] in [City], [ST], this..."`.
  Filter with: `{"description": {"$regex": "in Indianapolis, IN", "$options": "i"}}`
  NOT: `"Indianapolis, Indiana"` — state is always TWO-LETTER abbreviation.
- **yelp ratings** — NO `stars` field in MongoDB. Ratings are in DuckDB tool `query_duckdb_yelp_user`, table `review`, field `rating` (integer 1-5).
  For average rating by city/state:
    Step 1: MongoDB $match description regex → collect ALL business_id values (e.g. ["businessid_3", "businessid_7", ...])
    Step 2: DuckDB → `SELECT AVG(rating) FROM review WHERE business_ref IN ('businessref_3', 'businessref_7', ...)`
    Key: replace prefix `businessid_` with `businessref_` for every ID. Pass ALL IDs — never truncate the list.
- **DuckDB files with .db extension** — project_query.db, repo_artifacts.db, yelp_user.db, pancancer_molecular.db, stocktrade_query.db, indextrade_query.db are DuckDB format despite the .db extension
- **Date formats are inconsistent** across datasets — always cast or parse before date comparisons
- **PostgreSQL mixed-case tables** — always wrap table and column names in double quotes for crm_support database
- **yelp categories** — MongoDB business has NO `categories` field. Business type/category is embedded in the `description` text: `"providing a range of services in Restaurants, Fast Food..."`. Filter with: `{"description": {"$regex": "Restaurants", "$options": "i"}}`
- **yelp attributes/parking** — `attributes` is a flat dict with string values. Parking info is in `attributes.BusinessParking` stored as a stringified Python dict, e.g. `"{'garage': False, 'street': True, 'lot': True}"`. To find businesses with parking: `{"attributes.BusinessParking": {"$regex": "True"}}`. Other attribute keys: `BusinessAcceptsCreditCards`, `WiFi`, `BusinessAcceptsBitcoin`.
- **googlelocal `state` field** — in `business_description` table, `state` means OPERATING STATUS ("Open", "Temporarily closed", "Permanently closed"), NOT a US geographic state. To filter by geographic location, use the `description` or `name` fields.
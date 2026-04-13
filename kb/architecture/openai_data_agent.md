# Oracle Forge — System Architecture

## KB v1 — Architecture Layer
This document describes the Oracle Forge system architecture for injection into the agent's Layer 1 context.

---

## 1. System Overview

Oracle Forge is a multi-database AI data agent built with LangGraph. It decomposes natural language queries into database-specific sub-tasks, executes them via a unified MCP server, and synthesizes the results into a single answer.

The system handles four database types simultaneously:
- **PostgreSQL** — relational, normalized enterprise data
- **MongoDB** — document store with nested structures and free-text fields
- **SQLite** — lightweight relational, often reference/metadata tables
- **DuckDB** — analytical columnar engine, large fact tables, window functions

---

## 2. Core Components

### 2.1 OracleForgeAgent (`agent/main.py`)

Entry point. Instantiated with:
- `query_dir`: DAB query directory (contains query.json, ground_truth.csv, validate.py)
- `db_description`: concatenated KB context (Layer 1 + Layer 2 + Layer 3)
- `db_config_path`: path to dataset's db_config.yaml
- `max_iterations`: maximum conductor loop iterations (default 10)

The agent loads three-layer context, instantiates the Conductor, runs it, and returns the final answer string.

### 2.2 Conductor (`agent/conductor.py`)

LangGraph state machine. Receives the query + full KB context. Responsibilities:
1. **Decompose** — break the NL query into sub-tasks, one per database that needs to be queried
2. **Route** — select the correct sub-agent and MCP tool for each sub-task
3. **Execute** — call sub-agents in dependency order (prior results fed into dependent queries)
4. **Synthesize** — merge all sub-results into a single coherent answer

The Conductor does not write SQL or pipelines directly — it delegates to sub-agents.

### 2.3 Sub-Agents (`agent/sub_agents/`)

Specialist agents for each database type. Each sub-agent:
1. Fetches the tool schema from `GET /schema/{tool_name}`
2. Calls Claude (via OpenRouter) to generate a SQL query or MongoDB pipeline
3. Executes via `POST /v1/tools/{tool_name}`
4. If error: calls `recovery_router.recover()` and retries (max 2 attempts)
5. Returns a structured MCP result dict

| Sub-agent | File | DB type | Generates |
|---|---|---|---|
| PostgreSQL | `postgres_agent.py` | PostgreSQL | SQL SELECT with double-quoted identifiers |
| MongoDB | `mongo_agent.py` | MongoDB | JSON aggregation pipeline |
| SQLite | `sqlite_agent.py` | SQLite | Standard SQL SELECT |
| DuckDB | `duckdb_agent.py` | DuckDB | Analytical SQL with window functions |

### 2.4 MCP Server (`mcp/mcp_server.py`)

FastAPI server at `http://127.0.0.1:5000`. Provides:
- `POST /v1/tools/{tool_name}` — execute a query
- `GET /v1/tools` — list all 29 available tools
- `GET /schema/{tool_name}` — get full schema (table names, column names, sample rows)
- `GET /health` — verify all database connections

All tools accept `{"sql": "..."}` for relational DBs or `{"pipeline": "[...]"}` for MongoDB.

### 2.5 Self-Correction (`agent/self_correction/`)

Two-module failure recovery system:

**`failure_types.py`** — Typed failure taxonomy:
- `SQL_SYNTAX_ERROR` — malformed SQL
- `COLUMN_NOT_FOUND` — field doesn't exist in schema
- `TABLE_NOT_FOUND` — wrong table name
- `CROSS_DB_KEY_MISMATCH` — foreign key prefix wrong
- `EMPTY_RESULT` — query succeeded but returned 0 rows
- `PIPELINE_PARSE_ERROR` — MongoDB pipeline is invalid JSON

**`recovery_router.py`** — Routes each failure type to a targeted fix strategy:
- SQL syntax errors → rewrite with schema grounding
- Column not found → inspect schema, substitute correct field name
- Cross-DB key mismatch → apply prefix replacement
- Empty result → broaden filters, check join key format

---

## 3. Three-Layer Context Engineering

Context is injected into every sub-agent's system prompt:

| Layer | Source | Content |
|---|---|---|
| Layer 1 | `agent/AGENT.md` | MCP tools inventory, join key glossary, query dialect rules, critical notes |
| Layer 2 | `kb/domain/dab_{dataset}.md` | Dataset-specific schema, field types, known query patterns |
| Layer 3 | `kb/corrections/corrections_log.md` | Self-learned failure patterns from prior benchmark runs |

Layer 3 is the self-learning loop. `utils/autodream.py` reads new corrections and appends learnings to the domain KB files. After each benchmark run, the KB improves automatically.

---

## 4. Evaluation Architecture

**`eval/harness.py`** — Benchmark runner:
- Iterates all 54 DAB queries
- Runs N trials per query (default 5)
- Applies early stopping when majority reached
- Aborts on `RateLimitError` to save partial results
- Writes `eval/results/benchmark_{run_id}.json`

**`eval/scorer.py`** — Validation:
- Loads each query's `validate.py` dynamically via importlib
- Calls `mod.validate(answer)` → returns bool or structured result
- Handles missing validate.py, empty answers, and validation exceptions

**`eval/regression_suite.py`** — Regression detection:
- Loads two benchmark result JSONs (baseline + current)
- Computes per-query diffs: regressions and improvements
- Returns non-zero exit code if regressions exist (CI integration)

---

## 5. Data Flow for a Single Query

```
1. Harness loads query: "What is the avg rating of open restaurants in Indianapolis?"
2. OracleForgeAgent loads KB context (3 layers)
3. Conductor decomposes:
   Sub-task A: MongoDB — find all open businesses in Indianapolis
   Sub-task B: DuckDB — get avg rating for those business IDs
4. mongo_agent.run("query_mongo_yelp_business", "Find open businesses in Indianapolis")
   → generates: [{"$match": {"is_open": 1, "description": {"$regex": "in Indianapolis, IN", "$options": "i"}}}, {"$project": {"business_id": 1}}]
   → returns: [{"business_id": "businessid_3"}, {"business_id": "businessid_7"}, ...]
5. entity_resolver translates: businessid_3 → businessref_3, businessid_7 → businessref_7, ...
6. duckdb_agent.run("query_duckdb_yelp_user", "Get avg rating", prior_results=[mongo_result])
   → generates: SELECT AVG(rating) FROM review WHERE business_ref IN ('businessref_3', 'businessref_7', ...)
   → returns: [{"avg(rating)": 3.87}]
7. Conductor synthesizes: "3.87"
8. Harness scores: score("3.87", query_dir) → validates against ground_truth.csv
```

---

## 6. Infrastructure

| Component | Technology | Location |
|---|---|---|
| Shared server | tenai-infra | Accessible via Tailscale |
| Databases | PostgreSQL 15, MongoDB 7, SQLite 3, DuckDB 0.10 | Shared server |
| Agent | Python 3.11 + LangGraph | Shared server |
| MCP server | FastAPI + uvicorn | Port 5000, shared server |
| LLM | Claude Sonnet 4.6 via OpenRouter | Cloud API |
| Model ID | anthropic/claude-sonnet-4.6 | OpenRouter routing |

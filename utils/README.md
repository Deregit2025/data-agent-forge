# Oracle Forge — Shared Utility Library

Reusable modules for multi-database agent development. All modules are independently importable, tested, and documented below.

---

## Modules

### 1. `multi_pass_retrieval` — Iterative Query Refinement

Executes a retrieval task against an MCP tool, broadens the query if the first pass returns no results, and retries up to a configurable depth.

**When to use:** Any sub-agent that might return empty results on the first query attempt — e.g., when a business name is partially spelled, a date range is too narrow, or an enum value is unknown.

```python
from utils.multi_pass_retrieval import retrieve

result = retrieve(
    tool_name="query_duckdb_yelp_user",
    task="Find all reviews for businessref_42 with rating >= 4",
    context="DuckDB yelp_user.db — tables: review, tip, user",
    db_type="duckdb",
    max_passes=3,
)

# result is a standard MCP response dict:
# {"result": [...], "row_count": N, "error": null, ...}
print(result["result"])
```

**How it works:**
1. Pass 1 — runs the task as-is against the tool
2. If `row_count == 0`, calls the LLM to broaden the query (relax filters, try alternate field names)
3. Pass 2–N — retries with broadened query until results found or `max_passes` reached

---

### 2. `entity_resolver` — Cross-Database Key Translation

Detects and resolves foreign key prefix mismatches between databases. For example, MongoDB uses `businessid_42` while DuckDB uses `businessref_42` for the same entity.

**When to use:** Before building any IN clause that bridges MongoDB → DuckDB (yelp), PostgreSQL → SQLite (bookreview), or any cross-DB join listed in `agent/AGENT.md`.

```python
from utils.entity_resolver import resolve, resolve_auto, build_join_clause

# Explicit resolution using known mapping
resolved = resolve(
    entity_ids=["businessid_3", "businessid_7", "businessid_42"],
    source_prefix="businessid_",
    target_prefix="businessref_",
)
# → ["businessref_3", "businessref_7", "businessref_42"]

# Auto-detect prefix and resolve
resolved = resolve_auto(
    entity_ids=["businessid_3", "businessid_7"],
    target_db="duckdb_yelp_user",
)
# → ["businessref_3", "businessref_7"]

# Build SQL IN clause from resolved IDs
sql_clause = build_join_clause(
    ids=resolved,
    field="business_ref",
    db_type="sql",
)
# → "business_ref IN ('businessref_3', 'businessref_7')"
```

**Known mappings (from `agent/AGENT.md`):**

| Source prefix | Target prefix | Dataset |
|---|---|---|
| `businessid_` | `businessref_` | yelp (MongoDB → DuckDB) |
| `bookid_` | `purchaseid_` | bookreview (PostgreSQL → SQLite) |

---

### 3. `contract_validator` — Output Contract Enforcement

Validates that an agent answer meets the expected contract: non-empty, contains a concrete value, is consistent with intermediate query results, and matches the question's expected format (number, list, yes/no).

**When to use:** At the end of any conductor answer synthesis step, before returning the final answer to the harness.

```python
from utils.contract_validator import validate, validate_and_enforce, ValidationMode

# Basic validation — returns ValidationResult
result = validate(
    answer="Indianapolis",
    question="Which city has the highest average review rating?",
    db_results=[{"city_match": "Indianapolis", "avg_rating": 4.2}],
    mode=ValidationMode.STRICT,
)

print(result.is_valid)   # True or False
print(result.reason)     # Human-readable explanation
print(result.to_dict())  # Serializable dict for logging

# Enforce — raises ValueError if validation fails
validated_answer = validate_and_enforce(
    answer="42",
    question="How many businesses are open in Las Vegas?",
    db_results=[{"count": 42}],
)
# → "42"  (passes through if valid)
# → raises ValueError("answer failed contract: ...") if invalid
```

**Validation checks:**
1. `_check_not_empty` — answer is not blank or whitespace
2. `_check_has_concrete_value` — answer contains a number, name, or concrete fact (not just "I don't know")
3. `_check_consistent_with_results` — answer is entailed by the DB result rows
4. `_check_format_matches_question` — numeric questions get numeric answers, yes/no questions get yes/no answers

**Modes:**
- `ValidationMode.STRICT` — all 4 checks must pass
- `ValidationMode.LENIENT` — checks 1–2 only (use when DB results are unavailable)
- `ValidationMode.FORMAT_ONLY` — check 4 only (use for format-specific validation)

---

### 4. `autodream` — Self-Learning KB Updates

Reads the corrections log, extracts failure patterns, and calls Claude to update the corresponding domain KB file. Runs automatically after every benchmark run.

**When to use:** Typically called by `eval/harness.py` automatically. Call manually after adding corrections to `kb/corrections/corrections_log.md`.

```python
from utils.autodream import consolidate, log_correction

# Log a single failure for later consolidation
log_correction(
    dataset="yelp",
    query_id=1,
    wrong_approach="Filtered MongoDB by city field — field does not exist",
    correct_approach="Use regex on description field: {'description': {'$regex': 'in Indianapolis, IN'}}",
)

# Consolidate all corrections into KB domain files
consolidate()
# → reads kb/corrections/corrections_log.md
# → calls Claude to synthesize learnings per dataset
# → appends to kb/domain/dab_yelp.md, etc.
# → writes kb/corrections/CHANGELOG.md entry
```

---

## Running Tests

```bash
# Run all utility tests
pytest utils/tests/ -v

# Run a single module's tests
pytest utils/tests/test_entity_resolver.py -v
pytest utils/tests/test_contract_validator.py -v
pytest utils/tests/test_multi_pass_retrieval.py -v
pytest utils/tests/test_autodream.py -v
```

All tests use mocked MCP/OpenAI calls — no live server required.

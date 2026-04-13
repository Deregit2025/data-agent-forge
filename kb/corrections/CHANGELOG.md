# KB Corrections — CHANGELOG

## v1.0 — 2026-04-11

**Initial corrections log committed from development testing.**

Corrections documented:
1. **yelp/query1** — businessid_ vs businessref_ cross-DB prefix mismatch → fixed in duckdb_agent.py + AGENT.md
2. **yelp/location** — city field doesn't exist in MongoDB; use description regex → fixed in AGENT.md + dab_yelp.md
3. **yelp/ratings** — stars field doesn't exist in MongoDB; ratings in DuckDB review table → fixed in AGENT.md
4. **yelp/state_abbrev** — state must be 2-letter abbreviation in location regex, not full name → fixed in AGENT.md
5. **yelp/truncated_ids** — prior results capped at 5 rows caused incomplete IN clause → fixed in duckdb_agent.py
6. **mongo_agent/db_type** — wrong db_type passed to recovery router → fixed in mongo_agent.py

All 6 corrections have been applied to code and/or KB documents. autoDream will consolidate domain-level learnings into `kb/domain/dab_yelp.md` on next run.

**Status:** KB Corrections v1 — POPULATED (6 real failures from development)

---

## Planned: After Next Benchmark Run

- autoDream will add entries from all 54-query benchmark
- Expected: 10–20 new corrections across multiple datasets
- Domain KB files will be updated automatically


## 2026-04-14

Manual KB enrichment + injection test suite + agent bug fixes.

**KB completions (truncated files repaired):**
- `dab_pancancer.md` — added join keys (Patient_description ↔ ParticipantBarcode), cancer acronyms, log10 formula, pitfalls (days_to_death is TEXT, bracket values filtering)
- `dab_crmarenapro.md` — added 6 missing tables (knowledge__kav, issue__c, casehistory__c, emailmessage, livechattranscript, territory), join keys section, data quality rules (25% IDs have leading `#` — use LTRIM, 20% text fields have trailing whitespace — use TRIM)
- `dab_patents.md` — completed citation hint, added Section 5 query patterns (LIKE for CPC codes, free-text date handling)
- `dab_deps_dev.md` — added VersionInfo JSON parsing (`LIKE '%"IsRelease": true%'`, Ordinal sorting), three-way join sequence, Section 6 query patterns
- `dab_bookreview.md` — completed 3 query examples (decade grouping, English Lit&Fiction 5.0 rating, Children's Books ≥4.5 from 2020)
- `dab_github_repos.md` — added Section 6 with 3 query patterns (non-Python repos, copied files, commits by year)
- `dab_music_brainz.md` — completed query3 (DuckDB revenue SQL, entity resolution across duplicate track_ids)
- `dab_stockindex.md` — completed Europe exchange-to-symbol mapping (DAX → `^GDAXI`, CAC 40 → `^FCHI`, FTSE 100 → `^FTSE`)
- `dab_agnews.md` — completed expected answer format line

**Injection test suite added (`injection_tests/`):**
- `test_join_keys.md` — 7 tests covering cross-database join key transformations
- `test_unstructured_fields.md` — 5 tests covering free-text/JSON-like field parsing
- `test_retail.md` — 5 tests covering multi-dataset query routing (tool selection)

**Agent bug fixes:**
- All sub-agents + recovery_router: model `anthropic/claude-haiku-4-5-20251001` (invalid) → `anthropic/claude-3-5-haiku` (valid OpenRouter ID)
- `conductor.py` synthesize_node: `max_tokens=50 → 150`; fixed `step_purpose` → `task` key lookup; made JOINING RULE dataset-conditional
- `conductor.py` `_precompute_joins`: added `_precompute_googlelocal` (PostgreSQL gmap_id → SQLite avg_rating join)
- `conductor.py` plan_node: removed SQL field from plan format (purpose-only, no premature query generation)
- `postgres_agent.py` + `sqlite_agent.py`: upgraded prior_results from `[:5]` truncation to full ID extraction
- `duckdb_agent.py`: made AVERAGING RULE and PREFIX RULE conditional on `"yelp" in tool_name`

## 2026-04-13 14:59

Schema introspector run — DAB-description-first approach.

- `dab_stockindex.md` — regenerated from DAB descriptions + MCP schemas + 3 queries
- `dab_stockmarket.md` — regenerated from DAB descriptions + MCP schemas + 5 queries

## 2026-04-13 14:49

Schema introspector run — DAB-description-first approach.

- `dab_crmarenapro.md` — regenerated from DAB descriptions + MCP schemas + 13 queries
- `dab_deps_dev.md` — regenerated from DAB descriptions + MCP schemas + 2 queries
- `dab_github_repos.md` — regenerated from DAB descriptions + MCP schemas + 4 queries
- `dab_music_brainz.md` — regenerated from DAB descriptions + MCP schemas + 3 queries
- `dab_pancancer.md` — regenerated from DAB descriptions + MCP schemas + 3 queries
- `dab_patents.md` — regenerated from DAB descriptions + MCP schemas + 3 queries
- `dab_stockindex.md` — regenerated from DAB descriptions + MCP schemas + 3 queries
- `dab_stockmarket.md` — regenerated from DAB descriptions + MCP schemas + 5 queries

## 2026-04-13 13:28

Schema introspector run — DAB-description-first approach.

- `dab_agnews.md` — regenerated from DAB descriptions + MCP schemas + 4 queries
- `dab_bookreview.md` — regenerated from DAB descriptions + MCP schemas + 3 queries
- `dab_googlelocal.md` — regenerated from DAB descriptions + MCP schemas + 4 queries
# KB Domain Changelog

## 2026-04-11

Schema introspector run — all domain files generated.

- `dab_yelp.md` — generated from 3 tools
- `dab_agnews.md` — generated from 2 tools
- `dab_bookreview.md` — generated from 2 tools
- `dab_crmarenapro.md` — generated from 6 tools
- `dab_deps_dev.md` — generated from 2 tools
- `dab_github_repos.md` — generated from 2 tools
- `dab_googlelocal.md` — generated from 2 tools
- `dab_music_brainz.md` — generated from 2 tools
- `dab_pancancer.md` — generated from 2 tools
- `dab_patents.md` — generated from 2 tools
- `dab_stockindex.md` — generated from 2 tools
- `dab_stockmarket.md` — generated from 2 tools

Each document was enriched with Claude and requires injection testing before use.

# DataAgentBench: Deps.Dev V1 Domain Schema

## Databases
This domain (`DEPS_DEV_V1`) requires querying across dependency graph data, primarily using SQLite and DuckDB based on standard vulnerability and package schemas.

*(To be fully expanded from db_description)*

## Known Query Patterns & Edge Cases
- Expect complex recursive relationships between packages and dependencies.
- Version strings are stored as text and require semver-aware comparisons rather than simple string matching.

# DataAgentBench: Stock Index Domain Schema

## Databases
This domain (`stockindex`) requires querying across PostgreSQL and MongoDB containing indices and market prices.

*(To be fully expanded from db_description)*

## Known Query Patterns & Edge Cases
- Ticker symbols map across varying database conventions. Time series window logic using standard SQL rather than vendor-specific aggregations where possible.

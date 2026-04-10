# DataAgentBench: PanCancer Atlas Domain Schema

## Databases
This domain (`PANCANCER_ATLAS`) requires traversing genomics datasets across database dialects.

*(To be fully expanded from db_description)*

## Known Query Patterns & Edge Cases
- Gene symbols are often heavily encoded and require exact string lookups (e.g., matching across SQL tables storing patient clinical details and MongoDB stores of sequencing data).

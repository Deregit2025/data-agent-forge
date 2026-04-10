# DataAgentBench: GitHub Repos Domain Schema

## Databases
This domain (`GITHUB_REPOS`) requires querying across PostgreSQL and MongoDB containing issue, PR, and repo data.

*(To be fully expanded from db_description)*

## Known Query Patterns & Edge Cases
- Distinguishing between `issue_id` and `repository_id`.
- Unstructured text in issue bodies and pull request descriptions.

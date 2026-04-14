# Oracle Forge — Knowledge Base

The KB is the institutional memory of the agent. It is injected into every query as context, giving the agent the domain knowledge it cannot derive from code alone: which fields actually exist, how join keys transform across databases, and what failure patterns to avoid.

---

## Three-Layer Architecture

| Layer | Directory | Role | Loaded When |
|---|---|---|---|
| Layer 1 | `agent/AGENT.md` | MCP tools, join keys, dialect rules — the always-on layer | Every query |
| Layer 2 | `kb/domain/dab_*.md` | Dataset-specific schemas, field types, query patterns | Matched by dataset name |
| Layer 3 | `kb/corrections/corrections_log.md` | Self-learned failure patterns from real benchmark runs | Every query |

---

## Directory Structure

```
kb/
├── README.md                  ← this file
├── architecture/              ← KB v1: system design documentation
│   ├── CHANGELOG.md
│   ├── openai_data_agent.md   ← agent component design
│   ├── claude_code_memory.md  ← three-layer KB design rationale
│   └── injection_tests/       ← evidence tests for architecture KB
│       ├── test_claude_code.md
│       └── test_openai_agent.md
├── domain/                    ← KB v2: one file per DAB dataset
│   ├── CHANGELOG.md
│   ├── join_key_glossary.md   ← cross-DB join rules for all 12 datasets
│   ├── unstructured_fields.md ← free-text and JSON field parsing patterns
│   ├── dab_yelp.md
│   ├── dab_agnews.md
│   ├── dab_bookreview.md
│   ├── dab_crmarenapro.md
│   ├── dab_deps_dev.md
│   ├── dab_github_repos.md
│   ├── dab_googlelocal.md
│   ├── dab_music_brainz.md
│   ├── dab_pancancer.md
│   ├── dab_patents.md
│   ├── dab_stockindex.md
│   ├── dab_stockmarket.md
│   └── injection_tests/       ← evidence tests for domain KB
│       ├── test_join_keys.md
│       ├── test_unstructured_fields.md
│       └── test_retail.md
├── corrections/               ← KB v3: failure memory from real runs
│   ├── CHANGELOG.md
│   └── corrections_log.md     ← auto-updated by utils/autodream.py
└── evaluation/                ← KB v4: harness design and scoring methodology
    ├── CHANGELOG.md
    ├── harness_design.md
    └── injection_tests/
        └── test_harness.md
```

---

## KB v1 — Architecture (`kb/architecture/`)

Documents the system design decisions: why three layers, how the context budget is managed, component responsibilities, and data flow. This layer does not change unless the agent architecture changes.

---

## KB v2 — Domain (`kb/domain/`)

One file per DAB dataset. Each file documents:
- **Tool mapping**: which MCP tool to use for each table
- **Schema**: confirmed field names, types, and nullability
- **Join keys**: how IDs transform when crossing database boundaries
- **Query patterns**: known-good SQL/pipeline templates
- **Pitfalls**: fields that don't exist, formats that surprise the agent

Supporting files:
- `join_key_glossary.md` — all cross-DB join rules in one place
- `unstructured_fields.md` — how to query free-text and JSON-like fields

### Updating a domain KB file

When the agent fails on a dataset, update the matching `dab_{dataset}.md`:
1. Add the field or join key that was missing
2. Add a query pattern showing the correct approach
3. Add a note to `kb/corrections/corrections_log.md`
4. Update `CHANGELOG.md` with a dated entry

---

## KB v3 — Corrections (`kb/corrections/`)

Failure memory from real benchmark runs. Read by `utils/autodream.py` to propagate corrections back into domain KB files.

Format for each entry:
```
### [YYYY-MM-DD] Dataset: {dataset} | Query: {query_id}

**Wrong:** {what the agent did}
**Correct:** {what it should do}
**Impact:** {file changed and what changed}
```

Corrections are never deleted — they record the full learning history.

---

## KB v4 — Evaluation (`kb/evaluation/`)

Documents the harness design, scoring methodology, and early-stopping algorithm. Reference this before modifying `eval/harness.py` or `eval/scorer.py`.

---

## Injection Testing Protocol

Every KB document has corresponding injection tests in an `injection_tests/` subdirectory. Each test specifies:
- **Injection prompt**: the query that exercises the KB rule
- **Expected behavior (PASS)**: what the agent should do with KB context loaded
- **Failure mode (FAIL)**: what happens without the KB rule
- **KB source**: the exact file and section that provides the fix

Tests are run manually by injecting the prompt into the agent and comparing output. They serve as regression evidence — proof that the KB actively changes agent behavior.

---

## Maintenance

| Action | Files to update |
|---|---|
| Add a new failure pattern | `corrections_log.md` + relevant `dab_*.md` |
| Add a new dataset | New `dab_{name}.md` + `join_key_glossary.md` entry + `domain/CHANGELOG.md` |
| Fix a schema error | The relevant `dab_*.md` + `domain/CHANGELOG.md` |
| Update harness design | `evaluation/harness_design.md` + `evaluation/CHANGELOG.md` |

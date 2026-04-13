AI-DLC INCEPTION DOCUMENT
Project: Oracle Forge Data Agent
Sprint: Week 9 — Benchmark, Adversarial Probing, and Signal Corps
Role: Driver + Intelligence Officers
Current Phase: Construction → Operations

---

## 1. Press Release

Oracle Forge is a production-grade multi-database AI data agent that answers natural language questions across four database types simultaneously. In this sprint, the team moves from a working agent into full evaluation mode: running the complete DataAgentBench benchmark across all 54 queries, executing adversarial probing to find and fix agent failure patterns, and demonstrating measurable improvement from the Week 8 baseline through the self-correction and KB corrections system. The sprint ends with a benchmark score submitted to the DataAgentBench leaderboard, a documented proof that the agent learned from its failures, and a complete Signal Corps engagement portfolio.

---

## 2. Current Project State

### What exists now (carried from Sprint 1)
- MCP server running with 29 database tools (PostgreSQL, MongoDB, SQLite, DuckDB)
- Conductor agent fully implemented with LangGraph orchestration
- Four sub-agents (postgres, mongo, sqlite, duckdb) with self-correction loops
- Evaluation harness: harness.py, scorer.py, regression_suite.py, trace_schema.py
- Knowledge Base Layer 1 (AGENT.md): 29 tools, join keys, dialect rules
- Knowledge Base Layer 2 (kb/domain/): all 12 dataset schemas documented
- Utils library: schema_introspector, autodream, contract_validator, entity_resolver, multi_pass_retrieval
- Test suites: 60+ tests across all 4 utility modules

### What is being built in this sprint
- Full benchmark run: 54 queries × 5 trials each
- Adversarial probe library: 15+ probes across 3+ failure categories
- KB Layer 3 (corrections log): populated from benchmark failures via autoDream
- Score log showing measurable improvement from baseline to final run
- Signal Corps: published articles, engagement logs, community participation
- GitHub PR to ucbepic/DataAgentBench with results JSON
- Demo video: live agent + self-correction + probe walkthrough

### What does NOT exist yet
- Benchmark results (API key required)
- KB v3 corrections (will be auto-generated after benchmark runs)
- Signal Corps articles and engagement portfolio
- Score log progression data points
- GitHub PR to DataAgentBench repository

---

## 3. Honest FAQ — User View

**What can the agent do now?**
It can answer natural language questions that require querying 1–4 different database types simultaneously. It self-corrects on SQL/pipeline errors. It uses institutional knowledge from the KB to resolve cross-database entity mismatches.

**Can external users try it?**
The agent runs on the shared team server. Team members access via Tailscale. A web API layer is not yet built — queries are submitted via CLI.

**How good is it?**
We do not yet have a full benchmark score because the API key was exhausted during the first test run. Our target is a measurable improvement between the Week 8 baseline run and the final submission.

**What is the self-correction loop?**
When a query fails (SQL error, empty results, wrong format), the agent detects the failure type (SQL syntax error, wrong join key, missing field, etc.) and applies a targeted fix without restarting from scratch. Failures are logged to `kb/corrections/corrections_log.md` and autoDream updates the domain KB so the same mistake is not repeated.

---

## 4. Honest FAQ — Technical View

**What is the hardest part this sprint?**
The cross-database join pattern: MongoDB returns `businessid_N` identifiers, DuckDB expects `businessref_N`. If the prior results from MongoDB are truncated or the prefix is not replaced, the DuckDB IN clause returns 0 rows. This was the root cause of our first benchmark failure on yelp/query1. The fix (full ID extraction + prefix replacement in duckdb_agent.py) is deployed.

**What risks exist at this stage?**
- API key cost: 54 × 5 = 270 trials × ~$0.02/call = ~$5.40 per full run. The team needs a fresh API key budget.
- Rate limits: OpenRouter weekly key limit. Fixed by RateLimitError abort in harness.py.
- MongoDB field assumptions: AGENT.md now documents confirmed field list (no `stars`, `city`, `state` fields).
- Score variance: with 5 trials per query, majority pass (3/5) is required — some queries may pass on 2/5 and be miscounted as fails.

**Why does the agent sometimes return an empty answer?**
Three known causes: (1) cross-DB join key mismatch (fixed), (2) MongoDB location filter using wrong format (fixed to two-letter state abbreviation), (3) LLM generates a query for a field that does not exist (mitigated by KB domain docs showing confirmed fields).

**Why not use LangChain's built-in tool calling instead of the custom MCP layer?**
The MCP server provides a unified interface across all 4 DB types with consistent response format, error handling, and schema inspection. Sub-agents are simpler and more debuggable than tool-calling agents because the query generation and execution are explicit steps we control.

---

## 5. Key Decisions (Sprint 2 — Construction/Operations)

### Decision 1: Run benchmark before probing
Run the full benchmark first to collect real failure data. Then write adversarial probes based on actual failures, not hypothetical ones. This ensures the probe library documents real failure patterns with real fixes.

### Decision 2: autoDream runs after every partial run
Even partial benchmark runs (some datasets) produce correction data. autoDream consolidates after each run. This means KB v3 is built incrementally — we don't need to wait for the full 54-query run to start learning.

### Decision 3: Probe library targets DAB's 4 failure categories
The challenge requires 3+ of 4 categories:
- Multi-database routing (cross-DB joins, wrong tool selection)
- Ill-formatted key mismatch (businessid_ vs businessref_, prefix errors)
- Unstructured text extraction (MongoDB description field, parsing location)
- Domain knowledge gap (no `stars` field in yelp, inconsistent date formats)

We target all 4 to maximize evaluation score.

### Decision 4: Signal Corps articles reference technical findings
Signal Corps articles are not generic AI summaries. They cite specific Oracle Forge findings: the MongoDB field gap, the prefix mismatch fix, the multi-pass retrieval pattern. This satisfies the "technical credibility maintained" requirement.

---

## 6. Definition of Done — Sprint 2

The Construction → Operations gate is approved when:

1. Full benchmark run completed: all 54 DAB queries, minimum 5 trials each
2. Results JSON saved to `eval/results/benchmark_{run_id}.json`
3. Score log shows at least 2 data points (baseline + improved run)
4. Adversarial probe library: 15+ probes across 3+ failure categories, fixes documented
5. KB corrections log: minimum 5 entries from real benchmark failures
6. autoDream has run and updated at least one domain KB file
7. GitHub PR opened to ucbepic/DataAgentBench with results JSON and AGENT.md
8. Signal Corps: engagement_log.md with Week 8 post links, community_log.md with substantive comments
9. Signal Corps: at least one published article per member (600+ words, LinkedIn or Medium)
10. Demo video: max 8 minutes, hosted on YouTube or Google Drive (no login required)
11. Team approves readiness for Operations phase

---

## 7. Scope of This Sprint

### Included Now
- Benchmark execution (all 54 queries)
- Adversarial probing
- KB corrections (Layer 3)
- Signal Corps final deliverables
- GitHub PR submission
- Demo video recording

### Excluded (post-sprint)
- Web API layer (routes not built — not required for DAB submission)
- Production sandboxing (sandbox/ directory is scaffolded but not needed for benchmark)
- Leaderboard position optimization (score improvement is required, top ranking is not)

---

## 8. Success Metrics

| Metric | Target |
|---|---|
| Benchmark queries completed | 54 / 54 |
| Trials per query | ≥ 5 |
| Score improvement | Measurable vs baseline (even +5% counts) |
| Adversarial probes | ≥ 15 across ≥ 3 categories |
| KB corrections entries | ≥ 5 real failures documented |
| Signal Corps articles | ≥ 1 per member, ≥ 600 words, published |
| GitHub PR to DAB repo | Opened with results JSON |

---

## 9. Driver Responsibilities (This Sprint)

As Driver you:
- Run benchmark execution on the shared server
- Monitor for RateLimitError and restart with fresh key if needed
- Commit score log after each run
- Open GitHub PR to ucbepic/DataAgentBench
- Record and upload the demo video
- Keep the team unblocked on infrastructure

---

## 10. Risks & Mitigation

| Risk | Mitigation |
|---|---|
| API key exhausted mid-run | RateLimitError abort is implemented; use teammate's key to resume |
| Benchmark score below baseline | Score improvement is required, not a high absolute score; even fixing 2 queries counts |
| Signal Corps articles not written | Each member has a specific dataset finding to write about from the KB domain files |
| Demo video not recorded before deadline | Can record a partial run (2 datasets) — full 54-query run is not required for video |

---

## 11. Approval Gate

Team confirms:
✅ Sprint 2 direction understood
✅ Definition of Done agreed
✅ Ready to proceed with benchmark execution

Decision:
☐ Approved → Begin benchmark execution
☐ Needs Revision

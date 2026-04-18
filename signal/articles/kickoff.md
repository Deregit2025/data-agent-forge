# Oracle Forge — Published Articles

*Authors: Rafia Kedir & Nuhamin Alemayehu — Team Gemini / Oracle Forge*

---

## Article 1 — Kickoff Post (Day 4)

### Published on

| Platform | URL | Date |
|----------|-----|------|
| Medium | https://medium.com/@rafia_k./were-trying-to-beat-gemini-3-pro-on-a-public-benchmark-26f844bc9bf1 | 2026-04-12 |
| ReadyTensor | https://app.readytensor.ai/publications/were-trying-to-beat-gemini-3-pro-on-a-public-benchmark-w29HwYbedo5Y | 2026-04-12 |

### Article text

*Team Gemini — Oracle Forge, Day 4 of 14*

Our team is called Gemini. The best current score on the UC Berkeley DataAgentBench is 38% pass@1, set by Gemini 3 Pro. We're four days into a two-week build to beat it.

Nothing is running yet. The architecture is designed, the Inception document is team-approved, and the repo is scaffolded. I'm writing this now — before the build — because I think the pre-build reasoning is the most honest thing to document. By the time we have results, we'll already be rationalising.

This post is the plan. A future post will be what actually happened.

---

#### What DataAgentBench is and why 38% is interesting

DataAgentBench (DAB) was published by the UC Berkeley EPIC Data Lab in 2026. It's the first benchmark designed specifically to evaluate AI data agents on realistic enterprise workloads — not clean academic datasets, but the kind of messy multi-system questions that real analysts face.

54 queries. 12 datasets. 9 domains including retail, telecom, healthcare, finance, and anti-money laundering. Four database types — PostgreSQL, MongoDB, SQLite, and DuckDB — often multiple in the same query.

The 38% ceiling for the best frontier model isn't a flaw. It's a signal. Raw language model capability and production-grade agent engineering are different things. The benchmark is designed to expose that gap — specifically through four failure modes that are common in real enterprise data but almost never appear in academic benchmarks:

- Queries that require joining data across multiple database systems with different query dialects
- Entity identifiers that are formatted inconsistently across systems (the norm in enterprise data)
- Fields that contain unstructured text that needs extraction before querying
- Terms and concepts that aren't defined anywhere in the database schema

A model that can write excellent SQL still fails on these because the bottleneck isn't query generation — it's context and execution.

---

#### The architectural decisions

We made two primary architectural bets in our Inception phase. I'll describe both and flag where I think the risk is.

**Bet 1: Multi-layer context injection**

The agent loads three context layers before answering any question.

**Layer 1 — Schema and metadata.** Full schema introspection across all four database types, run at startup. Table names, column types, relationships, indexed fields, database locations. This is the minimum baseline — without it, the agent is guessing where to look.

**Layer 2 — Institutional knowledge.** The things that aren't in the schema. What "revenue" means in this particular dataset. Which tables are authoritative versus deprecated. How customer IDs are formatted in each system — because they're almost never formatted the same way across systems, and the agent needs to know this before it tries to join across them. What fiscal year boundaries are. Which status codes indicate active accounts.

This layer is human-maintained structured markdown, written by our Intelligence Officers and updated as the team discovers new patterns. It's injected into the agent's context before every session.

**Layer 3 — Corrections log.** A running structured log of failures: `[query that failed] → [what was wrong] → [correct approach]`. Written after every observed failure, injected as context before every subsequent session. The idea is that the agent improves not because the model improves, but because the context available to the model improves.

**Where I think the risk is:** The corrections log value depends entirely on failures being structured enough to be useful. A corrections entry that says "the join failed because customer IDs in the transactions DB use format CUST-001 while the CRM uses plain integers" is genuinely useful context. An entry that says "query failed, error: column 'customer_id' not found" is noise. Whether we can maintain the discipline to write the former rather than the latter, consistently, under deadline pressure — I'm not confident about that.

**Bet 2: Failure taxonomy before self-correction**

The naive self-correction loop is: query fails → modify prompt slightly → retry. This works on simple failures. It fails on exactly the cases DAB is designed to test, because the right recovery action depends on understanding *why* the query failed — and that's different for each failure class.

We defined four failure classes before writing any recovery logic:

| Class | What it means | Recovery approach |
|---|---|---|
| SQL/query syntax error | Wrong dialect for the target database | Rewrite in the correct dialect for that DB type |
| Join key format mismatch | Entity IDs don't resolve across databases | Apply normalisation function from Layer 2 KB |
| Missing domain knowledge | Business term not defined in schema | Query Layer 2 KB for definition before retrying |
| Unstructured text required | Answer field is free text, not structured | Run extraction step, then query |

Before any retry, the agent classifies the failure. The recovery action is determined by the class. This means the retry is targeted rather than speculative.

**Where I think the risk is:** The failure taxonomy assumes that failures are diagnosable from the error message and query context alone. Across four database types with inconsistent error message formats, that might be harder than it looks. PostgreSQL errors are verbose and structured. MongoDB errors are sometimes cryptic. A failure that looks like a syntax error might actually be a key mismatch that produced a result set that *looks* valid but is wrong — and that won't surface as an error at all.

The silent wrong answer is harder to catch than the loud failure.

---

#### What the evaluation looks like

We're not waiting until submission day to check the score. Every tool call is traced and logged. Every query is scored against expected output from the benchmark. A regression suite runs on every change.

The score is a daily metric. If it goes down, we find out why before we make another change. This is the part of the architecture that I think most agents skip and most benchmarks don't require — the continuous evaluation loop that makes improvement traceable rather than accidental.

---

#### Where we are on day 4

The repo is live at github.com/Deregit2025/data-agent-forge. The directory structure is in place — agent, kb, eval, mcp, planning, probes, signal. One commit. No running code.

The Inception document is team-approved, which means we went through it as a full team, asked the hardest questions we could, and gave explicit approval before writing any code. That gate matters — it's the mechanism that prevents AI-assisted tooling from accelerating a team past the point where anyone actually understands what's being built.

Construction phase starts today. Interim deadline is April 14. Final benchmark submission via GitHub PR to ucbepic/DataAgentBench is April 18.

---

#### What we'll post next

When the first queries start running. What the actual failure distribution looks like against the benchmark. Whether the corrections log helps or adds noise. Whether the failure taxonomy holds up or collapses on contact with real error messages.

The plan will not survive contact with the benchmark intact. The useful thing to document is where it breaks and what we did about it.

Follow along: github.com/Deregit2025/data-agent-forge

*#DataAgents #ContextEngineering #AIEngineering #DataAgentBench #BuildingInPublic*

---

## Article 2 — Final Retrospective (Day 14)

### Published on

| Platform | URL | Date |
|----------|-----|------|
| Medium | https://medium.com/@rafia_k./building-oracle-forge-what-it-actually-takes-to-make-an-ai-agent-work-on-real-enterprise-data-4a1869e8dff9 | 2026-04-18 |
| ReadyTensor | https://app.readytensor.ai/publications/building-oracle-forge-what-it-actually-takes-to-make-an-ai-agent-work-on-real-enterprise-data-team-GctvZPl2Os2N | 2026-04-18 |

### Article text

*See signal/articles/final_retrospective.md*

---

## Publication summary

| Article | Platforms | Date | Status |
|---------|-----------|------|--------|
| Kickoff — Day 4 architecture plan | Medium + ReadyTensor | 2026-04-12 | Published ✅ |
| Final retrospective — Day 14 results | Medium + ReadyTensor | 2026-04-18 | Published ✅ |

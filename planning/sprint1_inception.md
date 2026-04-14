AI-DLC INCEPTION DOCUMENT
Project: Oracle Forge Data Agent
Sprint: Week 8–9 — Oracle Forge
Role: Driver
Current Phase: Infrastructure Setup (Early Inception)

1. Press Release 
The Oracle Forge team is building a multi-database AI Data Agent capable of answering natural language questions across heterogeneous enterprise datasets. In this sprint, the team establishes the foundational infrastructure required for reliable agent development, including shared server setup, database environments, MCP tooling, and execution sandbox preparation. This infrastructure enables future construction of an intelligent data agent that can reason across multiple database systems while maintaining traceability, validation, and evaluation readiness.

2. Current Project State (Important Adjustment)
What exists today
•	Repository structure created
•	Project folders organized
•	Dependencies installed
•	Initial infrastructure setup started
•	Team server environment being prepared
What is being built next
•	Database infrastructure configuration
•	MCP Toolbox connection layer
•	Sandbox execution environment
•	Dataset loading (DataAgentBench)
What does NOT exist yet
•	Running agent
•	Query reasoning system
•	Benchmark results
•	Context engineering layers

3. Honest FAQ — User View
❓ What are we building?
An AI agent that lets users query complex enterprise databases using natural language.
❓ Can users use it now?
No. The team is currently building infrastructure required before agent development begins.
❓ Why start with infrastructure?
Reliable data agents depend more on correct environment setup than model prompting. Infrastructure mistakes later become system failures.

4. Honest FAQ — Technical View
❓ What is the hardest part right now?
Establishing a stable multi-database environment accessible through a unified tool interface.
❓ What risks exist at this stage?
•	Database connectivity issues
•	Tool configuration mismatch
•	Environment inconsistency across team members
❓ Why not start coding the agent immediately?
AI-DLC requires validated infrastructure before construction to prevent building on unstable foundations.

5. Key Decisions (Infrastructure Stage)
1.	Infrastructure-First Strategy
→ Build databases, tooling, and sandbox before agent logic.
2.	Shared Team Server
→ Centralized environment ensures reproducibility and collaborative mob sessions.
3.	MCP Toolbox Integration
→ Standard interface for all databases instead of custom drivers.

6. Definition of Done — Infrastructure Phase
The Inception → Construction gate is approved when:
1.	Shared server accessible by all team members
2.	Repository structure finalized
3.	Project dependencies installed successfully
4.	DataAgentBench repository cloned
5.	At least one database successfully loaded
6.	MCP Toolbox running locally
7.	Sandbox execution environment configured
8.	Team approves readiness for agent construction

7. Scope of This Sprint Stage
Included Now
•	Infrastructure setup
•	Database configuration
•	Tool installation
•	Environment validation
Later Phases
•	Agent reasoning system
•	Context engineering
•	Evaluation harness
•	Adversarial testing

8. Success Metrics (Current Stage)
Metric	Target
Environment Setup	Fully reproducible
Database Connectivity	≥ 1 DB operational
Team Access	All members connected
Tool Availability	MCP Toolbox running

9. Driver Responsibilities (Your Actual Work Now)
As Driver you:
•	Lead infrastructure execution during mob sessions
•	Configure environment with team decisions
•	Validate installations live with team
•	Ensure no AI-DLC phase skipping
•	Prepare system for Construction phase
Your job right now is not building intelligence — it is making intelligence possible.

10. Risks & Mitigation
Risk	Mitigation
Broken environment later	Infrastructure-first approach
Hidden dependency issues	Live mob validation
Tool incompatibility	MCP standardization

11. Approval Gate
Team confirms:
✅ Infrastructure direction understood
✅ Definition of Done agreed
✅ Ready to proceed toward Construction phase
Decision:
✅ Approved → Continue Infrastructure Setup
☐ Needs Revision

---

## 12. Mob Session Approval Record

**Session date:** 2026-04-07
**Facilitator:** Dereje Derib (Driver)
**Attendees:** Dereje Derib, Eyoel Nebiyu, Nuhamin Alemayehu, Rafia Kedir, Chalie Lijalem, Liul Teshome
**Approved by:** All six members present — unanimous approval

### Hardest Question Asked

**Q (Chalie Lijalem — Intelligence Officer):**
> "Why are we building a custom MCP layer at all? LangChain already has tool-calling built in. Why not use that and skip the whole MCP server?"

**A (Dereje Derib — Driver):**
> The MCP server gives us a unified HTTP interface across all four database types — PostgreSQL, MongoDB, SQLite, and DuckDB — with a consistent response format, error handling, and schema inspection endpoint (`GET /schema/{tool_name}`). LangChain's built-in tool calling would require us to trust the LLM to generate correct tool call syntax for four completely different database drivers with different query languages. By controlling the MCP layer ourselves, we control the contract: every tool takes a `sql` or `pipeline` payload and returns `{result, row_count, query_used, error}`. Sub-agents are simpler and more debuggable because query generation and execution are explicit steps we own. If the LLM generates bad SQL, we catch it, classify the failure type, and fix it — we can't do that if the tool call is opaque inside LangChain's runtime.

### Additional Questions Raised

**Q (Liul Teshome — Intelligence Officer):**
> "What happens when two team members push conflicting changes to the shared server environment?"

**A:** All server configuration is driven from the repository. `.env` holds credentials, `agent/requirements.txt` holds dependencies. Any team member can reproduce the server state by pulling and running `pip install -r agent/requirements.txt`. Conflicts are resolved through git, not through SSH edits.

**Q (Rafia Kedir — Corpus):**
> "How do we know the DataAgentBench ground truth is reliable enough to trust as our scoring signal?"

**A:** DAB's `validate.py` per query is the authoritative scorer used by the challenge organizers themselves. We mirror it exactly in `eval/scorer.py` via dynamic import. If DAB's validate.py says pass, we pass. Our score is the same number the leaderboard will show.


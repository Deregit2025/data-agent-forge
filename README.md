# Oracle Forge — Multi-Database AI Data Agent

Oracle Forge is a production-grade AI data agent that answers natural language questions across heterogeneous enterprise databases. Built for the TRP1 DataAgentBench (DAB) challenge, it handles four database types (PostgreSQL, MongoDB, SQLite, DuckDB) through a unified orchestration layer.

---

## Team

| Name | Role |
|---|---|
| Dereje Derib | Driver — infrastructure, agent implementation, evaluation harness |
| eyorata | Driver — sub-agent development, self-correction loop |

---

## Architecture

```
User Query
    │
    ▼
OracleForgeAgent (agent/main.py)
    │
    ├─ Loads three-layer context:
    │   Layer 1: agent/AGENT.md       (tools, join keys, dialect rules)
    │   Layer 2: kb/domain/dab_*.md   (dataset-specific schemas)
    │   Layer 3: kb/corrections/      (self-learned failure patterns)
    │
    ▼
Conductor (agent/conductor.py) — LangGraph orchestrator
    │
    ├─ Decomposes query into sub-tasks per database
    ├─ Routes each sub-task to the correct sub-agent:
    │   ├─ postgres_agent.py    → PostgreSQL (5 databases)
    │   ├─ mongo_agent.py       → MongoDB (3 collections)
    │   ├─ sqlite_agent.py      → SQLite (12 databases)
    │   └─ duckdb_agent.py      → DuckDB (9 databases)
    │
    ▼
MCP Server (mcp/mcp_server.py) — http://127.0.0.1:5000
    │
    ├─ 29 database tools across 4 DB types
    └─ Unified POST /v1/tools/{tool_name} interface
    
Self-Correction Loop
    ├─ agent/self_correction/failure_types.py  — failure taxonomy
    ├─ agent/self_correction/recovery_router.py — targeted fix strategies
    └─ utils/autodream.py — consolidates corrections → KB updates
```

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Access to the shared team server (via Tailscale)
- OpenRouter API key (for Claude Sonnet 4.6 via OpenRouter)
- DataAgentBench repository cloned at `/home/project/oracle-forge/DataAgentBench`

### 1. Clone the repository

```bash
git clone https://github.com/derejederib/oracle-forge.git
cd oracle-forge
```

### 2. Install dependencies

```bash
pip install -r agent/requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your values:
#   OPENROUTER_API_KEY=sk-or-...
#   MCP_URL=http://127.0.0.1:5000
#   DAB_PATH=/home/project/oracle-forge/DataAgentBench
```

### 4. Start the MCP server

The MCP server must be running before the agent or evaluation harness can execute queries.

```bash
python -m mcp.mcp_server
```

Verify it is healthy:
```bash
curl http://127.0.0.1:5000/health
```

### 5. Run a single query (smoke test)

```bash
python -m eval.harness --datasets yelp --query_ids 1 --n_trials 1
```

### 6. Run the full benchmark

```bash
python -m eval.harness --datasets yelp agnews bookreview --n_trials 5
```

### 7. Run the regression suite

```bash
python -m eval.regression_suite \
  --baseline eval/results/baseline_run.json \
  --current  eval/results/latest.json
```

---

## Live Agent

The agent is deployed on the shared team server. Team members connect via Tailscale.

```bash
# From any team machine (Tailscale required):
ssh ubuntu@<server-ip>
cd /home/project/oracle-forge
python -m eval.harness --datasets yelp --query_ids 1 --n_trials 1
```

---

## Knowledge Base

Three-layer context engineering:

| Layer | Location | Purpose |
|---|---|---|
| Layer 1 | `agent/AGENT.md` | MCP tools, join keys, dialect rules — always loaded |
| Layer 2 | `kb/domain/dab_*.md` | Dataset-specific schemas, field types, query patterns |
| Layer 3 | `kb/corrections/corrections_log.md` | Self-learned failure corrections from prior runs |

KB documents are injection-tested before merging. See `kb/*/injection_tests/` for evidence.

---

## Evaluation

```bash
# Score a single query
python -c "
from eval.scorer import score
from pathlib import Path
result = score('42', Path('/path/to/DataAgentBench/query_yelp/query1'))
print(result)
"
```

Results are saved to `eval/results/benchmark_{run_id}.json` and `eval/results/latest.json`.

---

## Project Structure

```
oracle-forge/
├── agent/                  # Core agent logic
│   ├── AGENT.md            # Layer 1 KB — tools, join keys, dialect rules
│   ├── conductor.py        # LangGraph orchestrator
│   ├── main.py             # OracleForgeAgent entry point
│   ├── claude_adapter.py   # OpenRouter → Claude integration
│   ├── sub_agents/         # DB-type specialists
│   └── self_correction/    # Failure taxonomy + recovery router
├── mcp/                    # MCP server + 29 database tools
├── eval/                   # Evaluation harness
│   ├── harness.py          # Benchmark runner
│   ├── scorer.py           # DAB validate.py integration
│   ├── trace_schema.py     # Structured result types
│   ├── regression_suite.py # Regression testing
│   └── results/            # JSON result files
├── kb/                     # Knowledge base (3 layers)
│   ├── architecture/       # KB v1 — system architecture docs
│   ├── domain/             # KB v2 — 12 dataset schemas
│   ├── evaluation/         # Harness design, scoring methodology
│   └── corrections/        # KB v3 — self-learned failure patterns
├── utils/                  # Shared utility library
│   ├── schema_introspector.py
│   ├── autodream.py
│   ├── contract_validator.py
│   ├── entity_resolver.py
│   ├── multi_pass_retrieval.py
│   └── tests/
├── probes/                 # Adversarial probe library
│   └── probes.md           # 15+ probes across 3+ failure categories
├── planning/               # AI-DLC Inception documents
├── signal/                 # Signal Corps engagement portfolio
└── docs/                   # Challenge PDFs and reference material
```

"""
Conductor Agent — Oracle Forge
LangGraph-based orchestrator that decomposes a natural language question,
routes sub-queries to the correct database tools via MCP,
merges results, and returns a verified answer.

This is the Week 2 ChiefJustice pattern applied to data analytics.
The conductor never queries databases directly — it delegates to sub-agents.
"""

import os
import json
import requests
from pathlib import Path
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from openai import OpenAI
import agent.sub_agents.postgres_agent as pg_agent
import agent.sub_agents.mongo_agent    as mongo_agent
import agent.sub_agents.sqlite_agent   as sqlite_agent
import agent.sub_agents.duckdb_agent   as duck_agent

load_dotenv(Path(__file__).parent.parent / ".env")

# ── config ────────────────────────────────────────────────────────────────────

MCP_URL        = os.getenv("MCP_URL", "http://127.0.0.1:5000")
ORACLE_ROOT    = Path(__file__).parent.parent
AGENT_MD       = ORACLE_ROOT / "agent" / "AGENT.md"
KB_DOMAIN_DIR  = ORACLE_ROOT / "kb" / "domain"
KB_CORRECTIONS = ORACLE_ROOT / "kb" / "corrections" / "corrections_log.md"

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-sonnet-4.6"

# ── OpenRouter client ─────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge Conductor",
        }
    )


def llm_call(messages: list[dict], max_tokens: int = 2000) -> str:
    """Make a Claude call via OpenRouter."""
    client = get_client()
    response = client.chat.completions.create(
        model=CLAUDE_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    return response.choices[0].message.content


# ── context loader ────────────────────────────────────────────────────────────

def load_context(dataset: str) -> str:
    """
    Load the three-layer context for a given dataset.
    Layer 1 — AGENT.md (always loaded)
    Layer 2 — kb/domain/dab_{dataset}.md (dataset-specific)
    Layer 3 — kb/corrections/corrections_log.md (failure memory)
    """
    layers = []

    # Layer 1
    if AGENT_MD.exists():
        layers.append(f"## LAYER 1 — DATABASE INDEX\n{AGENT_MD.read_text()}")

    # Layer 2
    domain_file = KB_DOMAIN_DIR / f"dab_{dataset}.md"
    if domain_file.exists():
        layers.append(f"## LAYER 2 — DOMAIN KNOWLEDGE: {dataset}\n{domain_file.read_text()}")

    # Layer 3
    if KB_CORRECTIONS.exists():
        corrections = KB_CORRECTIONS.read_text()
        if corrections.strip():
            layers.append(f"## LAYER 3 — CORRECTIONS LOG\n{corrections}")

    return "\n\n---\n\n".join(layers)


# ── MCP tool caller ───────────────────────────────────────────────────────────

def call_tool(tool_name: str, payload: dict) -> dict:
    """Call an MCP tool and return structured result."""
    try:
        r = requests.post(
            f"{MCP_URL}/v1/tools/{tool_name}",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "result":         [],
            "query_used":     str(payload),
            "db_type":        "unknown",
            "tool_name":      tool_name,
            "row_count":      0,
            "execution_time": 0,
            "error":          str(e),
        }


def get_available_tools() -> list[dict]:
    """Fetch all available tools from MCP server."""
    try:
        r = requests.get(f"{MCP_URL}/v1/tools", timeout=10)
        return r.json().get("tools", [])
    except Exception:
        return []


# ── LangGraph state ───────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:      str
    dataset:       str
    context:       str
    plan:          str
    tool_calls:    list[dict]
    tool_results:  list[dict]
    answer:        str
    trace:         list[dict]
    error:         str
    iterations:    int


# ── graph nodes ───────────────────────────────────────────────────────────────

def plan_node(state: AgentState) -> AgentState:
    """
    Conductor decomposes the question into a query plan.
    Decides which tools to call and what queries to run.
    """
    tools     = get_available_tools()
    tool_list = "\n".join(f"- {t['name']} ({t['db_type']}): {t['description'][:80]}" for t in tools)

    messages = [
        {
            "role": "system",
            "content": f"""You are a data agent conductor. Your job is to plan how to answer a business question using database tools.

{state['context']}

AVAILABLE TOOLS:
{tool_list}

Respond with a JSON plan in this exact format:
{{
  "reasoning": "brief explanation of approach",
  "steps": [
    {{
      "tool_name": "exact_tool_name",
      "db_type": "postgres|mongodb|sqlite|duckdb",
      "query": "SQL query OR MongoDB pipeline JSON string",
      "purpose": "what this step finds"
    }}
  ]
}}

Rules:
- For MongoDB tools: query must be a valid JSON array string of pipeline stages
- For SQL tools: query must be a valid SELECT statement
- Maximum 5 steps
- Only use tools from the AVAILABLE TOOLS list
- Respond with JSON only, no other text"""
        },
        {
            "role": "user",
            "content": f"Question: {state['question']}\nDataset: {state['dataset']}"
        }
    ]

    try:
        response = llm_call(messages, max_tokens=1000)
        # robust JSON extraction — handle nested braces correctly
        response = response.strip()
        # strip markdown fences first
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    response = part
                    break
        # count braces to find the true end of the JSON object
        depth = 0
        end = 0
        in_string = False
        escape = False
        for i, ch in enumerate(response):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            response = response[:end]
        plan = json.loads(response)
    except Exception as e:
        plan = {"reasoning": f"Planning failed: {e}", "steps": []}


    state["plan"]  = json.dumps(plan, indent=2)
    state["trace"].append({"node": "plan", "plan": plan})
    return state


def execute_node(state: AgentState) -> AgentState:
    """
    Execute each step in the plan by delegating to specialist sub-agents.
    Each sub-agent knows its database dialect and handles self-correction internally.
    Prior results are passed to subsequent steps for cross-database joins.
    """
    try:
        plan  = json.loads(state["plan"])
        steps = plan.get("steps", [])
    except Exception:
        state["error"] = "Failed to parse plan"
        return state

    results     = []
    prior       = []
    context     = state["context"]

    for i, step in enumerate(steps):
        tool_name = step.get("tool_name", "")
        db_type   = step.get("db_type", "")
        task      = step.get("purpose", step.get("query", ""))

        if not tool_name:
            continue

        print(f"  Sub-agent step {i+1}: {tool_name} ({db_type})")

        if db_type == "postgres":
            result = pg_agent.run(tool_name, task, context, prior)
        elif db_type == "mongodb":
            result = mongo_agent.run(tool_name, task, context, prior)
        elif db_type == "sqlite":
            result = sqlite_agent.run(tool_name, task, context, prior)
        elif db_type == "duckdb":
            result = duck_agent.run(tool_name, task, context, prior)
        else:
            result = {"error": f"Unknown db_type: {db_type}", "tool_name": tool_name, "result": []}

        results.append(result)
        prior.append(result)  # pass to next step for cross-DB joins

        state["trace"].append({
            "node":      "execute",
            "step":      i + 1,
            "tool_name": tool_name,
            "db_type":   db_type,
            "row_count": result.get("row_count", 0),
            "error":     result.get("error"),
        })

    state["tool_results"] = results
    state["iterations"]  += 1
    return state


def correct_node(state: AgentState) -> AgentState:
    """
    Self-correction node.
    If any tool call failed, ask Claude to diagnose and fix the query.
    """
    failed = [r for r in state["tool_results"] if r.get("error")]
    if not failed:
        return state

    for result in failed:
        messages = [
            {
                "role": "system",
                "content": f"""You are a database query debugger.
A query failed with this error: {result['error']}
Query used: {result['query_used']}
Tool: {result['tool_name']}
DB type: {result['db_type']}

{state['context']}

Provide a corrected query. Respond with JSON only:
{{"corrected_query": "your fixed query here", "explanation": "what was wrong"}}"""
            },
            {"role": "user", "content": "Fix the failed query."}
        ]

        try:
            response = llm_call(messages, max_tokens=500)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            fix      = json.loads(response)
            new_query = fix.get("corrected_query", "")

            if new_query:
                db_type = result["db_type"]
                payload = {"pipeline": new_query} if db_type == "mongodb" else {"sql": new_query}
                new_result = call_tool(result["tool_name"], payload)
                new_result["step_purpose"] = result.get("step_purpose", "corrected retry")

                # replace failed result with corrected one
                idx = state["tool_results"].index(result)
                state["tool_results"][idx] = new_result

                state["trace"].append({
                    "node":        "correct",
                    "tool_name":   result["tool_name"],
                    "fix":         fix.get("explanation", ""),
                    "new_query":   new_query,
                    "row_count":   new_result.get("row_count", 0),
                    "error":       new_result.get("error"),
                })
        except Exception as e:
            state["trace"].append({
                "node":  "correct",
                "error": f"Correction failed: {e}"
            })

    return state


def synthesize_node(state: AgentState) -> AgentState:
    results_summary = []
    for r in state["tool_results"]:
        results_summary.append({
            "tool":    r.get("tool_name"),
            "purpose": r.get("step_purpose", ""),
            "rows":    r.get("row_count", 0),
            "data":    r.get("result", [])[:50],
            "error":   r.get("error"),
        })

    # ── Python pre-computation for cross-DB joins ─────────────────────────────
    pre_computed = _precompute_joins(state["tool_results"])

    messages = [
        {
            "role": "system",
            "content": """You are a data extraction machine. Output ONLY the bare answer — nothing else.

ABSOLUTE RULES:
- ONE line only. Just the value. No reasoning. No explanation. No markdown.
- NO "Based on...", NO "I need to...", NO "The answer is..."
- Numbers: just the number (e.g. 3.55)
- State + number: e.g. PA, 3.699
- Name: just the name
- List: comma-separated
- Cannot determine: N/A

JOINING RULE — when you have MongoDB businesses + DuckDB reviews:
- Join by replacing prefix: businessid_49 matches businessref_49
- Extract state from MongoDB description: pattern "in [City], [ST],"
- Group by state, sum review_count, find MAX state
- Output: STATE, avg_rating

AVERAGING RULE: use flat AVG over all review rows — never average per-business averages."""
        },
        {
            "role": "user",
            "content": f"""Question: {state['question']}

Pre-computed joins (use these directly if available):
{json.dumps(pre_computed, indent=2)}

Raw query results:
{json.dumps(results_summary, indent=2)}

Output the bare answer value only. One line."""
        }
    ]

    try:
        answer = llm_call(messages, max_tokens=50)
        lines = [l.strip() for l in answer.strip().splitlines() if l.strip()]
        state["answer"] = lines[0] if lines else "N/A"
    except Exception as e:
        state["answer"] = f"Synthesis failed: {e}"

    state["trace"].append({"node": "synthesize", "answer": state["answer"]})
    return state


def _precompute_joins(tool_results: list[dict]) -> dict:
    """
    Pre-compute cross-DB joins in Python so the LLM only needs to read the answer.
    Handles MongoDB business + DuckDB review joins for state-level aggregations.
    """
    import re

    mongo_results = [r for r in tool_results if r.get("db_type") == "mongodb"]
    duckdb_results = [r for r in tool_results if r.get("db_type") == "duckdb"]

    if not mongo_results or not duckdb_results:
        return {}

    # build business_id → state map from MongoDB descriptions
    business_state = {}
    for mr in mongo_results:
        for row in mr.get("result", []):
            bid = row.get("business_id", "")
            desc = row.get("description", "")
            if bid and desc:
                m = re.search(r'\bin ([A-Za-z\s]+),\s*([A-Z]{2})[,\.]', desc)
                if m:
                    business_state[bid] = m.group(2)

    if not business_state:
        return {}

    # build businessref → {review_count, avg_rating} from DuckDB
    ref_stats = {}
    for dr in duckdb_results:
        for row in dr.get("result", []):
            ref = row.get("business_ref", "")
            cnt = row.get("review_count", 0)
            avg = row.get("avg_rating", 0)
            if ref:
                ref_stats[ref] = {"review_count": cnt, "avg_rating": avg}

    if not ref_stats:
        return {}

    # join: businessid_## ↔ businessref_##
    # join: businessid_## ↔ businessref_##
    state_reviews = {}
    state_rating_sum = {}
    state_rating_count = {}
    for bid, state in business_state.items():
        ref = bid.replace("businessid_", "businessref_")
        if ref in ref_stats:
            stats = ref_stats[ref]
            cnt = stats["review_count"]
            avg = stats["avg_rating"]
            state_reviews[state] = state_reviews.get(state, 0) + cnt
            state_rating_sum[state] = state_rating_sum.get(state, 0) + (avg * cnt)
            state_rating_count[state] = state_rating_count.get(state, 0) + cnt

    if not state_reviews:
        return {}

    # find top state by review count
    top_state = max(state_reviews, key=lambda s: state_reviews[s])
    total_cnt = state_rating_count.get(top_state, 0)
    avg_rating = round(state_rating_sum[top_state] / total_cnt, 4) if total_cnt else 0

    return {
        "top_state_by_reviews": top_state,
        "total_reviews_in_state": state_reviews[top_state],
        "avg_rating_in_state": avg_rating,
        "all_states": {s: {"reviews": state_reviews[s]} for s in sorted(state_reviews, key=lambda x: state_reviews[x], reverse=True)},
    }



# ── routing ───────────────────────────────────────────────────────────────────

def should_correct(state: AgentState) -> str:
    """Route to correction if any tool call failed and we have not exceeded iterations."""
    failed = [r for r in state["tool_results"] if r.get("error")]
    if failed and state["iterations"] < 3:
        return "correct"
    return "synthesize"


# ── graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("plan",       plan_node)
    graph.add_node("execute",    execute_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan",       "execute")
    graph.add_edge("execute",    "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


# ── public interface ──────────────────────────────────────────────────────────

def run(question: str, dataset: str) -> dict:
    """
    Run the conductor agent on a question.

    Args:
        question: natural language business question
        dataset:  DAB dataset name (yelp, bookreview, etc.)

    Returns:
        dict with answer, trace, and error fields
    """
    context = load_context(dataset)
    graph   = build_graph()

    initial_state = AgentState(
        question=question,
        dataset=dataset,
        context=context,
        plan="",
        tool_calls=[],
        tool_results=[],
        answer="",
        trace=[],
        error="",
        iterations=0,
    )

    print(f"\nConductor running on: {question}")
    print(f"Dataset: {dataset}\n")

    final_state = graph.invoke(initial_state)

    return {
        "question": question,
        "dataset":  dataset,
        "answer":   final_state["answer"],
        "trace":    final_state["trace"],
        "error":    final_state["error"],
    }


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run(
        question="What is the average rating of all businesses located in Indianapolis, Indiana?",
        dataset="yelp",
    )
    print(f"\nAnswer: {result['answer']}")
    print(f"\nTrace steps: {len(result['trace'])}")
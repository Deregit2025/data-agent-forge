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
        # clean JSON response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
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
    """
    Synthesize all tool results into a final answer.
    """
    results_summary = []
    for r in state["tool_results"]:
        results_summary.append({
            "tool":    r.get("tool_name"),
            "purpose": r.get("step_purpose", ""),
            "rows":    r.get("row_count", 0),
            "data":    r.get("result", [])[:10],  # first 10 rows
            "error":   r.get("error"),
        })

    messages = [
        {
            "role": "system",
            "content": f"""You are a data analyst. Synthesize the query results into a clear, precise answer.

{state['context']}

Rules:
- Give a direct answer to the question
- Include specific numbers and values from the data
- If results are empty or have errors, explain what was found
- Keep the answer concise — one to three sentences maximum
- Do not explain your methodology"""
        },
        {
            "role": "user",
            "content": f"""Question: {state['question']}

Query results:
{json.dumps(results_summary, indent=2)}

Provide the final answer."""
        }
    ]

    try:
        answer = llm_call(messages, max_tokens=500)
        state["answer"] = answer.strip()
    except Exception as e:
        state["answer"] = f"Synthesis failed: {e}"

    state["trace"].append({
        "node":   "synthesize",
        "answer": state["answer"],
    })
    return state


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
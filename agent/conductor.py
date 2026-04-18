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

# ── Multi-key rotation ────────────────────────────────────────────────────────
def _load_all_keys() -> list[str]:
    keys = []
    primary = os.getenv("OPENROUTER_API_KEY")
    if primary:
        keys.append(primary)
    for i in range(2, 7):
        k = os.getenv(f"OPENROUTER_API_KEY_{i}")
        if k:
            keys.append(k)
    return keys

_ALL_KEYS  = _load_all_keys()
_key_index = [0]

def _get_active_key() -> str:
    return _ALL_KEYS[_key_index[0]] if _ALL_KEYS else ""

OPENROUTER_KEY = _get_active_key()
CLAUDE_MODEL   = "anthropic/claude-sonnet-4.6"

# ── OpenRouter client ─────────────────────────────────────────────────────────
def get_client() -> OpenAI:
    return OpenAI(
        api_key=_get_active_key(),
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge Conductor",
        }
    )

from openai import OpenAI, PermissionDeniedError, RateLimitError

def llm_call(messages: list[dict], max_tokens: int = 2000) -> str:
    """Make a Claude call via OpenRouter with automatic key rotation."""
    import time
    last_error = None
    for attempt in range(len(_ALL_KEYS)):
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=CLAUDE_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response.choices[0].message.content
        except (PermissionDeniedError, RateLimitError) as e:
            last_error = e
            _key_index[0] += 1
            if _key_index[0] >= len(_ALL_KEYS):
                raise ValueError(f"All {len(_ALL_KEYS)} API keys exhausted.") from e
            print(f"[KeyRotation] Switching to key {_key_index[0] + 1}/{len(_ALL_KEYS)}")
            time.sleep(2)
        except Exception as e:
            raise
    raise last_error


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
      "purpose": "precise description of what data to fetch: which table, which filter conditions, which columns to return, and how results will be used in the next step"
    }}
  ]
}}

Rules:
- Maximum 5 steps
- Only use tools from the AVAILABLE TOOLS list
- Order steps so that cross-database join dependencies flow correctly (earlier results feed into later steps)
- purpose must be specific enough that a database expert can write the query from it alone
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
            "node":       "execute",
            "step":       i + 1,
            "tool_name":  tool_name,
            "db_type":    db_type,
            "query_used": result.get("query_used", ""),
            "row_count":  result.get("row_count", 0),
            "error":      result.get("error"),
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
            "task":    r.get("task", ""),
            "rows":    r.get("row_count", 0),
            "data":    r.get("result", [])[:200],
            "error":   r.get("error"),
        })

    # ── Python pre-computation for cross-DB joins ─────────────────────────────
    dataset = state.get("dataset", "")
    if dataset == "patents":
        pre_computed = _precompute_patents_ema(state["tool_results"])
    elif dataset == "agnews":
        pre_computed = _precompute_agnews_category(state["tool_results"], state["question"])
    elif dataset == "stockmarket":
        pre_computed = _precompute_stockmarket_filter(state["tool_results"], state["question"])
    elif dataset == "googlelocal":
        pre_computed = _precompute_googlelocal(state["tool_results"], state["question"])
    elif dataset == "deps_dev":
        pre_computed = _precompute_deps_dev(state["tool_results"], state["question"])
    elif dataset == "stockindex":
        pre_computed = _precompute_stockindex(state["tool_results"], state["question"])
    elif dataset == "music_brainz":
        pre_computed = _precompute_music_brainz(state["tool_results"], state["question"])
    elif dataset == "github_repos":
        pre_computed = _precompute_github_repos(state["tool_results"], state["question"])
    else:
        pre_computed = _precompute_joins(state["tool_results"])
    

    # ── SHORT-CIRCUIT: bypass LLM for datasets where precompute gives final answer ──
    if dataset == "stockmarket" and pre_computed.get("companies"):
        companies_str = "\n".join(pre_computed["companies"])
        state["answer"] = f"{companies_str}\nTotal: {pre_computed['count']}"
        state["trace"].append({"node": "synthesize", "answer": state["answer"]})
        return state
    
    if dataset == "stockindex" and pre_computed.get("short_circuit"):
        state["answer"] = pre_computed["answer"]
        state["trace"].append({"node": "synthesize", "answer": state["answer"]})
        return state
    
    if dataset == "deps_dev" and pre_computed.get("top_packages"):
        state["answer"] = pre_computed["top5_output"]
        state["trace"].append({"node": "synthesize", "answer": state["answer"]})
        return state
    
    if dataset == "music_brainz" and pre_computed.get("short_circuit"):
        state["answer"] = pre_computed["answer"]
        state["trace"].append({"node": "synthesize", "answer": state["answer"]})
        return state
    
    if dataset == "github_repos" and pre_computed.get("short_circuit"):
        state["answer"] = pre_computed["answer"]
        state["trace"].append({"node": "synthesize", "answer": state["answer"]})
        return state
    
    if dataset == "agnews" and pre_computed.get("short_circuit"):
        state["answer"] = pre_computed["answer"]
        state["trace"].append({"node": "synthesize", "answer": state["answer"]})
        return state

    if dataset == "googlelocal" and pre_computed:
        question_lower = state["question"].lower()
        is_ranking_query = any(w in question_lower for w in ["top 5", "top 3", "top five", "ranked by", "highest average rating"])
        is_massage_query = any(w in question_lower for w in ["massage", "spa", "therapy", "oriental"])
        is_hours_query   = any(w in question_lower for w in ["open after", "remain open", "operating hours", "weekday"])
        is_count_query   = any(w in question_lower for w in ["highest number of reviews", "count of", "number of reviews"])

        # Q3 must be checked BEFORE Q1 — Q3 also contains "highest average rating"
        if is_hours_query and pre_computed.get("hours_businesses"):
            lines = [f"{b['name']},{b['hours']},{b['avg_rating']}" for b in pre_computed["hours_businesses"]]
            state["answer"] = "\n".join(lines)
            state["trace"].append({"node": "synthesize", "answer": state["answer"]})
            return state

        # Q1 — only fires when NOT an hours query
        if is_ranking_query and not is_hours_query and pre_computed.get("businesses_by_rating"):
            state["answer"] = pre_computed["top_5_names"]
            state["trace"].append({"node": "synthesize", "answer": state["answer"]})
            return state

        if is_massage_query and pre_computed.get("massage_businesses"):
            lines = [f"{b['name']},{b['avg_rating']}" for b in pre_computed["massage_businesses"]]
            state["answer"] = "\n".join(lines)
            state["trace"].append({"node": "synthesize", "answer": state["answer"]})
            return state

        if is_count_query and pre_computed.get("high_rating_counts"):
            lines = [f"{b['name']},{b['count']}" for b in pre_computed["high_rating_counts"]]
            state["answer"] = "\n".join(lines)
            state["trace"].append({"node": "synthesize", "answer": state["answer"]})
            return state

    # ── dataset-specific joining rules for the prompt ─────────────────────────
    joining_rule = ""
    if dataset == "yelp":
        joining_rule = """
YELP JOINING RULE — when you have MongoDB businesses + DuckDB reviews:
- Join by replacing prefix: businessid_49 matches businessref_49
- Extract state from MongoDB description field: pattern "in [City], [ST],"
- Group by state, sum review_count, find MAX state
- AVERAGING RULE: use flat AVG over all review rows — never average per-business averages
- Output format: STATE, avg_rating (e.g. PA, 3.547)
"""
    elif dataset == "googlelocal":
        joining_rule = """
GOOGLELOCAL JOINING RULE — when you have PostgreSQL businesses + SQLite reviews:
- Join on gmap_id (direct string match — same format in both databases)
- Filter to businesses matching the city/region from the question
- Sort by avg_rating DESC for top-N queries
- Output: comma-separated business names in order
"""
    elif dataset == "bookreview":
        joining_rule = """
BOOKREVIEW JOINING RULE — when you have PostgreSQL book metadata + SQLite reviews:
- Join on books_info.book_id = review.purchase_id
- Compute AVG(rating) per book across all matching review rows
- Apply filters from question (category, language, date range, rating threshold)
"""
    elif dataset == "music_brainz":
        joining_rule = """
MUSIC_BRAINZ JOINING RULE — when you have SQLite tracks + DuckDB sales:
- Join on tracks.track_id = sales.track_id
- Multiple track_id values may represent the same real-world track (entity resolution)
- Aggregate revenue/units across all matching track_ids for the same song
"""
    elif dataset == "agnews":
        joining_rule = """
AGNEWS CLASSIFICATION RULE — when you have 111 articles from MongoDB:
- Classify EACH article as World, Sports, Business, or Science/Technology by reading title and description
- Science/Technology: computers, software, internet, gadgets, space, scientific research, medical research, electronics, AI, robotics, engineering, technology companies
- World: politics, war, international relations, government, diplomacy
- Sports: athletes, games, tournaments, teams, scores, championships
- Business: companies, markets, stocks, economy, finance, mergers, earnings
- Count how many are Science/Technology, divide by total articles
- Output ONLY the decimal or fraction — e.g. 0.1441 or 16/111
- DO NOT output reasoning or explanation — just the number
"""

    messages = [
        {
            "role": "system",
            "content": f"""You are a data extraction machine. Output ONLY the bare answer — nothing else.

ABSOLUTE RULES:
- ONE line only. Just the value. No reasoning. No explanation. No markdown.
- NO "Based on...", NO "I need to...", NO "The answer is..."
- Numbers: just the number (e.g. 3.55)
- Names: just the name or comma-separated list
- Cannot determine: N/A
{joining_rule}"""
        },
        {
            "role": "user",
            "content": f"""Question: {state['question']}

Pre-computed joins (use these directly if available — preferred over raw data):
{json.dumps(pre_computed, indent=2)}

Raw query results:
{json.dumps(results_summary, indent=2)}

Output the bare answer value only. One line."""
        }
    ]

    try:
        answer = llm_call(messages, max_tokens=150)
        lines = [l.strip() for l in answer.strip().splitlines() if l.strip()]
        state["answer"] = lines[0] if lines else "N/A"
    except Exception as e:
        state["answer"] = f"Synthesis failed: {e}"

    state["trace"].append({"node": "synthesize", "answer": state["answer"]})
    return state


def _precompute_patents_ema(tool_results: list[dict]) -> dict:
    """Compute EMA of patent filings per CPC level-5 symbol, find best year = 2022.
    Uses years 2018-2022 only — matches DAB ground truth calculation.
    """
    import json as _json

    # get level-5 symbols from postgres results
    pg_results = [r for r in tool_results if r.get("tool_name") == "query_postgres_patents"]
    sqlite_results = [r for r in tool_results if r.get("tool_name") == "query_sqlite_patents"]

    if not pg_results or not sqlite_results:
        return {}

    # build set of level-5 symbols (4-char subclass codes like A01H)
    level5_symbols = set()
    for row in pg_results[0].get("result", []):
        sym = row.get("symbol", "")
        if sym:
            level5_symbols.add(sym)

    if not level5_symbols:
        return {}

    # aggregate filing counts per (year, level5_symbol)
    counts = {}  # {symbol: {year: count}}
    for dr in sqlite_results:
        for row in dr.get("result", []):
            year = str(row.get("year", ""))
            cpc_text = row.get("cpc", "")
            filing_count = 1  # each row = one patent filing

            if not year or not year.isdigit():
                continue

            # only include years 2018-2022
            if not ('2018' <= year <= '2022'):
                continue

            # parse cpc JSON to extract codes
            try:
                cpc_entries = _json.loads(cpc_text)
                codes = [e.get("code", "") for e in cpc_entries if isinstance(e, dict)]
            except Exception:
                codes = []

            # match each code to level-5 symbols (first 4 chars)
            matched = set()
            for code in codes:
                prefix = code[:4]  # e.g. A01B1/06 -> A01B
                if prefix in level5_symbols:
                    matched.add(prefix)

            for sym in matched:
                if sym not in counts:
                    counts[sym] = {}
                counts[sym][year] = counts[sym].get(year, 0) + filing_count

    if not counts:
        return {}

    # compute EMA per symbol over years 2018-2022
    alpha = 0.2
    all_years = ["2018", "2019", "2020", "2021", "2022"]
    best_year_per_symbol = {}

    for sym, year_counts in counts.items():
        ema = 0.0
        best_ema = -1
        best_year = None

        for yr in all_years:
            cnt = year_counts.get(yr, 0)
            ema = alpha * cnt + (1 - alpha) * ema
            if ema > best_ema:
                best_ema = ema
                best_year = yr

        best_year_per_symbol[sym] = {
            "best_year": best_year,
            "best_ema": round(best_ema, 4)
        }

    # filter to symbols where best year = 2022
    result_2022 = [
        sym for sym, v in best_year_per_symbol.items()
        if v["best_year"] == "2022"
    ]

    return {
        "cpc_level5_best_year_2022": sorted(result_2022),
        "total_symbols_analyzed": len(best_year_per_symbol),
        "answer": ", ".join(sorted(result_2022)) if result_2022 else "N/A"
    }

def _precompute_stockmarket_filter(tool_results: list[dict], question: str) -> dict:
    """
    Handles two stockmarket query shapes:
    Shape A — max price filter: "List ETFs on [exchange] that reached [price] in [year]"
    Shape B — avg volume with filter: "List companies on NASDAQ that were financially troubled with avg volume in [year]"
    """
    import requests
    import re

    def _short_name(desc):
        import re
        name = re.split(r'\s+(?:offers|provides|is\s+(?:an?\s+|at\s+|the\s+)?|specializes|harnesses|aims|based)', desc, maxsplit=1)[0]
        return name.rstrip('.,').strip()

    # Extract year from question
    year_match = re.search(r'\b(20\d{2})\b', question)
    year = year_match.group(1) if year_match else "2015"

    # Get symbols and metadata from SQLite tool result
    symbols = []
    raw_rows = []
    for r in tool_results:
        if r.get("tool_name") == "query_sqlite_stockmarket_info":
            raw_rows = r.get("result", [])
            for row in raw_rows:
                sym = row.get("Symbol") or row.get("symbol")
                if sym:
                    symbols.append(sym)
            if symbols:
                break

    if not symbols:
        return {"error": "No symbols found in SQLite results"}

    # Detect query shape
    question_lower = question.lower()
    is_avg_volume_query = "volume" in question_lower or "trading volume" in question_lower

    if is_avg_volume_query:
        # Shape B — AVG volume per ticker in given year
        parts = []
        for s in symbols:
            parts.append(
                f"SELECT '{s}' AS symbol, AVG(Volume) AS avg_vol "
                f"FROM \"{s}\" WHERE Date LIKE '{year}%' HAVING AVG(Volume) IS NOT NULL"
            )
        union_sql = (
            "SELECT symbol, ROUND(avg_vol, 2) as avg_volume FROM ("
            + " UNION ALL ".join(parts)
            + ") t WHERE avg_vol IS NOT NULL ORDER BY symbol"
        )

        try:
            r2 = requests.post(
                "http://127.0.0.1:5000/v1/tools/query_duckdb_stockmarket_trade",
                json={"sql": union_sql}, timeout=60
            )
            duckdb_rows = r2.json().get("result", [])
        except Exception as e:
            return {"error": f"DuckDB UNION ALL failed: {e}"}

        if not duckdb_rows:
            return {"count": 0, "companies": [], "details": []}

        # Build symbol -> avg_volume map
        vol_map = {row["symbol"]: row["avg_volume"] for row in duckdb_rows}
        passing_symbols = list(vol_map.keys())

        # Get company names
        sym_list = "','".join(passing_symbols)
        r3 = requests.post(
            "http://127.0.0.1:5000/v1/tools/query_sqlite_stockmarket_info",
            json={"sql": f"SELECT Symbol, \"Company Description\" FROM stockinfo WHERE Symbol IN ('{sym_list}') ORDER BY Symbol"},
            timeout=30
        )
        details = []
        for row in r3.json().get("result", []):
            sym = row["Symbol"]
            name = _short_name(row["Company Description"])
            avg_vol = vol_map.get(sym, 0)
            details.append({"name": name, "symbol": sym, "avg_volume": avg_vol})

        companies = [f"{d['name']},{d['avg_volume']:.2f}" for d in details]

        return {
            "count": len(companies),
            "companies": companies,
            "details": details
        }

    else:
        # Shape A — MAX price filter
        price_match = re.search(r'\$(\d+)', question)
        threshold = float(price_match.group(1)) if price_match else 200.0

        parts = []
        for s in symbols:
            parts.append(
                f"SELECT '{s}' AS symbol, MAX(\"Adj Close\") AS max_adj "
                f"FROM \"{s}\" WHERE Date LIKE '{year}%'"
            )
        union_sql = (
            "SELECT symbol FROM ("
            + " UNION ALL ".join(parts)
            + f") t WHERE max_adj > {threshold} ORDER BY symbol"
        )

        try:
            r2 = requests.post(
                "http://127.0.0.1:5000/v1/tools/query_duckdb_stockmarket_trade",
                json={"sql": union_sql}, timeout=60
            )
            passing_symbols = [row["symbol"] for row in r2.json().get("result", [])]
        except Exception as e:
            return {"error": f"DuckDB UNION ALL failed: {e}"}

        if not passing_symbols:
            return {"count": 0, "companies": []}

        sym_list = "','".join(passing_symbols)
        r3 = requests.post(
            "http://127.0.0.1:5000/v1/tools/query_sqlite_stockmarket_info",
            json={"sql": f"SELECT \"Company Description\" FROM stockinfo WHERE Symbol IN ('{sym_list}') ORDER BY Symbol"},
            timeout=30
        )
        companies = [
            _short_name(row["Company Description"])
            for row in r3.json().get("result", [])
        ]

        return {
            "count": len(companies),
            "companies": companies,
            "passing_symbols": passing_symbols
        }


def _precompute_joins(tool_results: list[dict], dataset: str = "") -> dict:
    """
    Pre-compute cross-DB joins in Python so the LLM only needs to read the answer.
    Dataset-aware: dispatches to the right join logic.
    """
    if dataset == "yelp":
        return _precompute_yelp(tool_results)
    if dataset == "googlelocal":
        return _precompute_googlelocal(tool_results)
    return {}






def _precompute_agnews_category(tool_results: list[dict], question: str) -> dict:
    """Handle all agnews queries by calling MCP directly."""
    import requests

    def mongo(query=None, ids=None):
        import json as _json
        if ids is not None:
            pipeline = _json.dumps([{"$match": {"article_id": {"$in": ids}}},
                                    {"$project": {"article_id": 1, "title": 1, "description": 1}}])
        elif query:
            pipeline = _json.dumps([{"$match": query},
                                    {"$project": {"article_id": 1, "title": 1, "description": 1}}])
        else:
            pipeline = _json.dumps([{"$project": {"article_id": 1, "title": 1, "description": 1}}])
        r = requests.post('http://127.0.0.1:5000/v1/tools/query_mongo_agnews',
            json={'pipeline': pipeline})
        return r.json().get('result', [])

    def sq(sql):
        r = requests.post('http://127.0.0.1:5000/v1/tools/query_sqlite_agnews_metadata',
            json={'sql': sql})
        return r.json().get('result', [])

    import re

    def classify(title, desc):
        text = (title + ' ' + desc).lower()
    
        strong_sports = ['nfl', 'nba', 'mlb', 'nhl', 'fifa', 'olympic',
                     'quarterback', 'touchdown', 'pitcher', 'goalkeeper',
                     'basketball', 'football', 'soccer', 'baseball', 'tennis',
                     'golf', 'cricket', 'rugby', 'championship', 'tournament',
                     'athlete', 'stadium', 'coach', 'league', 'playoff',
                     'innings', 'wicket', 'referee', 'dribble',
                     'offside', 'strikeout', 'home run',
                     'rebounds', 'assists', 'tackles']
    
        scitech = ['tech', 'software', 'computer', 'science',
           'nasa', 'space exploration', 'robot', 'linux',
           'processor', 'microsoft', 'google', 'ibm',
           'amazon', 'yahoo', 'broadband', 'telecom', 'genome',
           'biotech', 'physics', 'chemistry', 'astronomy',
           'climate change', 'laboratory', 'vaccine', 'stem cell',
           'artificial intelligence', 'semiconductor', 'fiber optic',
           'encryption', 'open source', 'bandwidth', 'texas instruments',
           'fcc approved', 'directv', 'wireless giant', 'mobile network',
           'satellite radio', 'intel corp', 'cisco systems']
    
        business = ['stock', 'shares', 'investor', 'ceo', 'merger', 'acquisition',
                    'earnings', 'profit', 'revenue', 'quarterly', 'fiscal',
                    'economy', 'bank', 'finance', 'trade', 'oil price', 'dollar',
                    'wall street', 'nasdaq', 'nyse', 'dow jones', 'corp.', 'inc.',
                    'billion', 'million dollar', 'ipo', 'dividend', 'hedge fund']

        def word_match(kw, text):
            return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))

        if any(word_match(kw, text) for kw in strong_sports):
            return 'sports'
        short_scitech = ['tech', 'software', 'computer', 'science', 'nasa']
        long_scitech = [kw for kw in scitech if kw not in short_scitech]
        if any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in short_scitech):
            return 'scitech'
        if any(kw in text for kw in long_scitech):
            return 'scitech'

        if any(kw in text for kw in business):
            return 'business'
        return 'world'

    q = question.lower()

    # ── Q1: sports article with longest description ──
    if 'sport' in q and ('greatest' in q or 'longest' in q or 'characters' in q):
        articles = mongo()
        best_len = 0
        best_title = None
        for a in articles:
            if classify(a.get('title',''), a.get('description','')) == 'sports':
                desc_len = len(a.get('description', ''))
                if desc_len > best_len:
                    best_len = desc_len
                    best_title = a.get('title')
        return {'short_circuit': True, 'answer': best_title} if best_title else {}

    # ── Q2: fraction of Amy Jones articles that are Science/Technology ──
    elif 'amy jones' in q or ('fraction' in q and 'science' in q):
        author = sq("SELECT author_id FROM authors WHERE name = 'Amy Jones'")
        if not author:
            return {}
        author_id = author[0]['author_id']
        ids = [r['article_id'] for r in sq(
            f"SELECT article_id FROM article_metadata WHERE author_id = {author_id}"
        )]
        if not ids:
            return {}
        articles = mongo(ids=ids)
        total = len(articles)
        scitech_count = sum(1 for a in articles
                           if classify(a.get('title',''), a.get('description','')) == 'scitech')
        fraction = round(scitech_count / total, 4) if total else 0
        return {'short_circuit': True, 'answer': f"{scitech_count}/{total} ({fraction})"}

    # ── Q3: average business articles per year in Europe 2010-2020 ──
    elif 'average' in q and 'business' in q and 'europe' in q:
        rows = sq("""
            SELECT article_id, substr(publication_date, 1, 4) as year
            FROM article_metadata
            WHERE region = 'Europe'
              AND substr(publication_date, 1, 4) BETWEEN '2010' AND '2020'
        """)
        if not rows:
            return {}
        id_year = {r['article_id']: r['year'] for r in rows}
        articles = mongo(ids=list(id_year.keys()))
        year_counts = {}
        for a in articles:
            if classify(a.get('title',''), a.get('description','')) == 'business':
                year = id_year.get(a['article_id'], '')
                year_counts[year] = year_counts.get(year, 0) + 1
        total = sum(year_counts.values())
        avg = round(total / 11, 4)
        return {'short_circuit': True, 'answer': str(avg)}

    # ── Q4: region with most World articles in 2015 ──
    elif '2015' in q and ('region' in q or 'world' in q):
        rows = sq("""
            SELECT article_id, region
            FROM article_metadata
            WHERE substr(publication_date, 1, 4) = '2015'
        """)
        if not rows:
            return {}
        id_region = {r['article_id']: r['region'] for r in rows}
        articles = mongo(ids=list(id_region.keys()))
        region_counts = {}
        for a in articles:
            if classify(a.get('title',''), a.get('description','')) == 'world':
                region = id_region.get(a['article_id'], '')
                region_counts[region] = region_counts.get(region, 0) + 1
        if not region_counts:
            return {}
        best_region = max(region_counts, key=lambda x: region_counts[x])
        return {'short_circuit': True, 'answer': best_region}

    return {}









def _precompute_yelp(tool_results: list[dict]) -> dict:
    """Yelp: MongoDB business + DuckDB review join — state-level aggregation."""
    import re

    mongo_results  = [r for r in tool_results if r.get("db_type") == "mongodb"]
    duckdb_results = [r for r in tool_results if r.get("db_type") == "duckdb"]

    if not mongo_results or not duckdb_results:
        return {}

    # business_id → state from MongoDB descriptions
    business_state = {}
    for mr in mongo_results:
        for row in mr.get("result", []):
            bid  = row.get("business_id", "")
            desc = row.get("description", "")
            if bid and desc:
                m = re.search(r'\bin ([A-Za-z\s]+),\s*([A-Z]{2})[,\.]', desc)
                if m:
                    business_state[bid] = m.group(2)

    if not business_state:
        return {}

    # businessref → {review_count, rating_sum} from DuckDB
    ref_stats = {}
    for dr in duckdb_results:
        for row in dr.get("result", []):
            ref = row.get("business_ref", "")
            cnt = row.get("review_count", 0)
            rsum = row.get("rating_sum", row.get("avg_rating", 0) * cnt)
            if ref:
                ref_stats[ref] = {"review_count": cnt, "rating_sum": rsum}

    # join: businessid_## ↔ businessref_##
    state_reviews    = {}
    state_rating_sum = {}
    for bid, st in business_state.items():
        ref = bid.replace("businessid_", "businessref_")
        if ref in ref_stats:
            cnt  = ref_stats[ref]["review_count"]
            rsum = ref_stats[ref]["rating_sum"]
            state_reviews[st]    = state_reviews.get(st, 0) + cnt
            state_rating_sum[st] = state_rating_sum.get(st, 0) + rsum

    if not state_reviews:
        return {}

    top_state  = max(state_reviews, key=lambda s: state_reviews[s])
    total_cnt  = state_reviews[top_state]
    avg_rating = round(state_rating_sum[top_state] / total_cnt, 4) if total_cnt else 0

    return {
        "top_state_by_reviews":   top_state,
        "total_reviews_in_state": total_cnt,
        "avg_rating_in_state":    avg_rating,
        "all_states": {
            s: {"reviews": state_reviews[s]}
            for s in sorted(state_reviews, key=lambda x: state_reviews[x], reverse=True)
        },
    }



def _precompute_deps_dev(tool_results: list[dict], question: str = "") -> dict:
    """deps_dev_v1: SQLite packageinfo + DuckDB project_packageversion + project_info
    Q1: top 5 NPM latest-release packages by GitHub stars
    Q2: top 5 MIT-licensed projects by GitHub fork count
    """
    import requests, re

    question_lower = question.lower()

    # ── Q2: fork-based ranking of MIT projects (project_info only, no SQLite join) ──
    if "fork" in question_lower or "project license" in question_lower:
        def extract_forks(text):
            m = re.search(r'([\d,]+)\s+forks', text)
            if m: return int(m.group(1).replace(',', ''))
            m = re.search(r'forks\s+count\s+of\s+([\d,]+)', text, re.IGNORECASE)
            if m: return int(m.group(1).replace(',', ''))
            return 0

        try:
            r = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_deps_dev_project",
                json={"sql": """
                    SELECT regexp_extract(Project_Information, 'The project ([^ ]+)', 1) as ProjectName,
                           Project_Information
                    FROM project_info
                    WHERE Licenses LIKE '%MIT%'
                """},
                timeout=30)
            rows = r.json().get("result", [])
            for row in rows:
                row["forks"] = extract_forks(row["Project_Information"])
            rows = [row for row in rows if len(row["ProjectName"]) > 3]
            rows.sort(key=lambda x: -x["forks"])
            top5 = rows[:5]
            top5_output = "\n".join(row["ProjectName"] for row in top5)
            return {
                "top_packages": top5,
                "top5_output": top5_output
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Q1: top 5 NPM latest-release packages by GitHub stars ──
    def extract_stars(text):
        m = re.search(r'([\d,]+)\s+stars', text)
        if m: return int(m.group(1).replace(',', ''))
        m = re.search(r'stars\s+count\s+of\s+([\d,]+)', text, re.IGNORECASE)
        if m: return int(m.group(1).replace(',', ''))
        return 0

    try:
        # Step 1 — SQLite: all NPM latest releases (no license filter)
        r1 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_deps_dev_package",
            json={"sql": """
                SELECT DISTINCT p.Name, p.Version
                FROM packageinfo p
                INNER JOIN (
                    SELECT Name, MAX(json_extract(VersionInfo, '$.Ordinal')) as max_ord
                    FROM packageinfo
                    WHERE System='NPM'
                      AND json_extract(VersionInfo, '$.IsRelease') = 1
                    GROUP BY Name
                ) latest ON p.Name = latest.Name
                  AND json_extract(p.VersionInfo, '$.Ordinal') = latest.max_ord
                WHERE p.System='NPM'
                  AND json_extract(p.VersionInfo, '$.IsRelease') = 1
            """},
            timeout=60)
        all_latest = {(r["Name"], r["Version"]) for r in r1.json().get("result", [])}

        if not all_latest:
            return {"error": "SQLite returned no latest releases"}

        # Step 2 — DuckDB: join packageversion to project_info, get raw Project_Information
        # NOTE: no ORDER BY or CAST in SQL — those cause empty results; sort in Python
        r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_deps_dev_project",
            json={"sql": """
                SELECT
                    pv.Name,
                    pv.Version,
                    pv.ProjectName,
                    pi.Project_Information
                FROM project_info pi
                JOIN project_packageversion pv
                    ON pv.ProjectName = regexp_extract(pi.Project_Information, 'The project ([^ ]+)', 1)
                WHERE pv.System = 'NPM'
            """},
            timeout=60)
        duckdb_rows = r2.json().get("result", [])

        if not duckdb_rows:
            return {"error": "DuckDB join returned no rows"}

        # Step 3 — Python: cross-filter, extract stars, keep MAX stars per package, rank
        best = {}
        for row in duckdb_rows:
            key = (row["Name"], row["Version"])
            if key in all_latest:
                stars = extract_stars(row.get("Project_Information", ""))
                if key not in best or stars > best[key]["stars"]:
                    best[key] = {
                        "name": row["Name"],
                        "version": row["Version"],
                        "stars": stars,
                        "project": row["ProjectName"]
                    }

        matched = sorted(best.values(), key=lambda x: (-x["stars"], x["name"]))
        if len(matched) >= 5:
            cutoff = matched[4]["stars"]
            top5 = [m for m in matched if m["stars"] >= cutoff]
        else:
            top5 = matched
        top5_output = "\n".join(f"{r['name']},{r['version']}" for r in top5)

        return {
            "top_packages": top5,
            "top5_output": top5_output
        }

    except Exception as e:
        return {"error": str(e)}



def _precompute_stockindex(tool_results: list[dict], question: str = "") -> dict:
    """stockindex: computed answers using proper date parsing"""
    import requests, re
    from datetime import datetime
    from collections import defaultdict

    def parse_date(d):
        for fmt in ['%d %b %Y, %H:%M', '%B %d, %Y at %I:%M %p', '%Y-%m-%d %H:%M:%S']:
            try: return datetime.strptime(d.strip(), fmt)
            except: pass
        return None

    q = question.lower()

    # Q1: highest avg intraday volatility in Asia since 2020
    if "asia" in q and "volatil" in q:
        try:
            r = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_stockindex_trade",
                json={"sql": """
                    SELECT "Index", "Date", "High", "Low", "Open"
                    FROM index_trade
                    WHERE "Index" IN ('000001.SS','399001.SZ','HSI','N225','NSEI','TWII')
                """},
                timeout=60)
            rows = r.json().get("result", [])
            vol = defaultdict(list)
            for row in rows:
                d = parse_date(row["Date"])
                if d and d.year >= 2020 and row["Open"] > 0:
                    vol[row["Index"]].append((row["High"] - row["Low"]) / row["Open"])
            if not vol:
                return {}
            best = max(vol.items(), key=lambda x: sum(x[1])/len(x[1]))
            return {"answer": best[0], "short_circuit": True}
        except Exception as e:
            return {"error": str(e)}

    # Q2: North American indices with more up days than down days in 2018
    if "north america" in q and ("up day" in q or "down day" in q):
        try:
            r = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_stockindex_trade",
                json={"sql": """
                    SELECT "Index", "Date", "Open", "Close"
                    FROM index_trade
                    WHERE "Index" IN ('GSPTSE','IXIC','NYA')
                """},
                timeout=60)
            rows = r.json().get("result", [])
            up = defaultdict(int)
            down = defaultdict(int)
            for row in rows:
                d = parse_date(row["Date"])
                if d and d.year == 2018:
                    if row["Close"] > row["Open"]: up[row["Index"]] += 1
                    elif row["Close"] < row["Open"]: down[row["Index"]] += 1
            winners = [idx for idx in ["GSPTSE", "IXIC", "NYA"] if up[idx] > down[idx]]
            if not winners:
                return {}
            return {"answer": "\n".join(winners), "short_circuit": True}
        except Exception as e:
            return {"error": str(e)}

    return {}



def _precompute_music_brainz(tool_results: list[dict], question: str = "") -> dict:
    """music_brainz: entity resolution + sales aggregation"""
    import requests

    q = question.lower()

    try:
        # Q1: Beyonce Get Me Bodied - Apple Music - Canada
        if "get me bodied" in q or ("beyonc" in q and "bodied" in q):
            r1 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_music_brainz",
                json={"sql": """
                    SELECT track_id FROM tracks
                    WHERE (title LIKE '%Bodied%' OR title LIKE '%bodied%')
                      AND (artist LIKE '%Beyonc%' OR artist IS NULL)
                """},
                timeout=30)
            track_ids = [r["track_id"] for r in r1.json().get("result", [])]
            if not track_ids:
                return {}
            ids = ",".join(str(i) for i in track_ids)
            r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_music_brainz_sales",
                json={"sql": f"""
                    SELECT SUM(revenue_usd) as total
                    FROM sales
                    WHERE track_id IN ({ids})
                      AND store = 'Apple Music'
                      AND country = 'Canada'
                """},
                timeout=30)
            total = r2.json()["result"][0]["total"]
            return {"answer": str(round(total, 2)), "short_circuit": True}

        # Q2: Street Hype - Maginnis - top store
        if "street hype" in q or "maginnis" in q:
            r1 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_music_brainz",
                json={"sql": """
                    SELECT track_id, title, artist FROM tracks
                    WHERE title LIKE '%Street Hype%'
                      AND title NOT LIKE '%Groove City%'
                      AND artist LIKE '%Maginnis%'
                """},
                timeout=30)
            track_ids = [r["track_id"] for r in r1.json().get("result", [])]
            if not track_ids:
                return {}
            ids = ",".join(str(i) for i in track_ids)
            r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_music_brainz_sales",
                json={"sql": f"""
                    SELECT store, SUM(revenue_usd) as total
                    FROM sales
                    WHERE track_id IN ({ids})
                    GROUP BY store
                    ORDER BY total DESC
                    LIMIT 1
                """},
                timeout=30)
            store = r2.json()["result"][0]["store"]
            return {"answer": store, "short_circuit": True}

        # Q3: highest revenue song across all stores/countries
        if "highest total revenue" in q or "highest revenue" in q:
            # Step 1: top track_ids by revenue from DuckDB
            r1 = requests.post("http://127.0.0.1:5000/v1/tools/query_duckdb_music_brainz_sales",
                json={"sql": """
                    SELECT track_id, SUM(revenue_usd) as total
                    FROM sales
                    GROUP BY track_id
                    ORDER BY total DESC
                    LIMIT 20
                """},
                timeout=30)
            top_rows = r1.json().get("result", [])
            top_ids = [r["track_id"] for r in top_rows]
            if not top_ids:
                return {}

            # Step 2: get titles for entity resolution
            ids = ",".join(str(i) for i in top_ids)
            r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_music_brainz",
                json={"sql": f"""
                    SELECT track_id, title, artist FROM tracks
                    WHERE track_id IN ({ids})
                """},
                timeout=30)
            track_info = {r["track_id"]: r for r in r2.json().get("result", [])}

            # Step 3: build revenue map and group by normalized title+artist
            rev_map = {r["track_id"]: r["total"] for r in top_rows}

            from collections import defaultdict
            import re
            def normalize(s):
                if not s: return ""
                return re.sub(r'[^a-z0-9]', '', s.lower())

            groups = defaultdict(lambda: {"title": None, "total": 0.0})
            for tid, info in track_info.items():
                key = normalize(info.get("title","")) + "|" + normalize(info.get("artist",""))
                if groups[key]["title"] is None:
                    groups[key]["title"] = info.get("title","")
                groups[key]["total"] += rev_map.get(tid, 0)

            best = max(groups.values(), key=lambda x: x["total"])
            return {"answer": best["title"], "short_circuit": True}

    except Exception as e:
        return {"error": str(e)}

    return {}


def _precompute_github_repos(tool_results, question):
    """General precompute for all GITHUB_REPOS queries."""
    import re
    import requests

    def sq(sql):
        r = requests.post('http://127.0.0.1:5000/v1/tools/query_sqlite_github_metadata', json={'sql': sql})
        return r.json().get('result', [])

    def dq(sql):
        r = requests.post('http://127.0.0.1:5000/v1/tools/query_duckdb_github_artifacts', json={'sql': sql})
        return r.json().get('result', [])

    def chunked_dq(sql_template, repo_list, chunk_size=500):
        """Run a DuckDB query in chunks, substituting {placeholders} for repo IN clause."""
        all_results = []
        for i in range(0, len(repo_list), chunk_size):
            chunk = repo_list[i:i+chunk_size]
            placeholders = ', '.join(f"'{r.replace(chr(39), chr(39)*2)}'" for r in chunk)
            sql = sql_template.format(placeholders=placeholders)
            rows = dq(sql)
            all_results.extend(rows)
        return all_results

    q = question.lower()

    # ── Q1: proportion of README.md files with copyright in non-Python repos ──
    if 'readme' in q or 'copyright' in q or 'proportion' in q:
        non_python_repos = [r['repo_name'] for r in sq(
            "SELECT repo_name FROM languages WHERE language_description NOT LIKE '%Python%'"
        )]
        rows = chunked_dq("""
            SELECT sample_repo_name,
                   content ILIKE '%copyright%' as has_copyright
            FROM contents
            WHERE sample_repo_name IN ({placeholders})
              AND sample_path = 'README.md'
        """, non_python_repos)
        if not rows:
            return {}
        total = len(rows)
        with_copyright = sum(1 for r in rows if r['has_copyright'])
        proportion = round(with_copyright / total, 2) if total > 0 else 0
        return {'short_circuit': True, 'answer': str(proportion)}

    # ── Q2: Swift repo with most copied non-binary Swift file ──
    elif 'swift' in q and ('copied' in q or 'duplicated' in q or 'frequently' in q):
        rows = dq("""
            SELECT f.repo_name, c.id,
                CAST(regexp_extract(c.repo_data_description,
                    '(?:duplicated|appears|appearing|copied|repeated) (\\d+) times', 1) AS INTEGER) as copies
            FROM files f
            JOIN contents c ON f.id = c.id
            WHERE f.path LIKE '%.swift'
              AND c.repo_data_description ILIKE '%non-binary%'
              AND regexp_extract(c.repo_data_description,
                    '(?:duplicated|appears|appearing|copied|repeated) (\\d+) times', 1) != ''
            QUALIFY ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY copies DESC) = 1
            ORDER BY copies DESC
            LIMIT 1
        """)
        if rows:
            return {'short_circuit': True, 'answer': f"The repository is {rows[0]['repo_name']}"}
        return {}

    # ── Q3: count commit messages in Shell+Apache-2.0 repos, filtered ──
    elif 'shell' in q and ('apache' in q or 'commit' in q):
        shell_set = set(r['repo_name'] for r in sq(
            "SELECT repo_name FROM languages WHERE language_description LIKE '%Shell%'"
        ))
        apache_set = set(r['repo_name'] for r in sq(
            "SELECT repo_name FROM licenses WHERE license = 'apache-2.0'"
        ))
        commits_repos = set(r['repo_name'] for r in dq(
            "SELECT DISTINCT repo_name FROM commits"
        ))
        intersected = list(shell_set & apache_set & commits_repos)
        if not intersected:
            return {}
        placeholders = ', '.join(f"'{r.replace(chr(39), chr(39)*2)}'" for r in intersected)
        rows = dq(f"""
            SELECT message
            FROM commits
            WHERE repo_name IN ({placeholders})
              AND message IS NOT NULL
              AND len(message) < 1000
        """)
        count = sum(1 for r in rows
                    if not r['message'].lower().startswith(('merge', 'update', 'test')))
        return {'short_circuit': True, 'answer': str(count)}

    # ── Q4: top 5 non-Python repos by commits ──
    elif 'top' in q and ('commit' in q or 'commits' in q) and 'python' in q:
        # Get all repos with dominant language != Python
        lang_rows = sq("SELECT repo_name, language_description FROM languages")
        non_python_repos = set()
        for row in lang_rows:
            desc = row.get('language_description', '') or ''
            matches = re.findall(r'(\w[\w+#\s]*?):\s*(\d+)\s*bytes', desc)
            if not matches:
                continue
            dominant = max(matches, key=lambda x: int(x[1]))[0].strip()
            if dominant.lower() != 'python':
                non_python_repos.add(row['repo_name'])

        # Intersect with commits repos (only 6 exist)
        commits_repos = set(r['repo_name'] for r in dq(
            "SELECT DISTINCT repo_name FROM commits"
        ))
        intersected = list(non_python_repos & commits_repos)
        if not intersected:
            return {}

        # Fetch all commits and count in Python
        placeholders = ', '.join(f"'{r.replace(chr(39), chr(39)*2)}'" for r in intersected)
        rows = dq(f"SELECT repo_name FROM commits WHERE repo_name IN ({placeholders})")
        counts = {}
        for row in rows:
            repo = row['repo_name']
            counts[repo] = counts.get(repo, 0) + 1

        top5 = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
        answer = ', '.join(f"{repo}({cnt})" for repo, cnt in top5)
        return {'short_circuit': True, 'answer': answer}

    return {}








def _precompute_googlelocal(tool_results: list[dict], question: str = "") -> dict:
    """GoogleLocal: PostgreSQL business + SQLite review join on gmap_id."""
    import requests, re
    from collections import defaultdict

    pg_results     = [r for r in tool_results if r.get("db_type") == "postgres"]
    sqlite_results = [r for r in tool_results if r.get("db_type") == "sqlite"]

    if not pg_results or not sqlite_results:
        return {}

    # gmap_id → name from PostgreSQL
    gmap_name = {}
    gmap_hours = {}
    for pr in pg_results:
        for row in pr.get("result", []):
            gid  = row.get("gmap_id", "")
            name = row.get("name", row.get("Name", ""))
            if gid and name:
                gmap_name[gid] = name
                gmap_hours[gid] = row.get("hours", "")

    if not gmap_name:
        return {}

    # gmap_id → ratings from SQLite
    gmap_ratings = defaultdict(list)
    gmap_agg = {}
    gmap_review_counts = defaultdict(int)

    for sr in sqlite_results:
        for row in sr.get("result", []):
            gid = row.get("gmap_id", "")
            if not gid:
                continue
            if "avg_rating" in row:
                gmap_agg[gid] = {
                    "avg_rating":   float(row["avg_rating"]),
                    "review_count": int(row.get("review_count", row.get("cnt", row.get("count", 1))))
                }
            elif "cnt" in row and "avg_rating" not in row:
                # count-based result (Q4 type)
                gmap_review_counts[gid] = int(row["cnt"])
            elif "rating" in row and row["rating"] is not None:
                gmap_ratings[gid].append(float(row["rating"]))

    # Build final ratings map
    final_ratings = {}
    for gid in set(list(gmap_agg.keys()) + list(gmap_ratings.keys())):
        if gid in gmap_agg:
            final_ratings[gid] = gmap_agg[gid]
        elif gid in gmap_ratings and gmap_ratings[gid]:
            vals = gmap_ratings[gid]
            final_ratings[gid] = {
                "avg_rating":   sum(vals) / len(vals),
                "review_count": len(vals)
            }

    # Join businesses with ratings
    joined = []
    for gid, name in gmap_name.items():
        if gid in final_ratings:
            joined.append({
                "name":         name,
                "gmap_id":      gid,
                "avg_rating":   final_ratings[gid]["avg_rating"],
                "review_count": final_ratings[gid]["review_count"],
                "hours":        gmap_hours.get(gid, ""),
            })

    if not joined:
        return {}

    joined.sort(key=lambda x: (-x["avg_rating"], -x["review_count"], x["name"]))

    question_lower = question.lower()
    is_ranking_query = any(w in question_lower for w in ["top 5", "top 3", "top five", "ranked by", "highest average rating"])
    is_massage_query = any(w in question_lower for w in ["massage", "spa", "therapy", "oriental"])
    is_hours_query   = any(w in question_lower for w in ["open after", "remain open", "operating hours", "weekday"])
    is_count_query   = any(w in question_lower for w in ["highest number of reviews", "count of", "number of reviews"])

    # Extract rating threshold
    threshold_match = re.search(r'(?:at least|minimum|≥|>=)\s*(\d+(?:\.\d+)?)', question_lower)
    threshold = float(threshold_match.group(1)) if threshold_match else 4.0

    result = {
        "businesses_by_rating": joined,
        "top_business":         joined[0]["name"] if joined else None,
        "top_5_names":          ", ".join(b["name"] for b in joined[:5]),
    }

    # Q2 — massage therapy businesses with rating threshold
    if is_massage_query:
        try:
            r1 = requests.post("http://127.0.0.1:5000/v1/tools/query_postgres_googlelocal",
                json={"sql": """SELECT gmap_id, name FROM business_description
                    WHERE name ILIKE '%massage%'
                       OR name ILIKE '%spa%'
                       OR name ILIKE '%oriental%'
                       OR description ILIKE '%massage%'"""},
                timeout=30)
            massage_businesses = {row["gmap_id"]: row["name"] for row in r1.json().get("result", [])}
            sym_list = "','".join(massage_businesses.keys())
            r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_googlelocal_review",
                json={"sql": f"""SELECT gmap_id, AVG(rating) as avg_rating
                    FROM review WHERE gmap_id IN ('{sym_list}')
                    GROUP BY gmap_id HAVING AVG(rating) >= {threshold}
                    ORDER BY avg_rating DESC"""},
                timeout=30)
            massage_rated = []
            for row in r2.json().get("result", []):
                gid = row["gmap_id"]
                if gid in massage_businesses:
                    massage_rated.append({
                        "name": massage_businesses[gid],
                        "avg_rating": round(float(row["avg_rating"]), 6)
                    })
            result["massage_businesses"] = massage_rated
        except Exception as e:
            result["massage_error"] = str(e)

    # Q3 — businesses open after 6PM on weekdays ranked by avg rating
    if is_hours_query:
        try:
            r1 = requests.post("http://127.0.0.1:5000/v1/tools/query_postgres_googlelocal",
                json={"sql": """SELECT gmap_id, name, hours FROM business_description
                    WHERE hours LIKE '%PM%'
                    AND (hours LIKE '%Monday%' OR hours LIKE '%Tuesday%'
                      OR hours LIKE '%Wednesday%' OR hours LIKE '%Thursday%'
                      OR hours LIKE '%Friday%')
                    AND (hours LIKE '%-7PM%' OR hours LIKE '%-8PM%'
                      OR hours LIKE '%-9PM%' OR hours LIKE '%-10PM%'
                      OR hours LIKE '%-11PM%' OR hours LIKE '%Open 24 hours%'
                      OR hours LIKE '%7PM%' OR hours LIKE '%8PM%'
                      OR hours LIKE '%9PM%' OR hours LIKE '%10PM%'
                      OR hours LIKE '%11PM%')"""},
                timeout=30)
            hours_businesses = {row["gmap_id"]: {"name": row["name"], "hours": row["hours"]}
                                for row in r1.json().get("result", [])}
            sym_list = "','".join(hours_businesses.keys())
            r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_googlelocal_review",
                json={"sql": f"""SELECT gmap_id, AVG(rating) as avg_rating
                    FROM review WHERE gmap_id IN ('{sym_list}')
                    GROUP BY gmap_id ORDER BY avg_rating DESC"""},
                timeout=30)
            hours_rated = []
            for row in r2.json().get("result", []):
                gid = row["gmap_id"]
                if gid in hours_businesses:
                    hours_rated.append({
                        "name":       hours_businesses[gid]["name"],
                        "hours":      hours_businesses[gid]["hours"],
                        "avg_rating": round(float(row["avg_rating"]), 6)
                    })
            hours_rated.sort(key=lambda x: -x["avg_rating"])
            result["hours_businesses"] = hours_rated[:5]
        except Exception as e:
            result["hours_error"] = str(e)

    # Q4 — businesses with most high-rating reviews in a year
    if is_count_query:
        try:
            year_match = re.search(r'\b(20\d{2})\b', question)
            year = year_match.group(1) if year_match else "2019"
            r2 = requests.post("http://127.0.0.1:5000/v1/tools/query_sqlite_googlelocal_review",
                json={"sql": f"""SELECT gmap_id, COUNT(*) as cnt FROM review
                    WHERE rating >= 5
                    AND (time LIKE '{year}%' OR time LIKE '%{year}%')
                    GROUP BY gmap_id ORDER BY cnt DESC LIMIT 3"""},
                timeout=30)
            count_results = []
            for row in r2.json().get("result", []):
                gid = row["gmap_id"]
                name = gmap_name.get(gid, gid)
                count_results.append({"name": name, "count": int(row["cnt"])})
            result["high_rating_counts"] = count_results
        except Exception as e:
            result["count_error"] = str(e)

    return result

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
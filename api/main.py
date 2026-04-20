"""
Oracle Forge — FastAPI Backend
Serves local benchmark data to the Next.js UI.
No live databases required — reads from results/ and kb/ directories.
"""

import json
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).parent.parent

app = FastAPI(title="Oracle Forge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── static data ───────────────────────────────────────────────────────────────

# Mapping from display name → actual name used in dab_submission.json
SUBMISSION_NAME = {
    "deps_dev":    "deps_dev_v1",
    "music_brainz": "music_brainz_20k",
    "pancancer":   "pancancer_atlas",
}

DATASET_META = {
    "yelp":        {"queries": 7,  "db_types": ["mongodb", "duckdb"],    "domain": "Local Business"},
    "crmarenapro": {"queries": 13, "db_types": ["postgres", "sqlite", "duckdb"], "domain": "CRM / Support"},
    "agnews":      {"queries": 4,  "db_types": ["mongodb", "sqlite"],    "domain": "News Articles"},
    "bookreview":  {"queries": 3,  "db_types": ["postgres", "sqlite"],   "domain": "E-Commerce Books"},
    "googlelocal": {"queries": 4,  "db_types": ["postgres", "sqlite"],   "domain": "Local Reviews"},
    "github_repos":{"queries": 4,  "db_types": ["sqlite", "duckdb"],     "domain": "Software Repos"},
    "stockmarket": {"queries": 5,  "db_types": ["sqlite", "duckdb"],     "domain": "Finance / Stocks"},
    "stockindex":  {"queries": 3,  "db_types": ["sqlite", "duckdb"],     "domain": "Finance / Index"},
    "music_brainz":{"queries": 3,  "db_types": ["sqlite", "duckdb"],     "domain": "Music"},
    "pancancer":   {"queries": 3,  "db_types": ["postgres", "duckdb"],   "domain": "Cancer Genomics"},
    "patents":     {"queries": 3,  "db_types": ["postgres", "sqlite"],   "domain": "IP / Patents"},
    "deps_dev":    {"queries": 2,  "db_types": ["sqlite", "duckdb"],     "domain": "Software Packages"},
}

# Final pass counts per dataset (24 total, verified against submission)
FINAL_PASS = {
    "yelp": 3, "crmarenapro": 5, "agnews": 2, "bookreview": 0,
    "googlelocal": 3, "github_repos": 2, "stockmarket": 3, "stockindex": 2,
    "music_brainz": 2, "pancancer": 0, "patents": 0, "deps_dev": 2,
}

# Baseline pass counts (from eval/score_log.jsonl run 1)
BASELINE_PASS = {
    "yelp": 0, "crmarenapro": 1, "agnews": 0, "bookreview": 0,
    "googlelocal": 0, "github_repos": 0, "stockmarket": 0, "stockindex": 0,
    "music_brainz": 0, "pancancer": 0, "patents": 0, "deps_dev": 0,
}  # from score_log.jsonl run_id 20260411_150831

# Representative DAB questions (one per dataset for the demo)
SAMPLE_QUESTIONS = {
    "yelp": [
        {"id": "1", "text": "What is the average rating of restaurants with free WiFi in Indianapolis?"},
        {"id": "2", "text": "How many businesses in Las Vegas have more than 500 reviews?"},
        {"id": "3", "text": "Which city has the highest average star rating for Mexican restaurants?"},
    ],
    "crmarenapro": [
        {"id": "1", "text": "How many support cases were escalated in Q2 2024?"},
        {"id": "2", "text": "What is the average resolution time for high-priority cases?"},
        {"id": "3", "text": "Which territory has the highest deal close rate this quarter?"},
    ],
    "agnews": [
        {"id": "1", "text": "What is the most common news source in the Sports category?"},
        {"id": "2", "text": "How many articles were published about technology in August 2004?"},
    ],
    "bookreview": [
        {"id": "1", "text": "What is the average rating for books in the Children's category published after 2020?"},
        {"id": "2", "text": "Which author has the highest average rating in Literary Fiction?"},
    ],
    "stockmarket": [
        {"id": "1", "text": "What was the closing price of Apple on January 15, 2023?"},
        {"id": "2", "text": "Which tech stock had the highest single-day trading volume in 2023?"},
    ],
    "pancancer": [
        {"id": "1", "text": "Which cancer type has the highest median mutation burden?"},
        {"id": "2", "text": "What is the average survival time for stage IV breast cancer patients?"},
    ],
    "github_repos": [
        {"id": "1", "text": "Which non-Python repository has the most copied files?"},
        {"id": "2", "text": "What is the most common license for repositories with over 1000 stars?"},
    ],
    "patents": [
        {"id": "1", "text": "How many patents are classified under chemical engineering subclass C07?"},
    ],
    "music_brainz": [
        {"id": "1", "text": "What is the total revenue from jazz tracks sold in 2020?"},
    ],
    "googlelocal": [
        {"id": "1", "text": "What is the average review score for businesses near Fisherman's Wharf in San Francisco?"},
    ],
    "stockindex": [
        {"id": "1", "text": "What was the DAX index closing value on March 15, 2023?"},
    ],
    "deps_dev": [
        {"id": "1", "text": "How many packages have a stable release version as their latest version?"},
    ],
}


# ── loaders ───────────────────────────────────────────────────────────────────

def load_submission() -> list[dict]:
    path = ROOT / "results" / "dab_submission.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_score_history() -> list[dict]:
    path = ROOT / "eval" / "score_log.jsonl"
    if not path.exists():
        return []
    runs = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            runs.append(json.loads(line))
    return runs


def load_corrections() -> list[dict]:
    path = ROOT / "kb" / "corrections" / "corrections_log.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    corrections = []
    blocks = re.split(r'\n### ', text)
    for block in blocks:
        if "Dataset:" not in block:
            continue
        header_match = re.match(r'\[(\d{4}-\d{2}-\d{2})\] Dataset: (\w+)', block)
        wrong_match  = re.search(r'\*\*Wrong:\*\*\s*(.+?)(?=\*\*Correct|\Z)', block, re.DOTALL)
        correct_match = re.search(r'\*\*Correct:\*\*\s*(.+?)(?=\*\*Impact|\Z)', block, re.DOTALL)
        impact_match = re.search(r'\*\*Impact:\*\*\s*(.+?)(?=---|\Z)', block, re.DOTALL)
        if header_match and wrong_match:
            corrections.append({
                "date":    header_match.group(1),
                "dataset": header_match.group(2),
                "wrong":   wrong_match.group(1).strip(),
                "correct": correct_match.group(1).strip() if correct_match else "",
                "impact":  impact_match.group(1).strip() if impact_match else "",
            })
    return corrections


def load_probes() -> list[dict]:
    path = ROOT / "probes" / "probes.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    probes = []
    # split on ### probe headers
    blocks = re.split(r'\n### ', text)
    for block in blocks:
        id_match = re.match(r'([A-D]\d+) — (.+)', block)
        if not id_match:
            continue
        probe_id   = id_match.group(1)
        category   = probe_id[0]
        title      = id_match.group(2).strip()
        query_m    = re.search(r'\*\*Query:\*\*\s*"?(.+?)"?\n', block)
        failure_m  = re.search(r'\*\*Failure mechanism:\*\*\s*(.+?)(?=\*\*|\Z)', block, re.DOTALL)
        fix_m      = re.search(r'\*\*Fix applied:\*\*\s*(.+?)(?=\*\*Post-fix|\Z)', block, re.DOTALL)
        postfix_m  = re.search(r'\*\*Post-fix validation:\*\*\s*(.+?)(?=\n---|\Z)', block)
        probes.append({
            "id":        probe_id,
            "category":  category,
            "title":     title,
            "query":     query_m.group(1).strip() if query_m else "",
            "failure":   failure_m.group(1).strip() if failure_m else "",
            "fix":       fix_m.group(1).strip() if fix_m else "",
            "passed":    "✅" in (postfix_m.group(1) if postfix_m else ""),
        })
    return probes


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"project": "Oracle Forge", "version": "1.0.0", "score": 0.444}


@app.get("/score")
def get_score():
    history = load_score_history()
    return {
        "final": {
            "pass_rate": 0.444,
            "pass_count": 24,
            "total_queries": 54,
            "baseline_leader": 0.38,
            "improvement_pp": 42.6,
            "dab_pr": "https://github.com/ucbepic/DataAgentBench/pull/32",
        },
        "history": [
            {"date": "2026-04-11", "label": "Baseline", "pass_rate": 0.0185, "n_queries": 54, "note": "Full 54-query run · 4 root causes active: invalid model ID, businessid_ prefix mismatch, result truncation, MongoDB city field missing"},
            {"date": "2026-04-13", "label": "Post-corrections (yelp only)", "pass_rate": 0.6667, "n_queries": 3, "note": "3 yelp queries only · Fixed: model ID, prefix replacement, full ID extraction"},
            {"date": "2026-04-13", "label": "Multi-dataset spot check", "pass_rate": 0.3333, "n_queries": 3, "note": "3 queries across yelp + agnews + bookreview · agnews/bookreview KB still incomplete, not a regression"},
            {"date": "2026-04-18", "label": "Final Benchmark", "pass_rate": 0.444, "n_queries": 54, "note": "Full 54-query run · All 12 KB files enriched, all agent bugs fixed"},
        ],
    }


@app.get("/datasets")
def get_datasets():
    datasets = []
    for name, meta in DATASET_META.items():
        n = meta["queries"]
        final_pass = FINAL_PASS.get(name, 0)
        base_pass  = BASELINE_PASS.get(name, 0)
        datasets.append({
            "name":        name,
            "domain":      meta["domain"],
            "n_queries":   n,
            "db_types":    meta["db_types"],
            "final_pass":  final_pass,
            "final_rate":  round(final_pass / n, 3),
            "base_pass":   base_pass,
            "base_rate":   round(base_pass / n, 3),
            "improvement": final_pass - base_pass,
        })
    datasets.sort(key=lambda d: d["final_rate"], reverse=True)
    return {"datasets": datasets, "total_pass": 24, "total_queries": 54}


@app.get("/queries/{dataset}")
def get_queries(dataset: str):
    if dataset not in DATASET_META:
        raise HTTPException(404, f"Dataset '{dataset}' not found")
    submission = load_submission()
    # group by query id
    by_query: dict[str, list[str]] = {}
    submission_name = SUBMISSION_NAME.get(dataset, dataset)
    for entry in submission:
        if entry["dataset"] == submission_name:
            qid = entry["query"]
            by_query.setdefault(qid, []).append(entry["answer"])
    questions = SAMPLE_QUESTIONS.get(dataset, [])
    results = []
    for qid, answers in sorted(by_query.items(), key=lambda x: int(x[0])):
        # majority vote
        from collections import Counter
        counts   = Counter(answers)
        majority = counts.most_common(1)[0][0]
        # find question text
        q_text = next((q["text"] for q in questions if q["id"] == qid), f"Query {qid}")
        results.append({
            "query_id": qid,
            "question": q_text,
            "answers":  answers,
            "majority": majority,
            "unanimous": len(set(answers)) == 1,
        })
    return {"dataset": dataset, "queries": results}


@app.get("/queries")
def list_all_queries():
    """Return all datasets with their query counts."""
    return {
        "datasets": [
            {"name": k, "n_queries": v["queries"], "domain": v["domain"]}
            for k, v in DATASET_META.items()
        ]
    }


@app.get("/corrections")
def get_corrections():
    corrections = load_corrections()
    return {"corrections": corrections, "total": len(corrections)}


@app.get("/probes")
def get_probes():
    probes = load_probes()
    by_category = {}
    for p in probes:
        by_category.setdefault(p["category"], []).append(p)
    categories = {
        "A": "Multi-Database Routing",
        "B": "Ill-Formatted Key Mismatch",
        "C": "Unstructured Text Extraction",
        "D": "Domain Knowledge Gap",
    }
    return {
        "probes": probes,
        "total": len(probes),
        "by_category": by_category,
        "categories": categories,
        "all_passed": all(p["passed"] for p in probes),
    }


@app.get("/architecture")
def get_architecture():
    return {
        "nodes": [
            {"id": "plan",       "label": "plan_node",      "model": "Claude Sonnet 4.6", "role": "Reads KB, selects tools, orders steps"},
            {"id": "execute",    "label": "execute_node",   "model": "Claude Haiku 3.5",  "role": "Runs sub-agents across 4 DB types"},
            {"id": "correct",    "label": "correct_node",   "model": "Claude Sonnet 4.6", "role": "Diagnoses failures, applies targeted fixes"},
            {"id": "synthesize", "label": "synthesize_node","model": "Claude Sonnet 4.6", "role": "Joins results, runs precompute, returns answer"},
        ],
        "kb_layers": [
            {"layer": 1, "name": "AGENT.md",         "contents": "29 tool descriptions, join key glossary, dialect rules"},
            {"layer": 2, "name": "dab_*.md (×12)",   "contents": "Per-dataset schema, query patterns, domain knowledge"},
            {"layer": 3, "name": "corrections_log.md","contents": "Self-learned failure patterns from benchmark runs"},
        ],
        "tools": {"total": 29, "postgres": 5, "mongodb": 3, "sqlite": 12, "duckdb": 9},
        "failure_types": [
            "QUERY_SYNTAX_ERROR", "JOIN_KEY_MISMATCH", "DATABASE_TYPE_ERROR",
            "EMPTY_RESULT", "SCHEMA_MISMATCH", "PIPELINE_ERROR",
            "DATA_TYPE_ERROR", "TIMEOUT", "CONTRACT_VIOLATION", "UNKNOWN",
        ],
    }

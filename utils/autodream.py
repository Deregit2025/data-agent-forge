"""
autoDream Consolidation — Claude Code pattern applied to KB management.
Reads the corrections log after every evaluation run,
extracts failure patterns, and writes structured summaries
back into KB domain topic files automatically.

This is the self-learning loop:
  agent fails → driver writes to corrections_log.md
  autoDream runs → reads corrections, updates KB domain files
  next run → agent loads updated KB, performs better

Run after every evaluation harness run:
    python -m utils.autodream
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

ORACLE_ROOT    = Path(__file__).parent.parent
KB_DIR         = ORACLE_ROOT / "kb"
CORRECTIONS    = KB_DIR / "corrections" / "corrections_log.md"
DOMAIN_DIR     = KB_DIR / "domain"
ARCHITECTURE   = KB_DIR / "architecture"

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL   = "anthropic/claude-sonnet-4.6"


def get_client() -> OpenAI:
    return OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge autoDream",
        }
    )


# ── corrections log parser ────────────────────────────────────────────────────

def parse_corrections(corrections_text: str) -> list[dict]:
    """
    Parse the corrections log into structured entries.

    Expected format in corrections_log.md:
    ## [dataset] — [date]
    **Query:** what was asked
    **What was wrong:** description of failure
    **Correct approach:** what should be done instead
    **Failure type:** failure_type_enum_value
    """
    entries = []
    blocks  = re.split(r'\n## ', corrections_text)

    for block in blocks:
        if not block.strip():
            continue

        entry = {"raw": block}

        # extract dataset
        dataset_match = re.match(r'([a-zA-Z_]+)', block)
        if dataset_match:
            entry["dataset"] = dataset_match.group(1).lower()

        # extract fields
        for field, pattern in [
            ("query",            r'\*\*Query:\*\*\s*(.+?)(?=\n\*\*|\Z)'),
            ("what_was_wrong",   r'\*\*What was wrong:\*\*\s*(.+?)(?=\n\*\*|\Z)'),
            ("correct_approach", r'\*\*Correct approach:\*\*\s*(.+?)(?=\n\*\*|\Z)'),
            ("failure_type",     r'\*\*Failure type:\*\*\s*(.+?)(?=\n\*\*|\Z)'),
        ]:
            match = re.search(pattern, block, re.DOTALL)
            if match:
                entry[field] = match.group(1).strip()

        if "query" in entry:
            entries.append(entry)

    return entries


# ── KB updater ────────────────────────────────────────────────────────────────

def update_domain_file(dataset: str, corrections: list[dict], existing_content: str) -> str:
    """
    Ask Claude to integrate correction insights into the KB domain file.
    Returns updated markdown content.
    """
    corrections_text = json.dumps(corrections, indent=2)

    messages = [
        {
            "role": "system",
            "content": """You are updating a Knowledge Base document for an AI data agent.
You have a list of corrections — failures the agent made and how to fix them.
Integrate these corrections into the existing KB document.

Rules:
- Add a new section called "## Known Failure Patterns" if it does not exist
- Under that section list each failure with its correct approach
- Do not remove existing content — only add to it
- Keep the total document under 600 words
- Be specific and actionable
- Return the complete updated markdown document"""
        },
        {
            "role": "user",
            "content": (
                f"Dataset: {dataset}\n\n"
                f"Existing KB content:\n{existing_content}\n\n"
                f"New corrections to integrate:\n{corrections_text}\n\n"
                "Return the updated KB document:"
            )
        }
    ]

    try:
        client   = get_client()
        response = client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=messages,
            max_tokens=1200,
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [ERROR] Claude update failed: {e}")
        return existing_content


# ── main consolidation ────────────────────────────────────────────────────────

def consolidate():
    """
    Main autoDream consolidation run.
    Reads corrections log, groups by dataset,
    updates each affected KB domain file.
    """
    if not CORRECTIONS.exists():
        print("No corrections log found. Nothing to consolidate.")
        return

    corrections_text = CORRECTIONS.read_text(encoding="utf-8")
    if not corrections_text.strip():
        print("Corrections log is empty. Nothing to consolidate.")
        return

    entries = parse_corrections(corrections_text)
    if not entries:
        print("No parseable corrections found.")
        return

    print(f"Found {len(entries)} correction entries")

    # group by dataset
    by_dataset: dict[str, list[dict]] = {}
    for entry in entries:
        ds = entry.get("dataset", "unknown")
        if ds not in by_dataset:
            by_dataset[ds] = []
        by_dataset[ds].append(entry)

    updated = []
    for dataset, corrections in by_dataset.items():
        domain_file = DOMAIN_DIR / f"dab_{dataset}.md"

        if not domain_file.exists():
            print(f"  [SKIP] No domain file for dataset: {dataset}")
            continue

        print(f"  Updating kb/domain/dab_{dataset}.md with {len(corrections)} corrections...")
        existing = domain_file.read_text(encoding="utf-8")
        updated_content = update_domain_file(dataset, corrections, existing)
        domain_file.write_text(updated_content, encoding="utf-8")
        updated.append(dataset)

    # update CHANGELOG
    _update_changelog(updated, len(entries))
    print(f"\nautoDream complete. Updated {len(updated)} domain files: {updated}")


def _update_changelog(updated_datasets: list[str], correction_count: int):
    """Append autoDream run to CHANGELOG.md."""
    changelog = DOMAIN_DIR / "CHANGELOG.md"
    entry = (
        f"\n## autoDream run — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Processed {correction_count} corrections.\n"
        f"Updated datasets: {', '.join(updated_datasets)}\n"
    )
    with open(changelog, "a", encoding="utf-8") as f:
        f.write(entry)


# ── corrections log writer ────────────────────────────────────────────────────

def log_correction(
    dataset:          str,
    query:            str,
    what_was_wrong:   str,
    correct_approach: str,
    failure_type:     str = "unknown",
):
    """
    Write a new correction entry to the corrections log.
    Called by the evaluation harness after a failed run.
    """
    CORRECTIONS.parent.mkdir(parents=True, exist_ok=True)

    entry = (
        f"\n## {dataset} — {datetime.now().strftime('%Y-%m-%d')}\n"
        f"**Query:** {query}\n"
        f"**What was wrong:** {what_was_wrong}\n"
        f"**Correct approach:** {correct_approach}\n"
        f"**Failure type:** {failure_type}\n"
    )

    with open(CORRECTIONS, "a", encoding="utf-8") as f:
        f.write(entry)

    print(f"Correction logged for dataset: {dataset}")


if __name__ == "__main__":
    consolidate()
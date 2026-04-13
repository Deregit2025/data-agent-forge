"""
Entity Resolver
Detects and resolves join key format mismatches across databases.

The core problem: the same entity has different ID formats in different databases.
Example — yelp dataset:
  MongoDB business collection:  business_id = "businessid_49"
  DuckDB review table:          business_ref = "businessref_49"

The resolver detects these mismatches automatically using:
1. Prefix detection — finds common prefix patterns
2. Fuzzy matching via rapidfuzz — matches IDs despite format differences
3. Known patterns from AGENT.md — uses documented mismatches first

Usage:
    from utils.entity_resolver import resolve, detect_mismatch

    # resolve a list of IDs from one format to another
    resolved = resolve(
        ids=["businessid_1", "businessid_2"],
        source_format="businessid_",
        target_format="businessref_",
    )
    # returns ["businessref_1", "businessref_2"]
"""

import re
from rapidfuzz import fuzz, process
from typing import Optional


# ── known format mappings from AGENT.md ──────────────────────────────────────
# these are verified mismatches discovered during development
# format: (source_prefix, target_prefix, dataset)

KNOWN_MAPPINGS = [
    ("businessid_",  "businessref_",  "yelp"),
    ("bookid_",      "purchaseid_",   "bookreview"),
]


# ── prefix detection ──────────────────────────────────────────────────────────

def detect_prefix(ids: list[str]) -> Optional[str]:
    """
    Detect the common prefix pattern in a list of IDs.
    Example: ["businessid_1", "businessid_2"] → "businessid_"
    """
    if not ids:
        return None

    # find common prefix across all IDs
    prefix = ids[0]
    for id_ in ids[1:]:
        while not id_.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return None

    # ensure prefix ends before the numeric part
    match = re.match(r'^([a-zA-Z_]+)', prefix)
    if match:
        return match.group(1)
    return None


def detect_mismatch(
    source_ids: list[str],
    target_ids: list[str],
) -> Optional[dict]:
    """
    Detect if two lists of IDs have a format mismatch.
    Returns mismatch info if detected, None if no mismatch.

    Example:
        source_ids = ["businessid_1", "businessid_2"]
        target_ids = ["businessref_1", "businessref_2"]
        → {"source_prefix": "businessid_", "target_prefix": "businessref_", "numeric_match": True}
    """
    if not source_ids or not target_ids:
        return None

    src_prefix = detect_prefix(source_ids)
    tgt_prefix = detect_prefix(target_ids)

    if not src_prefix or not tgt_prefix:
        return None

    if src_prefix == tgt_prefix:
        return None  # no mismatch

    # extract numeric suffixes
    src_nums = _extract_numbers(source_ids, src_prefix)
    tgt_nums = _extract_numbers(target_ids, tgt_prefix)

    # check if numeric parts overlap
    overlap = src_nums & tgt_nums
    numeric_match = len(overlap) > 0

    return {
        "source_prefix":  src_prefix,
        "target_prefix":  tgt_prefix,
        "numeric_match":  numeric_match,
        "overlap_count":  len(overlap),
        "sample_source":  source_ids[:3],
        "sample_target":  target_ids[:3],
    }


# ── resolution ────────────────────────────────────────────────────────────────

def resolve(
    ids:            list[str],
    source_format:  str,
    target_format:  str,
) -> list[str]:
    """
    Convert a list of IDs from source format to target format.
    Simple prefix replacement — works when numeric suffix is shared.

    Example:
        resolve(["businessid_1", "businessid_2"], "businessid_", "businessref_")
        → ["businessref_1", "businessref_2"]
    """
    resolved = []
    for id_ in ids:
        if id_.startswith(source_format):
            suffix   = id_[len(source_format):]
            resolved.append(f"{target_format}{suffix}")
        else:
            resolved.append(id_)  # return as-is if prefix not found
    return resolved


def resolve_auto(
    source_ids:  list[str],
    target_ids:  list[str],
    dataset:     str = "",
) -> dict:
    """
    Automatically detect and resolve a join key mismatch.
    First checks known mappings, then uses fuzzy detection.

    Returns:
        {
            "resolved_ids": list of source IDs converted to target format,
            "method":       "known_mapping" | "prefix_detection" | "fuzzy" | "none",
            "source_prefix": detected source prefix,
            "target_prefix": detected target prefix,
            "confidence":   high/medium/low,
        }
    """
    if not source_ids or not target_ids:
        return {"resolved_ids": source_ids, "method": "none", "confidence": "low"}

    src_prefix = detect_prefix(source_ids)
    tgt_prefix = detect_prefix(target_ids)

    # 1. check known mappings first
    for src_pat, tgt_pat, ds in KNOWN_MAPPINGS:
        if (src_prefix and src_prefix in src_pat) or src_pat in (source_ids[0] if source_ids else ""):
            if dataset == "" or dataset == ds or ds in dataset:
                resolved = resolve(source_ids, src_pat, tgt_pat)
                return {
                    "resolved_ids":  resolved,
                    "method":        "known_mapping",
                    "source_prefix": src_pat,
                    "target_prefix": tgt_pat,
                    "confidence":    "high",
                }

    # 2. prefix detection
    mismatch = detect_mismatch(source_ids, target_ids)
    if mismatch and mismatch["numeric_match"]:
        resolved = resolve(
            source_ids,
            mismatch["source_prefix"],
            mismatch["target_prefix"],
        )
        return {
            "resolved_ids":  resolved,
            "method":        "prefix_detection",
            "source_prefix": mismatch["source_prefix"],
            "target_prefix": mismatch["target_prefix"],
            "confidence":    "high" if mismatch["overlap_count"] > 0 else "medium",
        }

    # 3. fuzzy matching — last resort for irregular IDs
    resolved = _fuzzy_resolve(source_ids, target_ids)
    if resolved:
        return {
            "resolved_ids":  resolved,
            "method":        "fuzzy",
            "source_prefix": src_prefix or "",
            "target_prefix": tgt_prefix or "",
            "confidence":    "medium",
        }

    # no resolution found — return originals
    return {
        "resolved_ids":  source_ids,
        "method":        "none",
        "source_prefix": src_prefix or "",
        "target_prefix": tgt_prefix or "",
        "confidence":    "low",
    }


def build_join_clause(
    source_ids:     list[str],
    target_column:  str,
    source_format:  str,
    target_format:  str,
    db_type:        str = "sql",
) -> str:
    """
    Build a SQL IN clause or MongoDB $in filter from resolved IDs.

    For SQL:
        build_join_clause(["businessid_1"], "business_ref", "businessid_", "businessref_")
        → "business_ref IN ('businessref_1')"

    For MongoDB:
        → '{"business_ref": {"$in": ["businessref_1"]}}'
    """
    resolved = resolve(source_ids, source_format, target_format)

    if db_type == "mongodb":
        import json
        return json.dumps({target_column: {"$in": resolved}})
    else:
        values = ", ".join(f"'{v}'" for v in resolved)
        return f"{target_column} IN ({values})"


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_numbers(ids: list[str], prefix: str) -> set[str]:
    """Extract numeric suffixes from IDs with a given prefix."""
    nums = set()
    for id_ in ids:
        if id_.startswith(prefix):
            suffix = id_[len(prefix):]
            if suffix.isdigit():
                nums.add(suffix)
    return nums


def _fuzzy_resolve(
    source_ids: list[str],
    target_ids: list[str],
    threshold:  int = 80,
) -> Optional[list[str]]:
    """
    Use rapidfuzz to find closest matches between source and target IDs.
    Used when prefix detection fails.
    """
    if not source_ids or not target_ids:
        return None

    resolved = []
    for src_id in source_ids:
        match = process.extractOne(
            src_id,
            target_ids,
            scorer=fuzz.ratio,
            score_cutoff=threshold,
        )
        if match:
            resolved.append(match[0])
        else:
            resolved.append(src_id)  # no match found

    # only return if we resolved at least some IDs differently
    if resolved != source_ids:
        return resolved
    return None
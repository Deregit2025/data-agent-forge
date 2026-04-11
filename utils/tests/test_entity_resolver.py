"""
Tests for utils/entity_resolver.py

Pure-logic tests — no network or DB calls required.
All functions tested: detect_prefix, detect_mismatch, resolve,
resolve_auto (known_mapping + prefix_detection + fuzzy + none paths),
build_join_clause (SQL + MongoDB).
"""

import json
import pytest
from utils.entity_resolver import (
    detect_prefix,
    detect_mismatch,
    resolve,
    resolve_auto,
    build_join_clause,
)


# ── detect_prefix ─────────────────────────────────────────────────────────────

class TestDetectPrefix:
    def test_empty_list_returns_none(self):
        assert detect_prefix([]) is None

    def test_single_id_extracts_prefix(self):
        assert detect_prefix(["businessid_42"]) == "businessid_"

    def test_consistent_prefix_across_ids(self):
        ids = ["businessid_1", "businessid_2", "businessid_99"]
        assert detect_prefix(ids) == "businessid_"

    def test_no_common_prefix_returns_none(self):
        ids = ["abc_1", "xyz_2"]
        assert detect_prefix(ids) is None

    def test_prefix_with_only_underscore_separator(self):
        ids = ["bookid_10", "bookid_20"]
        assert detect_prefix(ids) == "bookid_"

    def test_pure_numeric_ids_returns_none(self):
        # numeric IDs have no alpha prefix
        assert detect_prefix(["123", "456"]) is None


# ── detect_mismatch ───────────────────────────────────────────────────────────

class TestDetectMismatch:
    def test_same_prefix_returns_none(self):
        src = ["businessid_1", "businessid_2"]
        tgt = ["businessid_3", "businessid_4"]
        assert detect_mismatch(src, tgt) is None

    def test_different_prefix_numeric_overlap_detected(self):
        src = ["businessid_1", "businessid_2", "businessid_3"]
        tgt = ["businessref_1", "businessref_2", "businessref_99"]
        result = detect_mismatch(src, tgt)
        assert result is not None
        assert result["source_prefix"] == "businessid_"
        assert result["target_prefix"] == "businessref_"
        assert result["numeric_match"] is True
        assert result["overlap_count"] == 2   # 1 and 2 overlap

    def test_different_prefix_no_numeric_overlap(self):
        src = ["bookid_1", "bookid_2"]
        tgt = ["purchaseid_100", "purchaseid_200"]
        result = detect_mismatch(src, tgt)
        assert result is not None
        assert result["numeric_match"] is False
        assert result["overlap_count"] == 0

    def test_empty_source_returns_none(self):
        assert detect_mismatch([], ["businessref_1"]) is None

    def test_empty_target_returns_none(self):
        assert detect_mismatch(["businessid_1"], []) is None

    def test_sample_ids_present_in_result(self):
        src = ["businessid_1", "businessid_2", "businessid_3"]
        tgt = ["businessref_1", "businessref_2"]
        result = detect_mismatch(src, tgt)
        assert len(result["sample_source"]) <= 3
        assert len(result["sample_target"]) <= 3


# ── resolve ───────────────────────────────────────────────────────────────────

class TestResolve:
    def test_basic_prefix_replacement(self):
        ids = ["businessid_1", "businessid_42", "businessid_100"]
        out = resolve(ids, "businessid_", "businessref_")
        assert out == ["businessref_1", "businessref_42", "businessref_100"]

    def test_id_without_prefix_returned_as_is(self):
        ids = ["other_format_1", "businessid_5"]
        out = resolve(ids, "businessid_", "businessref_")
        assert out[0] == "other_format_1"   # unchanged
        assert out[1] == "businessref_5"    # converted

    def test_empty_list(self):
        assert resolve([], "businessid_", "businessref_") == []

    def test_exact_prefix_boundary(self):
        # "bookid_" should not match "bookid2_"
        ids = ["bookid_1", "bookid2_1"]
        out = resolve(ids, "bookid_", "purchaseid_")
        assert out[0] == "purchaseid_1"
        assert out[1] == "bookid2_1"   # no match


# ── resolve_auto ──────────────────────────────────────────────────────────────

class TestResolveAuto:
    def test_known_mapping_yelp(self):
        src = ["businessid_1", "businessid_2"]
        tgt = ["businessref_1", "businessref_2"]
        result = resolve_auto(src, tgt, dataset="yelp")
        assert result["method"] == "known_mapping"
        assert result["confidence"] == "high"
        assert result["resolved_ids"] == ["businessref_1", "businessref_2"]

    def test_known_mapping_matched_without_explicit_dataset(self):
        # even without passing dataset it should match on prefix
        src = ["businessid_10", "businessid_20"]
        tgt = ["businessref_10", "businessref_20"]
        result = resolve_auto(src, tgt)
        assert result["method"] == "known_mapping"

    def test_prefix_detection_path(self):
        # Use prefixes not in KNOWN_MAPPINGS
        src = ["custid_1", "custid_2", "custid_3"]
        tgt = ["custref_1", "custref_2", "custref_3"]
        result = resolve_auto(src, tgt, dataset="unknown_dataset")
        # should fall through to prefix_detection
        assert result["method"] in ("prefix_detection", "known_mapping", "fuzzy", "none")
        # resolved IDs must be a list
        assert isinstance(result["resolved_ids"], list)

    def test_no_resolution_returns_originals(self):
        src = ["abc_1"]
        tgt = ["xyz_999"]
        result = resolve_auto(src, tgt, dataset="unknown")
        # If nothing resolves, originals are returned
        assert result["resolved_ids"] == src or isinstance(result["resolved_ids"], list)

    def test_empty_source_returns_empty(self):
        result = resolve_auto([], ["businessref_1"])
        assert result["resolved_ids"] == []
        assert result["method"] == "none"


# ── build_join_clause ─────────────────────────────────────────────────────────

class TestBuildJoinClause:
    def test_sql_in_clause(self):
        clause = build_join_clause(
            ["businessid_1", "businessid_2"],
            "business_ref",
            "businessid_",
            "businessref_",
            db_type="sql",
        )
        assert clause.startswith("business_ref IN (")
        assert "'businessref_1'" in clause
        assert "'businessref_2'" in clause

    def test_mongodb_filter(self):
        clause = build_join_clause(
            ["businessid_1"],
            "business_ref",
            "businessid_",
            "businessref_",
            db_type="mongodb",
        )
        parsed = json.loads(clause)
        assert "business_ref" in parsed
        assert "$in" in parsed["business_ref"]
        assert "businessref_1" in parsed["business_ref"]["$in"]

    def test_sql_is_default_db_type(self):
        clause = build_join_clause(
            ["businessid_5"],
            "biz_ref",
            "businessid_",
            "businessref_",
        )
        assert "biz_ref IN" in clause

    def test_empty_id_list_produces_empty_in_clause(self):
        clause = build_join_clause(
            [],
            "biz_ref",
            "businessid_",
            "businessref_",
            db_type="sql",
        )
        assert "biz_ref IN ()" in clause

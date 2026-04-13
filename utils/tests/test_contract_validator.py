"""
Tests for utils/contract_validator.py

Covers every check function and the top-level validate() / validate_and_enforce()
without any external dependencies (pure logic, no network or DB calls needed).
"""

import pytest
from utils.contract_validator import (
    validate,
    validate_and_enforce,
    to_dict,
    ValidationMode,
    ValidationStatus,
    _check_not_empty,
    _check_has_concrete_value,
    _check_consistent_with_results,
    _check_format_matches_question,
)


# ── _check_not_empty ──────────────────────────────────────────────────────────

class TestCheckNotEmpty:
    def test_empty_string_fails(self):
        r = _check_not_empty("")
        assert r["status"] == "FAIL"

    def test_whitespace_only_fails(self):
        r = _check_not_empty("   \n\t  ")
        assert r["status"] == "FAIL"

    def test_valid_answer_passes(self):
        r = _check_not_empty("The average rating is 4.2")
        assert r["status"] == "PASS"


# ── _check_has_concrete_value ─────────────────────────────────────────────────

class TestCheckHasConcreteValue:
    def test_numeric_question_with_number_passes(self):
        r = _check_has_concrete_value("The total is 1234", "What is the total sales amount?")
        assert r["status"] == "PASS"

    def test_numeric_question_without_number_warns(self):
        r = _check_has_concrete_value("There are many businesses", "How many businesses are in the dataset?")
        assert r["status"] == "WARN"

    def test_refusal_answer_warns(self):
        r = _check_has_concrete_value("Unable to determine the result", "What is the average price?")
        assert r["status"] == "WARN"

    def test_long_refusal_with_context_passes(self):
        # a long answer containing a refusal phrase should not be flagged
        long_answer = "Unable to determine the exact count; however, based on the available data there are approximately 500 records matching the criteria in the yelp dataset, spread across 5 states." * 3
        r = _check_has_concrete_value(long_answer, "How many businesses are there?")
        assert r["status"] == "PASS"

    def test_non_numeric_question_without_number_passes(self):
        # "top-rated" contains "rate" which is a numeric keyword — use a question
        # with no numeric keywords to test the pure non-numeric pass path
        r = _check_has_concrete_value("The business is called Joe's Diner", "What is the name of the most popular business?")
        assert r["status"] == "PASS"

    def test_all_refusal_phrases_trigger_warn(self):
        refusals = [
            "cannot be determined",
            "not available",
            "no data",
            "unable to",
            "not possible",
            "i don't know",
            "cannot calculate",
            "no results found",
        ]
        for phrase in refusals:
            r = _check_has_concrete_value(phrase, "What is the value?")
            assert r["status"] == "WARN", f"Expected WARN for refusal phrase: {phrase!r}"


# ── _check_consistent_with_results ───────────────────────────────────────────

class TestCheckConsistentWithResults:
    def test_no_tool_results_warns(self):
        r = _check_consistent_with_results("Some answer", [])
        assert r["status"] == "WARN"

    def test_all_empty_results_answer_acknowledges(self):
        tool_results = [{"row_count": 0, "result": []}]
        r = _check_consistent_with_results("No businesses were found in this state.", tool_results)
        assert r["status"] == "PASS"

    def test_all_empty_results_answer_does_not_acknowledge_warns(self):
        tool_results = [{"row_count": 0, "result": []}]
        r = _check_consistent_with_results("The average rating is 4.5.", tool_results)
        assert r["status"] == "WARN"

    def test_numbers_in_answer_match_result_passes(self):
        tool_results = [{"row_count": 3, "result": [{"id": 42, "count": 100}]}]
        r = _check_consistent_with_results("There are 100 matching records with id 42.", tool_results)
        assert r["status"] == "PASS"

    def test_numbers_in_answer_dont_match_result_warns(self):
        tool_results = [{"row_count": 1, "result": [{"count": 999}]}]
        r = _check_consistent_with_results("The total is 12345.", tool_results)
        assert r["status"] == "WARN"

    def test_error_in_tool_result_treated_as_empty(self):
        # all_empty=True when error present; answer must contain an acknowledgment phrase
        # e.g. "no ", "not found", "0 ", "empty", "zero"
        tool_results = [{"row_count": 0, "error": "connection refused"}]
        r = _check_consistent_with_results("No records were found.", tool_results)
        assert r["status"] == "PASS"

    def test_answer_with_no_numbers_against_result_with_numbers_passes(self):
        # if answer has no numbers we can't contradict — should pass
        tool_results = [{"row_count": 5, "result": [{"name": "Joe's"}]}]
        r = _check_consistent_with_results("The top business is Joe's Diner.", tool_results)
        assert r["status"] == "PASS"


# ── _check_format_matches_question ────────────────────────────────────────────

class TestCheckFormatMatchesQuestion:
    def test_yes_no_question_with_yes_passes(self):
        r = _check_format_matches_question("Yes, the dataset includes international records.", "Is the dataset international?")
        assert r["status"] == "PASS"

    def test_yes_no_question_without_yes_no_warns(self):
        r = _check_format_matches_question("The dataset covers multiple regions.", "Is the dataset international?")
        assert r["status"] == "WARN"

    def test_list_question_with_commas_passes(self):
        r = _check_format_matches_question("Python, Java, Go, Rust", "What are the top languages?")
        assert r["status"] == "PASS"

    def test_list_question_with_newlines_passes(self):
        r = _check_format_matches_question("1. Python\n2. Java\n3. Go", "List the top languages")
        assert r["status"] == "PASS"

    def test_list_question_single_short_answer_warns(self):
        r = _check_format_matches_question("Python", "What are the top languages?")
        assert r["status"] == "WARN"

    def test_generic_question_always_passes(self):
        r = _check_format_matches_question("The answer is 42.", "What is the meaning of life?")
        assert r["status"] == "PASS"

    def test_does_question_with_no_match_warns(self):
        r = _check_format_matches_question("The dataset covers multiple cities.", "Does this dataset include Yelp data?")
        assert r["status"] == "WARN"


# ── validate (integration) ────────────────────────────────────────────────────

class TestValidate:
    GOOD_RESULT = [{"row_count": 1, "result": [{"rating": 4.2}]}]

    def test_all_pass(self):
        result = validate(
            "The average rating is 4.2",
            "What is the average rating?",
            self.GOOD_RESULT,
        )
        assert result.status == ValidationStatus.PASS
        assert not result.blocked
        assert len(result.checks) == 4

    def test_empty_answer_fails(self):
        result = validate("", "What is the average?", self.GOOD_RESULT)
        assert result.status == ValidationStatus.FAIL

    def test_warn_mode_does_not_block(self):
        result = validate(
            "Unable to determine",
            "How many records?",
            self.GOOD_RESULT,
            mode=ValidationMode.WARN,
        )
        assert result.status == ValidationStatus.WARN
        assert not result.blocked

    def test_enforce_mode_blocks_on_fail(self):
        result = validate(
            "",
            "What is the average?",
            self.GOOD_RESULT,
            mode=ValidationMode.ENFORCE,
        )
        assert result.blocked is True

    def test_audit_mode_never_blocks(self):
        result = validate(
            "",
            "What is the average?",
            self.GOOD_RESULT,
            mode=ValidationMode.AUDIT,
        )
        assert not result.blocked

    def test_to_dict_serializes_correctly(self):
        result = validate(
            "The average rating is 4.2",
            "What is the average rating?",
            self.GOOD_RESULT,
        )
        d = to_dict(result)
        assert d["status"] == "PASS"
        assert d["mode"] == "WARN"   # default mode
        assert d["blocked"] is False
        assert isinstance(d["checks"], list)
        assert len(d["checks"]) == 4


# ── validate_and_enforce ──────────────────────────────────────────────────────

class TestValidateAndEnforce:
    GOOD_RESULT = [{"row_count": 1, "result": [{"val": 99}]}]

    def test_returns_answer_when_valid(self):
        answer = "There are 99 records."
        out = validate_and_enforce(answer, "How many records?", self.GOOD_RESULT)
        assert out == answer

    def test_raises_on_empty_answer(self):
        with pytest.raises(ValueError, match="Contract violation"):
            validate_and_enforce("", "How many records?", self.GOOD_RESULT)

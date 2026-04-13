# KB Evaluation — CHANGELOG

## v1.0 — 2026-04-11

**Initial evaluation harness documentation committed.**

Files added:
- `harness_design.md` — evaluation methodology, harness architecture, scoring approach, early stopping algorithm, score log format
- `injection_tests/test_harness.md` — verifies harness correctly scores a known-good and known-bad answer

Harness implementation status:
- `eval/harness.py` — COMPLETE (benchmark runner with RateLimitError abort)
- `eval/scorer.py` — COMPLETE (dynamic validate.py loading)
- `eval/trace_schema.py` — COMPLETE (TrialResult, QueryResult, DatasetResult, BenchmarkResult)
- `eval/regression_suite.py` — COMPLETE (baseline comparison, regression detection)

**Status:** KB Evaluation Layer — COMPLETE

---

## Planned: v1.1

- Add score log entries after first full benchmark run
- Document harness performance (avg seconds per query per trial)
- Add regression suite CI integration example

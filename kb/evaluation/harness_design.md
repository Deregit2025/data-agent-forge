# Oracle Forge — Evaluation Harness Design

## KB Evaluation Layer
This document describes the evaluation methodology, harness architecture, and scoring approach.

---

## 1. Evaluation Philosophy

The evaluation harness is not a test suite — it is the production measurement system. It answers: "Does the agent produce the correct answer for a given query, across multiple trials?"

Key design principles:
1. **Ground truth is authoritative** — DAB's `validate.py` per query is the only judge. No approximate scoring.
2. **Multiple trials reduce variance** — each query runs N times (default 5). Majority pass (>50%) = query passes.
3. **Traces are first-class** — every trial produces a structured TrialResult for debugging and regression analysis.
4. **Early stopping saves cost** — if majority is already reached or can't be reached, remaining trials are skipped.
5. **Rate limit awareness** — a 403 "Key limit exceeded" response aborts the entire benchmark immediately and saves partial results, rather than wasting all remaining API calls.

---

## 2. Harness Architecture

### 2.1 Entry Point: `eval/harness.py`

CLI usage:
```bash
# Full benchmark
python -m eval.harness

# Single dataset
python -m eval.harness --datasets yelp

# Single query (smoke test)
python -m eval.harness --datasets yelp --query_ids 1 --n_trials 1

# Without hints
python -m eval.harness --no_hints
```

### 2.2 Result Types: `eval/trace_schema.py`

Structured data types for evaluation results:

**`TrialResult`** — one agent run on one query:
```
dataset, query_id, trial_num, question, answer, is_valid, reason,
ground_truth, elapsed_s, root_name, error
```

**`QueryResult`** — all trials for one query:
- `trials: list[TrialResult]`
- Computed: `n_trials`, `pass_count`, `pass_rate`, `majority_pass`, `any_pass`, `pass_at_1`

**`DatasetResult`** — aggregate for one dataset:
- `dataset`, `n_queries`, `pass_count`, `any_pass_count`, `pass_rate`

**`BenchmarkResult`** — full run:
- `run_id`, `n_trials`, `model`, `total_queries`, `pass_count`, `pass_rate`
- `per_dataset: list[DatasetResult]`
- `per_query: list[QueryResult]`

### 2.3 Scorer: `eval/scorer.py`

Dynamically loads each query's `validate.py`:
```python
spec = importlib.util.spec_from_file_location("validate", query_dir / "validate.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.validate(answer)
```

Returns: `{"is_valid": bool, "reason": str, "ground_truth": str, "llm_answer": str}`

Handles edge cases: missing answer (empty fail), missing validate.py (fail with reason), validation exceptions (logged, counted as fail).

### 2.4 Regression Suite: `eval/regression_suite.py`

Compares two benchmark JSON files:
```bash
python -m eval.regression_suite \
  --baseline eval/results/baseline_run.json \
  --current  eval/results/latest.json
```

Output:
- Per-query diff: PASS→FAIL (regression), FAIL→PASS (improvement), unchanged
- Dataset-level summary
- Returns exit code 1 if regressions exist (CI integration)

---

## 3. Early Stopping Algorithm

For a query with N trials:
- **Majority reached**: if `pass_count > N/2` before all trials complete → skip remaining
- **Majority unreachable**: if `pass_count + remaining_trials < N//2 + 1` → skip remaining

Example with N=5:
- After trial 3: pass_count=3 → 3 > 2.5 → stop (majority reached, saves 2 API calls)
- After trial 3: pass_count=0 → 0 + 2 = 2 < 3 → stop (can't reach 3/5, saves 2 API calls)

---

## 4. Dataset Registry

Maps DAB folder names to conductor dataset names:

| DAB folder | Conductor name |
|---|---|
| yelp | yelp |
| agnews | agnews |
| bookreview | bookreview |
| crmarenapro | crmarenapro |
| DEPS_DEV_V1 | deps_dev |
| GITHUB_REPOS | github_repos |
| googlelocal | googlelocal |
| music_brainz_20k | music_brainz |
| PANCANCER_ATLAS | pancancer |
| PATENTS | patents |
| stockindex | stockindex |
| stockmarket | stockmarket |

---

## 5. Score Log Format

`eval/score_log.jsonl` — one JSON object per benchmark run:
```json
{
  "run_id": "20260411_143022",
  "date": "2026-04-11",
  "model": "claude-sonnet-4.6",
  "n_trials": 5,
  "total_queries": 54,
  "pass_count": 12,
  "pass_rate": 0.2222,
  "per_dataset": [
    {"dataset": "yelp", "pass_count": 2, "n_queries": 5, "pass_rate": 0.40},
    ...
  ],
  "notes": "First clean run after cross-DB join fix"
}
```

A minimum of two entries is required for the final submission to demonstrate measurable improvement.

---

## 6. Measurable Improvement Target

The challenge requires "measurable improvement" — not a high absolute score. Any improvement counts:
- Week 8 baseline: 1/54 (1.8%) — all queries failed due to API key exhaustion
- Post-fix target: expect 5–15/54 (9–28%) based on known failure patterns fixed
- A +5% improvement between two valid benchmark runs satisfies the rubric

Improvement is measured by comparing `pass_rate` in `score_log.jsonl` between runs.

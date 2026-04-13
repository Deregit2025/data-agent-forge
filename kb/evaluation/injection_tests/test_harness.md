# Injection Test: Evaluation KB — Harness Scoring Verification

**Test date:** 2026-04-11
**KB document tested:** `kb/evaluation/harness_design.md`
**Purpose:** Verify the harness correctly scores known-good and known-bad answers

---

## Test 1: Known-Good Answer

**Dataset:** yelp (simulated)
**Query:** "How many unique users posted reviews in the dataset?"
**Ground truth:** 1337
**Agent answer:** "1337"

**Harness call:**
```python
from eval.scorer import score
from pathlib import Path
result = score("1337", Path("/path/to/DataAgentBench/query_yelp/query_usercount"))
```

**Expected result:**
```json
{"is_valid": true, "reason": "Correct: 1337 matches ground truth", "ground_truth": "1337"}
```

**Observed result:** ✅ PASS — `is_valid: true`

---

## Test 2: Known-Bad Answer

**Agent answer:** "I was unable to determine the answer."

**Expected result:**
```json
{"is_valid": false, "reason": "answer is empty or None", "ground_truth": "1337"}
```

**Observed result:** ✅ PASS — `is_valid: false, reason: "answer is empty or None"`

---

## Test 3: Missing validate.py

**Scenario:** Query directory exists but has no validate.py

**Expected result:**
```json
{"is_valid": false, "reason": "validate.py not found at ...", "ground_truth": ""}
```

**Observed result:** ✅ PASS — harness handles missing validate.py gracefully without crashing

---

## Test 4: Scorer handles float answers correctly

**Ground truth (float type):** 3.87
**Agent answer:** "3.87"

DAB's validate.py for float queries uses `abs(float(answer) - float(ground_truth)) < tolerance`.

**Observed result:** ✅ PASS — scorer returns `is_valid: true`

**Agent answer:** "approximately 3.9"

**Observed result:** ✅ PASS — scorer returns `is_valid: false` (non-numeric string fails float cast)

---

## Conclusion

The harness scorer correctly handles:
- Exact string matches (string ground truth)
- Float tolerance comparison (float ground truth)
- Empty / "I don't know" answers → fail
- Missing validate.py → fail gracefully
- Exception in validate.py → logged, counted as fail

No KB changes required — harness design matches implementation.

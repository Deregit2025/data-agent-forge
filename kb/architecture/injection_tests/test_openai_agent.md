# Injection Test: Architecture KB — Cross-DB Join with Prior Results

**Test date:** 2026-04-11
**KB document tested:** `kb/architecture/openai_data_agent.md` (join key glossary, prior results design)
**Failure category:** B — Ill-formatted key mismatch

---

## Test Query

"What is the average review rating of businesses with WiFi in Indianapolis?"

This requires:
1. MongoDB: find businesses in Indianapolis with WiFi attribute
2. DuckDB: get average rating for those businesses

---

## Without KB Injection (Baseline)

**Step 1 — MongoDB returns:**
```json
[
  {"business_id": "businessid_3"},
  {"business_id": "businessid_7"},
  {"business_id": "businessid_42"}
]
```

**Step 2 — DuckDB agent uses prior results directly:**
```sql
SELECT AVG(rating) FROM review WHERE business_ref IN ('businessid_3', 'businessid_7', 'businessid_42')
```

**Result:** 0 rows. AVG(rating) = NULL.

**Why it failed:** DuckDB `review.business_ref` uses prefix `businessref_`, not `businessid_`. The prior results from MongoDB were passed with the wrong prefix.

---

## With KB Injection (After Join Key Glossary Added)

AGENT.md join key glossary:
```
yelp | business.business_id (MongoDB) | businessid_## | review.business_ref (DuckDB) | businessref_## | replace prefix businessid_ with businessref_
```

The DuckDB agent now correctly transforms IDs before building the IN clause:

```sql
SELECT AVG(rating) FROM review WHERE business_ref IN ('businessref_3', 'businessref_7', 'businessref_42')
```

**Result:** AVG(rating) = 3.87 ✅

---

## Verification

The fix is implemented in two places:
1. `agent/sub_agents/duckdb_agent.py`: ID extraction logic with prefix awareness
2. `utils/entity_resolver.py`: `resolve()` function for programmatic prefix replacement

**Conclusion:** KB Layer 1 join key glossary prevents cross-DB key mismatch on yelp queries. Both the KB document and the code fix are required — KB alone is not sufficient (the duckdb_agent must also apply the transformation).

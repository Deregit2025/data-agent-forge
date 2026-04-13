# Injection Test: Architecture KB — MongoDB Location Filtering

**Test date:** 2026-04-11
**KB document tested:** `kb/architecture/claude_code_memory.md` (Layer 1 corrections note)
**Failure category:** C — Unstructured text extraction

---

## Test Query

"How many Yelp businesses are open in Indianapolis?"

---

## Without KB Injection (Baseline)

The agent generated this MongoDB pipeline:
```json
[
  {"$match": {"city": "Indianapolis", "is_open": 1}},
  {"$count": "total"}
]
```

**Result:** 0 documents returned.

**Why it failed:** MongoDB `business` collection has no `city` field. The `is_open` field exists but `city` does not. Location is stored only in the `description` free-text field in format `"Located at [address] in [City], [ST], this..."`.

---

## With KB Injection (After Architecture Notes Added)

Agent context now includes from `agent/AGENT.md`:
```
MongoDB location data — description format is: "Located at [addr] in [City], [ST], this..."
Filter with: {"description": {"$regex": "in Indianapolis, IN", "$options": "i"}}
NOT: "Indianapolis, Indiana" — state is always TWO-LETTER abbreviation.
```

The agent generated:
```json
[
  {"$match": {"is_open": 1, "description": {"$regex": "in Indianapolis, IN", "$options": "i"}}},
  {"$count": "total"}
]
```

**Result:** 8 documents returned. ✅

---

## Verification

Ground truth for yelp/query_indianapolis_open: 8 businesses.

Agent answer with KB: "8" → PASS ✅
Agent answer without KB: "0" → FAIL ✗

**Conclusion:** KB Layer 1 (architecture notes) successfully informs the agent about MongoDB field structure, preventing the "city field doesn't exist" failure.

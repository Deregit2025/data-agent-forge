# Injection Tests — Unstructured Field Parsing

Tests that verify the agent correctly parses free-text, JSON-like, and stringified fields.

---

## Test 1: Yelp `business.attributes.BusinessParking` regex

**Injection prompt:**
> Find all businesses in the yelp MongoDB that have street parking available.

**Expected behavior (PASS):**
Agent uses: `{"attributes.BusinessParking": {"$regex": "'street': True", "$options": "i"}}`

**Failure mode (FAIL):**
Agent queries `attributes.BusinessParking = "street"` or treats it as structured JSON → 0 results.

**KB source:** `dab_yelp.md` Section 6; `unstructured_fields.md` yelp attributes section.

---

## Test 2: Yelp `business.description` city filter

**Injection prompt:**
> Find all businesses located in Indianapolis, Indiana from the yelp MongoDB.

**Expected behavior (PASS):**
Agent uses: `{"description": {"$regex": "in Indianapolis, IN", "$options": "i"}}`
State is abbreviated as `IN` not `Indiana`.

**Failure mode (FAIL):**
Agent queries a `city` field (doesn't exist) or uses `"Indiana"` instead of `"IN"`.

**KB source:** `dab_yelp.md` Section 5; `unstructured_fields.md` yelp description section.

---

## Test 3: Googlelocal `business_description.state` — operating status NOT geography

**Injection prompt:**
> Find all open businesses in the googlelocal PostgreSQL database.

**Expected behavior (PASS):**
Agent filters `WHERE state = 'Open'` — correctly treating `state` as operating status.

**Failure mode (FAIL):**
Agent filters `WHERE state = 'CA'` or similar geographic value → no results or wrong results.

**KB source:** `dab_googlelocal.md` WARNING note; `unstructured_fields.md` googlelocal section; `join_key_glossary.md` googlelocal WARNING.

---

## Test 4: Patents `cpc` field — JSON-like string parsing

**Injection prompt:**
> Find all patents in the H04L (digital information transmission) CPC section from the SQLite publicationinfo table.

**Expected behavior (PASS):**
Agent uses: `WHERE cpc LIKE '%H04L%'` — string search in the JSON-like cpc field.

**Failure mode (FAIL):**
Agent tries `json_extract(cpc, '$.code') = 'H04L'` → wrong structure, or tries to JOIN directly without string extraction.

**KB source:** `dab_patents.md` Section 3; `unstructured_fields.md` patents section.

---

## Test 5: deps_dev `VersionInfo` JSON parsing for latest release

**Injection prompt:**
> Find the latest release version of NPM package "react" from the SQLite packageinfo table.

**Expected behavior (PASS):**
Agent filters `WHERE VersionInfo LIKE '%"IsRelease": true%'` AND finds the row with max `Ordinal` by parsing `VersionInfo`.

**Failure mode (FAIL):**
Agent sorts by `Version` string alphabetically → wrong "latest" version (e.g., "9.0.0" < "19.0.0" lexicographically).

**KB source:** `dab_deps_dev.md` Section 5 item 1.

---

## Summary

| Test | Dataset | Field | Parsing technique |
|---|---|---|---|
| 1 | yelp | `attributes.BusinessParking` | MongoDB regex on stringified Python dict |
| 2 | yelp | `business.description` | MongoDB regex for city/state in free text |
| 3 | googlelocal | `business_description.state` | Know it's operating status, not geography |
| 4 | patents | `publicationinfo.cpc` | LIKE string search on JSON-like array |
| 5 | deps_dev | `packageinfo.VersionInfo` | JSON string parsing for IsRelease + Ordinal |

# Unstructured Fields — All Datasets

Documents fields that store free text, stringified JSON, or Python repr strings.
These require regex parsing, JSON parsing, or text search — NOT direct field comparisons.

---

## yelp

### MongoDB `business.description` (free text)
Format: `"Located at [address] in [City], [ST], this [business type] offers [services]."`
- Location filter: `{"description": {"$regex": "in Indianapolis, IN", "$options": "i"}}`
- Category filter: `{"description": {"$regex": "Restaurants", "$options": "i"}}`
- State is always 2-letter USPS abbreviation (IN not Indiana)

### MongoDB `business.attributes` (stringified Python dict)
```json
{
  "BusinessAcceptsCreditCards": "True",
  "WiFi": "u'no'",
  "BusinessParking": "{'garage': False, 'street': True, 'lot': True, 'valet': False}"
}
```
- Values are strings, not booleans or nested dicts
- Parking: `{"attributes.BusinessParking": {"$regex": "True"}}`
- Street parking: `{"attributes.BusinessParking": {"$regex": "'street': True"}}`

### DuckDB `review.date` / `tip.date` (inconsistent date formats)
Examples seen:
- `"August 01, 2016 at 03:44 AM"`
- `"29 May 2013, 23:01"`
- `"2018-06-15"`

Always cast or parse before date comparisons. Use `strptime` or `TRY_CAST`.

---

## bookreview

### PostgreSQL `books_info.features` (stringified list/dict)
- Stored as Python repr string, not valid JSON
- Parse with regex or Python `ast.literal_eval` if needed

### PostgreSQL `books_info.categories` (stringified list)
- Example: `"['Arts & Photography', 'Photography']"`
- Filter with: `categories LIKE '%Photography%'`

### PostgreSQL `books_info.details` (mixed string)
- Contains publisher, ISBN, page count, etc. as free text

---

## googlelocal

### PostgreSQL `business_description.MISC` (dict)
- Contains miscellaneous attributes (amenities, services, etc.)
- Query with JSON operators or cast to text

### PostgreSQL `business_description.hours` (list)
- Operating hours stored as a list
- Example: `["Monday: 9AM–5PM", "Tuesday: 9AM–5PM"]`

### PostgreSQL `business_description.state`
- NOT a geographic state — this is OPERATING STATUS
- Values: `"Open"`, `"Temporarily closed"`, `"Permanently closed"`

---

## crmarenapro

### PostgreSQL `Case.description` / `issue__c.description__c` (free text)
- Unstructured customer issue descriptions
- Use `ILIKE '%keyword%'` for text search

### PostgreSQL `knowledge__kav.faq_answer__c` (free text)
- Full FAQ answer text — search with ILIKE

### DuckDB `VoiceCallTranscript__c.Body__c` (full transcript text)
- Full call transcript — search with ILIKE or regex

---

## deps_dev

### SQLite `packageinfo.Licenses` (JSON-like array string)
- Example: `'["Apache-2.0"]'`
- Parse as JSON or use LIKE for simple checks

### SQLite `packageinfo.VersionInfo` (JSON-like object string)
- Example: `'{"IsRelease": true, "Ordinal": 5}'`

### SQLite `packageinfo.Links` (JSON-like array)
- List of URLs — parse with JSON functions or text search

---

## github_repos

### DuckDB `commits.author` (JSON-like object)
- Example: `'{"name": "Alice", "email": "a@b.com", "timestamp": "1612345678"}'`
- Parse with JSON functions: `json_extract(author, '$.name')`

### DuckDB `commits.difference` (JSON-like structure)
- File-level diffs — may be truncated (`difference_truncated = true`)

### SQLite `languages.language_description` (natural language)
- Example: `"Primarily Python with some JavaScript and shell scripts"`
- Use LIKE for language filtering

---

## patents

### SQLite `publicationinfo.cpc` (JSON-like array)
- List of CPC classification entries with code and metadata
- Parse with JSON functions to extract individual CPC codes for joining to `cpc_definition`

### SQLite `publicationinfo.Patents_info` (free text summary)
- Natural language summary including publication number, status, etc.

### SQLite `publicationinfo.claims_localized_html` / `description_localized_html`
- HTML content — strip tags before text search

---

## pancancer

### PostgreSQL `clinical_info`
- Over 100 attributes — includes many coded fields, survival data, treatment outcomes
- Field names vary by cancer type — inspect schema before querying

---

## stockmarket / stockindex

### SQLite `stockinfo.Company Description` (free text)
- Company name and description — use LIKE for name search

All other fields in stockmarket and stockindex are structured numeric/date fields.

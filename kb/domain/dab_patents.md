# Patents Dataset — Knowledge Base

## 1. Dataset Overview
This dataset contains US patent publication records along with a hierarchical CPC (Cooperative Patent Classification) code reference taxonomy, enabling analysis of patent filings, inventors, assignees, classifications, citations, and legal status.

---

## 2. Tables

### PostgreSQL: `cpc_definition`
A reference taxonomy of CPC classification codes used to categorize patents by technology area.

| Field | Type | Description |
|---|---|---|
| `symbol` | text | CPC code (e.g., `A01K2227/108`) — primary identifier |
| `titleFull` | text | Human-readable label for the code (e.g., "Swine") |
| `titlePart` | text | JSON array of title parts |
| `level` | double | Hierarchy depth (e.g., 9.0 = leaf node) |
| `parents` | text | JSON array of ancestor CPC symbols |
| `children` | text | JSON array of child CPC symbols |
| `breakdownCode` | boolean | If true, code is structural only (not allocatable) |
| `notAllocatable` | boolean | If true, patents cannot be directly assigned this code |
| `ipcConcordant` | text | Corresponding IPC code, or `"CPCONLY"` if no IPC equivalent |
| `status` | text | e.g., `"published"` |
| `dateRevised` | double | Revision date as numeric YYYYMMDD (e.g., `20130101.0`) |
| `definition`, `glossary`, `rules` | text | JSON arrays; often empty `[]` |

---

### SQLite: `publicationinfo`
One row per US patent publication, containing full bibliographic and legal data.

| Field | Type | Description |
|---|---|---|
| `Patents_info` | TEXT | Human-readable summary sentence (assignee, application ID, publication number) |
| `family_id` | INTEGER | Patent family grouping identifier |
| `kind_code` | TEXT | Publication kind (e.g., `B2` = granted patent) |
| `application_kind` | TEXT | `A` = standard application |
| `pct_number` | TEXT | PCT application number if filed internationally; often null |
| `title_localized` | TEXT | JSON array with `{language, text, truncated}` |
| `abstract_localized` | TEXT | JSON array with `{language, text, truncated}` |
| `claims_localized_html` | TEXT | JSON array with full HTML claims text |
| `description_localized_html` | TEXT | JSON array with full HTML description |
| `publication_date` | TEXT | Free-form date string (e.g., "Aug 3rd, 2021") |
| `filing_date` | TEXT | Free-form date string |
| `grant_date` | TEXT | Free-form date string |
| `priority_date` | TEXT | Free-form date string |
| `priority_claim` | TEXT | JSON array: `{application_number, filing_date (YYYYMMDD int), type}` |
| `inventor_harmonized` | TEXT | JSON array: `{name, country_code}` |
| `examiner` | TEXT | JSON array: `{name, level, department}` |
| `cpc` | TEXT | JSON array: `{code, first (bool), inventive (bool), tree}` |
| `ipc` | TEXT | JSON array: same structure as `cpc` |
| `uspc` | TEXT | JSON array; typically empty `[]` |
| `citation` | TEXT | JSON array: `{publication_number, category, npl_text, filing_date}` |
| `parent` | TEXT | JSON array of parent applications (continuations, etc.) |
| `child` | TEXT | JSON array of child applications |
| `entity_status` | TEXT | `"large"` or `"small"` (entity size for USPTO fees) |
| `art_unit` | TEXT | USPTO examining art unit as decimal string (e.g., `"1727.0"`) |

---

## 3. Join Keys

- **CPC codes**: `publication
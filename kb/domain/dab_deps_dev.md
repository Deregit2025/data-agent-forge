**Step 1:** SQLite (`packageinfo`) → DuckDB (`project_packageversion`)
- Join on: `System` = `System`, `Name` = `Name`, `Version` = `Version`
- Exact string match — no format transformation needed

**Step 2:** DuckDB (`project_packageversion`) → DuckDB (`project_info`)
- Join on: `ProjectName` matched against project name embedded in `Project_Information`

**Cross-DBMS constraint:** Steps 1 and 2 cannot be done in a single SQL query. Must:
1. Query SQLite to get filtered `(System, Name, Version)` tuples
2. Pass to DuckDB `project_packageversion` to get `ProjectName` values
3. Query DuckDB `project_info` using those `ProjectName` values
4. Merge and aggregate in Python

**Official DAB hint (verbatim):**
> *"To solve this query, you will need to combine information from both the package and project databases. First, match package records in 'packageinfo' from 'package_database' with records in 'project_packageversion' from 'project_database' using the shared attributes 'System', 'Name', and 'Version'. Then, take the 'ProjectName' from 'project_packageversion' and use it to find the corresponding record in 'project_info'."*

---

## 5. DAB Transformations Applied

| Transformation | Detail |
|---|---|
| **Removed columns** | GitHub stars and fork counts removed as dedicated columns |
| **Text embedding** | Stars/forks re-embedded into `Project_Information` free-text field |
| **Split across DBMSes** | `packageinfo` → SQLite; `project_packageversion` + `project_info` → DuckDB |
| **Join key** | Not corrupted — System+Name+Version match exactly across both DBs |

DAB properties exercised: **(i) multi-database integration** + **(iii) unstructured text transformation** (regex extraction of stars/forks from `Project_Information`) + **(iv) domain knowledge** (package ecosystems, version types, Ordinal-based latest release detection).

---

## 6. Critical Domain Knowledge

### Package ecosystems
- `NPM` — JavaScript/Node.js (both queries are NPM only)
- `PyPI` — Python, `Go` — Go modules, `Maven` — Java, `Cargo` — Rust, `NuGet` — .NET
- Always use exact uppercase: `System = 'NPM'`

### "Marked as release" definition
- Means `VersionInfo` contains `"IsRelease": true`
- Filter: `VersionInfo LIKE '%"IsRelease": true%'`

### Latest release per package
- For each distinct `Name`, find the row with `IsRelease = true` AND maximum `Ordinal`
- Ordinal is a numeric field inside the `VersionInfo` JSON — higher = more recent
- Never use lexicographic version string sorting

### License distinction
- **Query 1** filters on **package-level** license: `packageinfo.Licenses LIKE '%MIT%'`
- **Query 2** filters on **project-level** license: `project_info.Licenses = 'MIT'`
- These are different fields — do not confuse them

---

## 7. Query Patterns

### Query 1 — Top 5 NPM packages by GitHub fork count
**Question:** "Among all NPM packages with license 'MIT' marked as release, which 5 have the highest GitHub fork count?"

**Step 1 — SQLite:** Get all NPM MIT release packages (latest release per package)
```sql
SELECT Name, Version, Licenses, VersionInfo
FROM packageinfo
WHERE System = 'NPM'
  AND Licenses LIKE '%MIT%'
  AND VersionInfo LIKE '%"IsRelease": true%'
```
Then in Python: for each Name, keep only the row with maximum Ordinal.

**Step 2 — DuckDB:** Get ProjectName for matching packages
```sql
SELECT Name, Version, ProjectName
FROM project_packageversion
WHERE System = 'NPM'
  AND (Name, Version) IN (('pkg1', 'v1'), ('pkg2', 'v2'), ...)
```

**Step 3 — DuckDB:** Get fork count from project_info
```sql
SELECT Project_Information,
    CAST(regexp_extract(Project_Information, '(\d+)\s+forks?', 1) AS INTEGER) as fork_count
FROM project_info
WHERE Project_Information LIKE '%owner/repo%'
ORDER BY fork_count DESC
LIMIT 5
```

**Step 4 — Python:** Join all three, extract fork counts, sort DESC, return top 5 package names.

**Output format:** 5 package names, one per line

---

### Query 2 — NPM packages marked as release under MIT-licensed projects
**Question shape:** "Among all NPM packages with license 'MIT' marked as release, which 5 have the highest GitHub fork count?"

**Step 1 — DuckDB (`project_info`):** Find all MIT-licensed projects
```sql
SELECT Project_Information FROM project_info
WHERE Licenses LIKE '%MIT%'
```
Extract ProjectName from Project_Information text.

**Step 2 — DuckDB (`project_packageversion`):** Get packages for those projects
```sql
SELECT System, Name, Version FROM project_packageversion
WHERE ProjectName IN ('owner/repo1', ...)
  AND System = 'NPM'
```

**Step 3 — SQLite (`packageinfo`):** Filter to release versions
```sql
SELECT Name, Version FROM packageinfo
WHERE System = 'NPM'
  AND (Name, Version) IN (...)
  AND VersionInfo LIKE '%"IsRelease": true%'
```

**Output format:** Count or list of package names

---

## 8. Common Agent Failure Modes

| Failure | How to avoid |
|---|---|
| Using lexicographic version sorting | Always use `Ordinal` from `VersionInfo` JSON for latest release |
| Confusing package license vs project license | Q1 uses `packageinfo.Licenses`, Q2 uses `project_info.Licenses` |
| Not parsing `VersionInfo` JSON | Use `LIKE '%"IsRelease": true%'` for release check |
| Trying cross-DB SQL join | Not possible — three separate queries, merge in Python |
| Missing fork/star count | Extract from `Project_Information` text using `regexp_extract()` in DuckDB |
| Wrong System case | Always `System = 'NPM'` (uppercase) |
| Using `project_info` join key wrong | Match `ProjectName` from `project_packageversion` against `Project_Information` text |

---

## 9. Upstream Source

| Field | Value |
|---|---|
| Original dataset | [Google deps.dev BigQuery Dataset](https://deps.dev) |
| Coverage | Open source package ecosystems: NPM, PyPI, Go, Maven, Cargo, NuGet |
| DAB citation | Google, 2021 — *Deps.dev BigQuery Dataset*; Bozsolik, 2019 |
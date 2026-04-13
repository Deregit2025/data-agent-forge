# Knowledge Base: deps.dev Dataset

## 1. Dataset Overview
This dataset contains open-source package metadata from [deps.dev](https://deps.dev), covering package versions, licenses, security advisories, dependency resolution status, and associated open-source project information.

---

## 2. Tables and Contents

### `packageinfo` (SQLite — `query_sqlite_deps_dev_package`)
Contains one row per package **version** across multiple ecosystems.

| Field | Type | Notes |
|---|---|---|
| `System` | TEXT | Package ecosystem: `NPM`, `PyPI`, `Go`, `Maven`, `Cargo`, etc. |
| `Name` | TEXT | Package name (may include scope, e.g. `@org/pkg`) |
| `Version` | TEXT | Version string |
| `Licenses` | TEXT | JSON array of SPDX license identifiers |
| `Advisories` | TEXT | JSON array of security advisories |
| `VersionInfo` | TEXT | JSON with `IsRelease` (bool) and `Ordinal` (int, version sequence order) |
| `Hashes` | TEXT | JSON array of `{Hash, Type}` objects; types: `MD5`, `SHA1`, `SHA256`, `SHA512` |
| `DependenciesProcessed` | INTEGER | `1` = dependency resolution attempted |
| `DependencyError` | INTEGER | `1` = error occurred during dependency resolution |
| `UpstreamPublishedAt` | REAL | Publish timestamp in **microseconds** since Unix epoch |
| `Links` | TEXT | JSON array of `{Label, URL}`; `ORIGIN` label = registry URL |
| `Registries` | TEXT | JSON array of additional registries |
| `SLSAProvenance` | REAL | SLSA provenance data (mostly null) |

**Composite key:** `(System, Name, Version)`

---

### `project_info` (DuckDB — `query_duckdb_deps_dev_project`)
Contains one row per open-source project (typically a GitHub repository).

| Field | Type | Notes |
|---|---|---|
| `Project_Information` | VARCHAR | Human-readable summary including open issues, stars, forks |
| `Licenses` | VARCHAR | JSON array of license identifiers |
| `Description` | VARCHAR | Project description |
| `Homepage` | VARCHAR | Project homepage URL |
| `OSSFuzz` | DOUBLE | OSS-Fuzz integration data (mostly null) |

---

### `project_packageversion` (DuckDB — `query_duckdb_deps_dev_project`)
Links projects to specific package versions.

| Field | Type | Notes |
|---|---|---|
| `System` | VARCHAR | Matches `packageinfo.System` |
| `Name` | VARCHAR | Matches `packageinfo.Name` |
| `Version` | VARCHAR | Matches `packageinfo.Version` |
| `ProjectType` | VARCHAR | e.g., `GITHUB` |
| `ProjectName` | VARCHAR | e.g., `github.com/org/repo` |
| `RelationProvenance` | VARCHAR | How the relationship was determined |
| `RelationType` | VARCHAR | Nature of the link (e.g., source repo) |

---

## 3. Join Keys
- `project_packageversion` → `packageinfo`: join on `(System, Name, Version)` — all three fields must match; both databases must be queried separately and results merged.
- `project_packageversion` → `project_info`: join on `ProjectName` (no explicit FK; match by project identifier string).

---

## 4. Domain Terms
- **System**: The package registry/ecosystem (e.g., NPM, PyPI)
- **Ordinal**: Integer indicating a version's sequential release order within a package
- **IsRelease**: Whether a version is a formal release (vs. pre-release)
- **DependencyError**: Failed dependency graph resolution for that version

---

## 5. Known Query Patterns
- Packages with security advisories by ecosystem
- Packages with dependency resolution errors
- License distribution across ecosystems
- Most starred/forked projects linked to specific packages
- Packages published within a date range (convert `Up
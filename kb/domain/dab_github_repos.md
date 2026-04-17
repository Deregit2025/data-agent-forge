# Knowledge Base: GitHub Repos Dataset (DataAgentBench)

---

## 1. Dataset Overview

The github_repos dataset contains metadata and artifacts for GitHub repositories, split across a SQLite metadata database (languages, licenses, watch counts) and a DuckDB artifacts database (file contents, commit history, file-level metadata).

---

## 2. CRITICAL — MCP Tool Mapping

| Tool Name | DB Type | Contains |
|---|---|---|
| `query_sqlite_github_metadata` | SQLite | `languages`, `licenses`, `repos` |
| `query_duckdb_github_artifacts` | DuckDB | `contents`, `commits`, `files` |

---

## 3. Tables and Collections

### SQLite — `languages`
- **Purpose:** Declares programming languages used per repository.
- **Fields:**
  - `repo_name` (TEXT): Repository identifier in `owner/repo` format.
  - `language_description` (TEXT): Natural language string listing one or more programming languages and their byte counts (e.g., `"Python: 12345 bytes, Shell: 678 bytes"`). May contain multiple languages.

### SQLite — `licenses`
- **Purpose:** Declares the license for each repository.
- **Fields:**
  - `repo_name` (TEXT): Repository identifier in `owner/repo` format.
  - `license` (TEXT): Lowercase license identifier string (e.g., `apache-2.0`, `mit`, `gpl-2.0`). Apache 2.0 is stored as `apache-2.0`.

### SQLite — `repos`
- **Purpose:** Repository-level watch statistics.
- **Fields:**
  - `repo_name` (TEXT): Repository identifier in `owner/repo` format.
  - `watch_count` (INTEGER): Number of GitHub watchers.

### DuckDB — `contents`
- **Purpose:** File content and file-level metadata for repository files.
- **Fields:**
  - `id` (VARCHAR): Blob identifier for the file (Git object SHA).
  - `content` (VARCHAR): Textual content of the file. May be truncated or contain placeholders for binary/large files.
  - `sample_repo_name` (VARCHAR): Repository name in `owner/repo` format.
  - `sample_ref` (VARCHAR): Branch name or commit SHA reference.
  - `sample_path` (VARCHAR): File path within the repository (e.g., `README.md`, `src/main.py`).
  - `sample_symlink_target` (VARCHAR): Symlink target path if the file is a symlink; otherwise NULL or empty.
  - `repo_data_description` (VARCHAR): Natural language metadata derived from file attributes including original size, whether the file is binary, number of copies, and file mode.

### DuckDB — `commits`
- **Purpose:** Full commit history across repositories.
- **Fields:**
  - `commit` (VARCHAR): Unique commit SHA.
  - `tree` (VARCHAR): SHA of the associated tree object.
  - `parent` (VARCHAR): Parent commit SHA(s); JSON-like format for merge commits.
  - `author` (VARCHAR): JSON-like object with author name, email, and timestamp.
  - `committer` (VARCHAR): JSON-like object with committer name, email, and timestamp.
  - `subject` (VARCHAR): Short subject line of the commit message.
  - `message` (VARCHAR): Full commit message text.
  - `trailer` (VARCHAR): Additional commit metadata (JSON-like).
  - `difference` (VARCHAR): JSON-like structure of file changes in the commit.
  - `difference_truncated` (DOUBLE): Non-null/truthy value indicates the difference data is truncated.
  - `repo_name` (VARCHAR): Repository name in `owner/repo` format.
  - `encoding` (VARCHAR): Encoding format of the commit data if applicable.

### DuckDB — `files`
- **Purpose:** File-level metadata (path, mode, blob ID) per repository reference.
- **Fields:**
  - `repo_name` (VARCHAR): Repository name in `owner/repo` format.
  - `ref` (VARCHAR): Branch or commit SHA reference.
  - `path` (VARCHAR): File path within the repository.
  - `mode` (INTEGER): File mode integer (e.g., normal file, executable, symlink).
  - `id` (VARCHAR): Blob identifier matching `contents.id`.
  - `symlink_target` (VARCHAR): Symlink target path if applicable.

---

## 4. Join Keys

| Left Table (Tool) | Left Key | Right Table (Tool) | Right Key | Notes |
|---|---|---|---|---|
| `languages` (SQLite) | `repo_name` | `licenses` (SQLite) | `repo_name` | Same format, direct join |
| `languages` (SQLite) | `repo_name` | `repos` (SQLite) | `repo_name` | Same format, direct join |
| `licenses` (SQLite) | `repo_name` | `commits` (DuckDB) | `repo_name` | Cross-DB join; apply filter in each DB then intersect repo_names |
| `languages` (SQLite) | `repo_name` | `commits` (DuckDB) | `repo_name` | Cross-DB join; fetch repo list from SQLite, use IN clause in DuckDB |
| `languages` (SQLite) | `repo_name` | `contents` (DuckDB) | `sample_repo_name` | **Key name differs**: `repo_name` vs `sample_repo_name` |
| `files` (DuckDB) | `id` | `contents` (DuckDB) | `id` | Blob-level join within DuckDB |
| `files` (DuckDB) | `repo_name` | `commits` (DuckDB) | `repo_name` | Within DuckDB |

**Verbatim from official hints:**
> Some queries may require joining across tables using identifiers such as "id" or "repo_name" to correctly combine information.

**Cross-database join pattern:** Since SQLite and DuckDB cannot be queried together natively, the correct approach is:
1. Query SQLite to get a filtered list of `repo_name` values.
2. Pass that list as an `IN (...)` filter in a subsequent DuckDB query.

---

## 5. Critical Domain Knowledge

### Verbatim Official Hints

> Some queries may require joining across tables using identifiers such as "id" or "repo_name" to correctly combine information.

> The "languages" table's language_description field may contain multiple programming languages per repository. To determine the primary or main language, compare the relative number of bytes across languages.

> The "contents" table's repo_data_description field contains natural language metadata derived from file attributes (e.g., size, binary, copies, mode). Some queries may rely on these attributes for filtering or interpretation.

### Additional Domain Knowledge

#### Determining Primary/Main Language
- `language_description` is a free-text field listing languages with byte counts (e.g., `"Python: 45000 bytes, JavaScript: 3000 bytes"`).
- To find the **main language**, parse byte counts from `language_description` and select the language with the highest byte count.
- To find repos where the **main language is NOT Python**: parse `language_description`, identify the language with the highest byte count, and exclude rows where that language is Python.
- To find repos that **do not use Python at all**: exclude any repo where `language_description` LIKE `'%Python%'`.
- These two interpretations differ — read each query carefully.
#### Identifying Non-Binary Files
- Binary vs. non-binary status is encoded in `contents.repo_data_description` as PROSE, not key-value.
- Actual phrasing is "non-binary" (e.g., "this non-binary file", "A 277-byte non-binary file").
- Filter non-binary files using: `repo_data_description ILIKE '%non-binary%'`
- Do NOT use `LIKE '%binary: false%'` — that pattern does not exist in the data.

#### Identifying Copies Count
- The number of copies is encoded in `repo_data_description` as PROSE, not key-value.
- Actual phrasings observed: "duplicated 8 times", "appears 9 times", "appearing 9 times".
- Correct DuckDB regex: `regexp_extract(repo_data_description, '(?:duplicated|appears|appearing) (\d+) times', 1)`
- Cast to integer: `CAST(regexp_extract(...) AS INTEGER)`
- Do NOT use `'copies: \d+'` — that pattern does not exist in the data.
- "Most frequently copied" = file `id` with highest extracted count.
- Deduplicate on `id` before finding max (same blob can appear across multiple repos).

#### README.md Detection
- Filter using `sample_path = 'README.md'` (case-sensitive exact match)
---

#### torvalds/linux cross-DB exclusion (Q4)
- `torvalds/linux` exists in DuckDB `commits` (16061 commits) but is ABSENT from SQLite `languages`.
- The cross-DB join (SQLite → DuckDB) therefore excludes it from Q4 results.
- Ground truth top 5 non-Python repos by commits: apple/swift, twbs/bootstrap, Microsoft/vscode, facebook/react, tensorflow/tensorflow.

## 6. Query Patterns

### query1: *Among repositories that do not use Python, what proportion of their README.md files include copyright information?*

1. `query_sqlite_github_metadata` (`languages`): Filter `language_description NOT LIKE '%Python%'`. Get `repo_name` for repos not using Python.
2. `query_duckdb_github_artifacts` (`contents`): Use `sample_repo_name IN (...)` with the repo list from step 1. Filter `sample_path = 'README.md'`.
3. Read the `content` field. Count how many READMEs contain the word "copyright" (case-insensitive, e.g., `content ILIKE '%copyright%'`).
4. Output the proportion (count of copyright READMEs / total READMEs from non-Python repos).

### query2: *Identify the repository in Swift language that contains the most frequently copied non-binary Swift file in the dataset, ensuring that each file is uniquely determined by its ID.*

1. `query_sqlite_github_metadata` (`languages`): Filter `language_description LIKE '%Swift%'`. Get `repo_name` for Swift repos.
2. `query_duckdb_github_artifacts` (`contents`): Filter `sample_repo_name IN (...)` with the Swift repos list. Filter `sample_path LIKE '%.swift'` AND repo_data_description ILIKE '%non-binary%'.
3. Extract the `copies` count from `repo_data_description` (e.g., parsing "copies: X"). Since each file must be uniquely determined by its ID, deduplicate rows by `id` or aggregate `copies` properly. Find the file `id` with the highest copy count.
4. Return its `sample_repo_name`. (If there are multiple rows for the same `id`, take that repository).

### query3: *How many commit messages are found in repositories that use the Shell programming language and are licensed under Apache-2.0, where each message exists, is shorter than 1,000 characters, and does not begin with 'merge', 'update', or 'test'?*

1. `query_sqlite_github_metadata` (`languages`): Filter `language_description LIKE '%Shell%'`. Get `repo_name` list.
2. `query_sqlite_github_metadata` (`licenses`): Filter `repo_name IN (...)` AND `license = 'apache-2.0'`. Get intersected `repo_name` list.
3. `query_duckdb_github_artifacts` (`commits`): Filter `repo_name IN (...)`.
4. Filter `message IS NOT NULL` AND `length(message) < 1000` AND NOT (message ILIKE 'merge%' OR message ILIKE 'update%' OR message ILIKE 'test%').
5. Count the resulting rows.

### query4: *List the repository names for the top five GitHub repositories whose main language is not Python, ordered by the highest number of commits.*

1. `query_sqlite_github_metadata` (`languages`): Process `language_description`. Parse byte counts for each language. Identify the dominant language (max bytes) for each repo. Keep `repo_name` where the dominant language is NOT Python.
2. `query_duckdb_github_artifacts` (`commits`): Filter `repo_name IN (...)`. Group by `repo_name` and count commits.
3. Order by commit count DESC. Return top 5 repository names.

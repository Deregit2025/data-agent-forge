# Knowledge Base: github_repos Dataset

## 1. Dataset Overview
This dataset contains metadata, source code artifacts, commit history, and file structure information for public GitHub repositories.

---

## 2. Tables and Contents

### SQLite — `query_sqlite_github_metadata`

#### `repos`
Stores basic repository-level metadata.
- `repo_name` (TEXT): Unique repo identifier in `owner/repo` format (e.g., `torvalds/linux`)
- `watch_count` (INTEGER): Number of watchers on the repository

#### `languages`
Describes programming languages used in each repository.
- `repo_name` (TEXT): Links to `repos.repo_name`
- `language_description` (TEXT): Human-readable natural language string describing languages and byte counts (e.g., `"Ruby (22,438 bytes), Shell (465 bytes)"`) — **not structured columns; requires text parsing**

#### `licenses`
Stores the open-source license associated with each repository.
- `repo_name` (TEXT): Links to `repos.repo_name`
- `license` (TEXT): License identifier (e.g., `mit`, `apache-2.0`)

---

### DuckDB — `query_duckdb_github_artifacts`

#### `commits`
One row per commit per repository.
- `commit` (VARCHAR): SHA1 commit hash
- `repo_name` (VARCHAR): Links to SQLite `repo_name`
- `subject` (VARCHAR): First line of commit message
- `message` (VARCHAR): Full commit message body
- `author` / `committer` (VARCHAR): JSON strings with fields `name`, `email`, `date` (microseconds epoch), `time_sec` (Unix seconds), `tz_offset`
- `parent` (VARCHAR): JSON array of parent commit SHA1 hashes
- `trailer` (VARCHAR): JSON array of commit trailer entries with `key` (e.g., `Signed-off-by`, `Acked-by`, `Cc`), `value`, `email`
- `difference` (VARCHAR): JSON array of file diffs with `old_path`, `new_path`, `old_sha1`, `new_sha1`, `old_mode`, `new_mode`
- `difference_truncated` (DOUBLE): Non-null if the diff was truncated; otherwise null
- `encoding` (VARCHAR): Commit encoding if non-default; usually null

#### `files`
One row per file per repository branch/ref.
- `repo_name` (VARCHAR): Links to `repos.repo_name`
- `ref` (VARCHAR): Branch or tag reference (e.g., `refs/heads/master`)
- `path` (VARCHAR): File path within the repository
- `id` (VARCHAR): Blob SHA1; links to `contents.id`
- `mode` (BIGINT): Unix file mode integer
- `symlink_target` (VARCHAR): Target path if file is a symlink

#### `contents`
Stores raw file content blobs.
- `id` (VARCHAR): Blob SHA1; links to `files.id`
- `content` (VARCHAR): Raw file content
- `sample_repo_name`, `sample_ref`, `sample_path` (VARCHAR): One example location where this blob appears
- `repo_data_description` (VARCHAR): Descriptive text about the blob's repository context

---

## 3. Join Keys
| From | Key | To | Key |
|---|---|---|---|
| SQLite `repos` | `repo_name` | DuckDB `commits` | `repo_name` |
| SQLite `repos` | `repo_name` | DuckDB `files` | `repo_name` |
| DuckDB `files` | `id` | DuckDB `contents` | `id` |

> **Format note:** `repo_name` is `owner/repo` string in both databases — no transformation needed when joining across SQLite and DuckDB.

---

## 4. Domain Terms
- **trailer**: Structured metadata appended to commit messages (e.g., `Signed-off-by`, `Acked-by`, `Reviewed-by`, `Cc`)
- **ref**: A Git reference pointing to a branch or tag
- **blob SHA1 (`id`)
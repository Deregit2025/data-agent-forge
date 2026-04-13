# Knowledge Base: MusicBrainz Dataset

## 1. Dataset Overview
This dataset combines a music track catalog (SQLite) with digital store sales records (DuckDB) to support analysis of track metadata and commercial performance across countries and platforms.

---

## 2. Tables

### `tracks` (SQLite — `query_sqlite_music_brainz`)
Contains metadata for individual music tracks sourced from multiple data providers.

| Field | Type | Notes |
|---|---|---|
| `track_id` | INTEGER (PK) | Internal unique identifier |
| `source_id` | INTEGER | Identifies the data provider/source system |
| `source_track_id` | TEXT | Track ID in the originating source system (e.g., `MBox7368722-HH`, `139137-A047`) |
| `title` | TEXT | May include artist name embedded (e.g., `"Daniel Balavoine - L'enfant aux yeux d'Italie"`) — not always clean |
| `artist` | TEXT | Can be `null` or `"[unknown]"` — not reliable as sole artist field |
| `album` | TEXT | Album name; may include `(unknown)` suffix |
| `year` | TEXT | Two-digit year strings (e.g., `"75"`, `"95"`); not standardized to 4-digit format; can be `null` |
| `length` | TEXT | **Inconsistent format**: sometimes seconds as integer string (`"219"`), sometimes human-readable (`"1m 58sec"`) |
| `language` | TEXT | Language of the track; inconsistent abbreviations (e.g., `"Por."` vs `"French"`, `"English"`) |

---

### `sales` (DuckDB — `query_duckdb_music_brainz_sales`)
Contains digital store sales transactions linked to tracks.

| Field | Type | Notes |
|---|---|---|
| `sale_id` | INTEGER | Unique sale record identifier |
| `track_id` | INTEGER | Foreign key to `tracks.track_id` |
| `country` | VARCHAR | Country where sale occurred (e.g., `"Canada"`, `"Germany"`) |
| `store` | VARCHAR | Digital storefront (e.g., `"Google Play"`, `"Apple Music"`) |
| `units_sold` | INTEGER | Number of units sold in this record |
| `revenue_usd` | DOUBLE | Revenue in US dollars for this record |

---

## 3. Join Keys
- `sales.track_id` → `tracks.track_id` (both INTEGER; direct join across databases)
- Cross-database queries require fetching from each tool separately and joining in application logic or a federated layer.

---

## 4. Domain Terms
- **source_id**: Numeric code representing a third-party catalog provider
- **[unknown]**: Literal string used as a placeholder for missing artist data
- **units_sold**: Per-record count; a single track may have multiple sales rows per country/store combination

---

## 5. Known Query Patterns
- Top-selling tracks or artists by `revenue_usd` or `units_sold`
- Sales breakdown by `country` or `store`
- Filter tracks by `language` (account for abbreviation inconsistencies)
- Identify tracks with missing or incomplete metadata (`artist IS NULL OR artist = '[unknown]'`)
- Revenue by album or year (requires normalizing `year` from 2-digit strings)
- Compare store performance across regions
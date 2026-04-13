# Knowledge Base: GoogleLocal Dataset

## 1. Dataset Overview
This dataset contains Google Maps business listings and customer reviews for local businesses, primarily in the Los Angeles area.

---

## 2. Tables & Collections

### PostgreSQL — `business_description`
Contains business profile information scraped from Google Maps.

| Field | Type | Description |
|---|---|---|
| `name` | text | Business name |
| `gmap_id` | text | Unique business identifier (e.g., `gmap_44`) |
| `description` | text | AI-generated or scraped business description |
| `num_of_reviews` | bigint | Total count of reviews for the business |
| `hours` | text | JSON array of `[day, hours_string]` pairs; `null` if unavailable |
| `MISC` | text | JSON object with attributes like Service options, Accessibility, Payments, Atmosphere |
| `state` | text | Current open/closed status (e.g., `"Open now"`, `"Open ⋅ Closes 6PM"`) |

**Notes:**
- `hours` is stored as a serialized JSON string, not a native array. Parse before filtering by day/time.
- `MISC` is a serialized JSON object with variable keys. Known keys include: `Service options`, `Accessibility`, `Offerings`, `Amenities`, `Atmosphere`, `Payments`.

---

### SQLite — `review`
Contains individual customer reviews linked to businesses.

| Field | Type | Description |
|---|---|---|
| `name` | TEXT | Reviewer's name |
| `time` | TEXT | Review timestamp — **inconsistent format**: some are `"September 03, 2020 at 04:15 PM"`, others are `"2021-04-12 17:07:52"` |
| `rating` | INTEGER | Star rating, range **1–5** |
| `text` | TEXT | Review text content |
| `gmap_id` | TEXT | Foreign key linking to `business_description.gmap_id` |

---

## 3. Join Keys

| Left Table | Key | Right Table | Key |
|---|---|---|---|
| `business_description` | `gmap_id` | `review` | `gmap_id` |

- Both use the same `gmap_id` string format (e.g., `gmap_44`). No format transformation needed for joins.
- Join requires a **cross-database query** (PostgreSQL ↔ SQLite).

---

## 4. Domain Terms

- **gmap_id**: Unique Google Maps place identifier used across both tables
- **state**: Operational status at scrape time, not a US state
- **MISC**: Catch-all attribute bag for business amenities and service features
- **num_of_reviews**: Stored on the business record; actual review count may differ from rows in `review` table

---

## 5. Known Query Patterns

- Find businesses by service type (parse `MISC → Service options`)
- Filter businesses currently open (use `state` field)
- Calculate average rating per business (aggregate `review.rating` grouped by `gmap_id`)
- Find businesses by operating hours on a specific day (parse `hours` JSON string)
- Join reviews to business details for sentiment or rating analysis
- Rank businesses by `num_of_reviews` or average `rating`
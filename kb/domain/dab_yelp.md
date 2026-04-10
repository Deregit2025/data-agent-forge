# DataAgentBench: Yelp Domain Schema & Known Patterns

## Databases
This domain requires querying across two distinct database systems: **MongoDB** and **DuckDB**.

### 1. `businessinfo_database` (MongoDB)
Contains metadata and check-in records for businesses.
**Collections:**
- `business`:
  - `_id` (ObjectId)
  - `business_id` (str): Unique business identifier.
  - `name` (str): Business name.
  - `review_count` (int): Total number of reviews.
  - `is_open` (int): Operational status (1=open, 0=closed).
  - `attributes` (dict or null): Nested features (parking, WiFi, etc.).
  - `hours` (dict or null): Operating hours.
  - `description` (str): Free-text description including location info.
- `checkin`:
  - `_id` (ObjectId)
  - `business_id` (str): Links to `business` collection.
  - `date` (list of str): Timestamps of check-ins.

### 2. `user_database` (DuckDB)
Contains user profiles, reviews, and tips.
**Tables:**
- `review`:
  - `review_id` (str)
  - `user_id` (str or null): Links to `user.user_id`.
  - `business_ref` (str): Links to `business.business_id` in MongoDB.
  - `rating` (int)
  - `useful`, `funny`, `cool` (int): Vote counts.
  - `text` (str): Unstructured review context.
  - `date` (str)
- `tip`:
  - `user_id` (str or null)
  - `business_ref` (str): Links to `business.business_id` in MongoDB.
  - `text` (str)
  - `date` (str)
  - `compliment_count` (int)
- `user`:
  - `user_id` (str)
  - `name` (str)
  - `review_count`, `useful`, `funny`, `cool` (int)
  - `yelping_since` (str)
  - `elite` (str): Comma-separated list of elite years.

---
## Known Query Patterns & Edge Cases
1. **Cross-Database Joins:** To find all reviews for a business named "X", the agent must first query MongoDB `business` collection to find the `business_id` where `name="X"`, and then query DuckDB `review` table using `business_ref = [business_id]`.
2. **Ill-formatted Foreign Keys:** DuckDB uses `business_ref` while MongoDB uses `business_id`. 
3. **Unstructured Data:** MongoDB's `business.description` field holds string descriptions containing location info, and DuckDB's `review.text` holds user text.

# Injection Test: Yelp Domain Knowledge

**Objective:** Verify that the LLM correctly parses the `dab_yelp.md`, `join_key_glossary.md`, and `unstructured_fields.md` files.

### Test Prompt:
> "According to our Domain Knowledge Base, if I want to join the MongoDB `business` collection to the DuckDB `review` table to find reviews for a specific business, what specific column name from DuckDB should I match against the MongoDB `business_id` field? Also, which specific field on the MongoDB `business` collection contains unstructured information about the business's location?"

### Expected Answer Elements:
1. Must identify the DuckDB column as `business_ref`.
2. Must identify the MongoDB unstructured field as `description`.
3. Should explicitly warn against using standard SQL equality on `description` because it is free-text.

### Result: 
*(To be filled by Intelligence Officer after testing)*

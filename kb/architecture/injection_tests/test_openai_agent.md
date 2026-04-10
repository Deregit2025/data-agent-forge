# Injection Test: OpenAI Data Agent Architecture

**Objective:** Verify that the LLM understands and can recall the layered context system from the internal `openai_data_agent.md` documentation.

### Test Prompt:
> "According to the Architecture Knowledge Base, if our Data Agent encounters a MongoDB target where the user's ID is stored as `uid` but needs to join it against a Postgres table where the ID is stored as `customer_id`, which specific layer of the Context Architecture provides the mapping instruction to resolve this irregularly formatted key?"

### Expected Answer Elements:
1. Must identify "Layer 5" by number.
2. Must specify that this is the "Ill-formatted Key Mappings" layer.
3. Should recognize that this layer provides the known irregularities and mappings across databases.

### Result: 
*(To be filled by Intelligence Officer after testing)*

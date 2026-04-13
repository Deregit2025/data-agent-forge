import time
import json
from typing import Any
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from mcp.db_config import MONGO_CONFIG, MONGO_TOOLS


class _JSONEncoder(json.JSONEncoder):
    """Handle MongoDB types that are not JSON serialisable by default."""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if hasattr(obj, "isoformat"):          # datetime
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.hex()
        return super().default(obj)


def _serialise(docs: list) -> list[dict]:
    """Convert a list of MongoDB documents to plain JSON-safe dicts."""
    return json.loads(json.dumps(docs, cls=_JSONEncoder))


def execute_query(tool_name: str, pipeline: str) -> dict[str, Any]:
    """
    Execute a MongoDB aggregation pipeline against the collection
    mapped to tool_name.

    pipeline  — JSON string representing a list of pipeline stages,
                e.g. '[{"$match": {"stars": {"$gte": 4}}}, {"$limit": 10}]'

    Returns the same structured response as all other tool files.
    """
    tool = MONGO_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, pipeline, f"Unknown tool: '{tool_name}'")

    # parse pipeline
    try:
        stages = json.loads(pipeline)
        if not isinstance(stages, list):
            raise ValueError("Pipeline must be a JSON array of stages.")
    except (json.JSONDecodeError, ValueError) as e:
        return _error_response(
            tool_name, pipeline,
            f"Invalid pipeline JSON: {e}. "
            "Pipeline must be a JSON array, e.g. '[{{\"$limit\": 5}}]'"
        )

    # safety — block write stages
    write_stages = {
        "$out", "$merge", "$indexStats",
        "$currentOp", "$listLocalSessions",
    }
    for stage in stages:
        for key in stage:
            if key in write_stages:
                return _error_response(
                    tool_name, pipeline,
                    f"Write stage '{key}' is not permitted. "
                    "Only read aggregation stages are allowed."
                )

    start  = time.perf_counter()
    client = None
    try:
        client     = MongoClient(MONGO_CONFIG["uri"], serverSelectionTimeoutMS=5000)
        db         = client[tool["database"]]
        collection = db[tool["collection"]]

        cursor  = collection.aggregate(stages)
        docs    = list(cursor)
        elapsed = round(time.perf_counter() - start, 4)
        result  = _serialise(docs)

        return {
            "result":         result,
            "query_used":     pipeline,
            "db_type":        "mongodb",
            "tool_name":      tool_name,
            "database":       tool["database"],
            "collection":     tool["collection"],
            "row_count":      len(result),
            "execution_time": elapsed,
            "error":          None,
        }

    except PyMongoError as e:
        elapsed = round(time.perf_counter() - start, 4)
        return {
            "result":         [],
            "query_used":     pipeline,
            "db_type":        "mongodb",
            "tool_name":      tool_name,
            "database":       tool.get("database", ""),
            "collection":     tool.get("collection", ""),
            "row_count":      0,
            "execution_time": elapsed,
            "error":          str(e),
        }
    finally:
        if client:
            client.close()


def get_schema(tool_name: str) -> dict[str, Any]:
    """
    Return a sample-based schema of the MongoDB collection
    mapped to tool_name.
    MongoDB is schemaless so we sample 100 documents and
    infer field names and types from them.
    Used by utils/schema_introspector.py.
    """
    tool = MONGO_TOOLS.get(tool_name)
    if tool is None:
        return _error_response(tool_name, "", f"Unknown tool: '{tool_name}'")

    client = None
    try:
        client     = MongoClient(MONGO_CONFIG["uri"], serverSelectionTimeoutMS=5000)
        db         = client[tool["database"]]
        collection = db[tool["collection"]]

        sample = list(collection.aggregate([{"$sample": {"size": 100}}]))
        fields = {}
        for doc in sample:
            for key, val in doc.items():
                if key not in fields:
                    fields[key] = type(val).__name__

        return {
            "tool_name":  tool_name,
            "db_type":    "mongodb",
            "database":   tool["database"],
            "collection": tool["collection"],
            "schema":     {
                tool["collection"]: [
                    {"field": k, "type": v}
                    for k, v in fields.items()
                ]
            },
            "note":  "Schema inferred from 100 document sample.",
            "error": None,
        }

    except PyMongoError as e:
        return _error_response(tool_name, "", str(e))
    finally:
        if client:
            client.close()


def list_tools() -> list[dict[str, Any]]:
    """
    Return all MongoDB tools with their descriptions.
    Called by mcp_server.py to build the combined tool list.
    """
    return [
        {
            "name":        name,
            "description": meta["description"],
            "db_type":     "mongodb",
            "database":    meta["database"],
            "collection":  meta["collection"],
            "parameters":  [
                {
                    "name":        "pipeline",
                    "type":        "string",
                    "description": (
                        "MongoDB aggregation pipeline as a JSON array of stages. "
                        "Example: '[{\"$match\": {\"stars\": {\"$gte\": 4}}}, "
                        "{\"$limit\": 10}]'"
                    ),
                    "required":    True,
                }
            ],
        }
        for name, meta in MONGO_TOOLS.items()
    ]


# ── helpers ───────────────────────────────────────────────────────────────────

def _error_response(tool_name: str, pipeline: str, msg: str) -> dict[str, Any]:
    return {
        "result":         [],
        "query_used":     pipeline,
        "db_type":        "mongodb",
        "tool_name":      tool_name,
        "database":       "",
        "collection":     "",
        "row_count":      0,
        "execution_time": 0,
        "error":          msg,
    }
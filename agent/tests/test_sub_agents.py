import asyncio

from agent.sub_agents.duckdb_agent import DuckDBSubAgent
from agent.sub_agents.mongo_agent import MongoSubAgent
from agent.sub_agents.postgres_agent import PostgresSubAgent
from agent.sub_agents.sqlite_agent import SQLiteSubAgent


def test_all_sub_agents_execute_with_yelp_hints():
    calls = []

    async def fake_executor(tool_name, payload):
        calls.append((tool_name, payload))
        return {"rows": [{"tool": tool_name, "ok": True}]}

    postgres = PostgresSubAgent(available_tools=["query_postgres_bookreview"])
    mongo = MongoSubAgent(available_tools=["query_mongo_yelp"])
    sqlite = SQLiteSubAgent(available_tools=["query_sqlite_yelp_user"])
    duckdb = DuckDBSubAgent(available_tools=["query_duckdb_music_brainz"])

    r1 = asyncio.run(
        postgres.execute(
            {"id": "p1", "db_type": "postgres", "task": "SELECT 1", "source_hint": "yelp"},
            tool_executor=fake_executor,
        )
    )
    r2 = asyncio.run(
        mongo.execute(
            {
                "id": "m1",
                "db_type": "mongo",
                "task": "find yelp docs",
                "collection": "business",
                "pipeline": [{"$limit": 1}],
                "source_hint": "yelp",
            },
            tool_executor=fake_executor,
        )
    )
    r3 = asyncio.run(
        sqlite.execute(
            {"id": "s1", "db_type": "sqlite", "task": "SELECT 1", "source_hint": "yelp"},
            tool_executor=fake_executor,
        )
    )
    r4 = asyncio.run(
        duckdb.execute(
            {"id": "d1", "db_type": "duckdb", "task": "SELECT 1", "source_hint": "yelp"},
            tool_executor=fake_executor,
        )
    )

    assert r1["status"] == "ok"
    assert r2["status"] == "ok"
    assert r3["status"] == "ok"
    assert r4["status"] == "ok"
    assert len(calls) == 4

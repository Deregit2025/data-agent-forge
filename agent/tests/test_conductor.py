import asyncio

from agent.conductor import ConductorAgent


def test_conductor_fans_out_and_merges():
    seen_tools = []

    async def fake_executor(tool_name, payload):
        seen_tools.append(tool_name)
        return {"rows": [{"tool": tool_name, "payload": payload}]}

    conductor = ConductorAgent(tool_executor=fake_executor)
    result = asyncio.run(conductor.run("Analyze Yelp business trend"))

    assert result["status"] in {"success", "partial_success"}
    assert result["result_count"] >= 1
    assert len(seen_tools) >= 1

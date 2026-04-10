"""Minimal runtime entrypoint for the conductor agent."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from agent.conductor import ConductorAgent


async def _demo_executor(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"tool": tool_name, "payload": payload, "rows": [{"ok": True}]}


async def run(question: str) -> dict[str, Any]:
    conductor = ConductorAgent(tool_executor=_demo_executor)
    return await conductor.run(question)


if __name__ == "__main__":
    output = asyncio.run(run("Summarize Yelp business activity"))
    print(json.dumps(output, indent=2))

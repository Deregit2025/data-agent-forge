"""
Claude Adapter for DataAgentBench
Registers Claude (claude-sonnet-4-6) as a supported model in DAB's
DataAgent framework so run_agent.py accepts --llm claude-sonnet-4-6.

Usage in DAB evaluation:
    python run_agent.py \
        --dataset yelp \
        --query_id 1 \
        --llm claude-sonnet-4-6 \
        --iterations 100 \
        --use_hints \
        --root_name run_0

Patching strategy:
    DAB's DataAgent.__init__ checks deployment_name to pick an LLM client.
    We monkey-patch the _init_client method to add a Claude branch
    without modifying DAB source files directly.
    This keeps the DAB repo clean and our changes isolated.
"""

import os
import json
from typing import Any
import anthropic

# ── Claude client wrapper ─────────────────────────────────────────────────────

class ClaudeClient:
    """
    Wraps the Anthropic client to match the interface DAB's DataAgent
    expects from its LLM client — specifically the chat.completions.create
    style call pattern.
    """

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model  = "claude-sonnet-4-6"
        self.chat   = self          # DAB calls self.client.chat.completions.create
        self.completions = self     # so we need self.client.chat.completions

    def create(
        self,
        model:       str,
        messages:    list[dict],
        tools:       list[dict] | None = None,
        max_tokens:  int = 4096,
        temperature: float = 0.0,
        **kwargs,
    ) -> "ClaudeResponse":
        """
        Translate DAB's OpenAI-style call into an Anthropic API call.
        Returns a ClaudeResponse that mimics OpenAI's response structure
        so DAB's parsing logic works without modification.
        """
        # separate system message from conversation messages
        system  = ""
        history = []
        for msg in messages:
            if msg["role"] == "system":
                system += msg["content"] + "\n"
            else:
                history.append(msg)

        # build Anthropic API call kwargs
        call_kwargs: dict[str, Any] = {
            "model":      self.model,
            "max_tokens": max_tokens,
            "messages":   history,
        }
        if system.strip():
            call_kwargs["system"] = system.strip()
        if tools:
            call_kwargs["tools"] = _convert_tools(tools)

        response = self.client.messages.create(**call_kwargs)
        return ClaudeResponse(response)


class ClaudeResponse:
    """
    Wraps Anthropic's response to match OpenAI's response structure.
    DAB accesses: response.choices[0].message.content
                  response.choices[0].message.tool_calls
                  response.choices[0].finish_reason
    """

    def __init__(self, response: anthropic.types.Message):
        self.choices = [ClaudeChoice(response)]
        self.usage   = {
            "input_tokens":  response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }


class ClaudeChoice:
    def __init__(self, response: anthropic.types.Message):
        self.finish_reason = _map_stop_reason(response.stop_reason)
        self.message       = ClaudeMessage(response)


class ClaudeMessage:
    def __init__(self, response: anthropic.types.Message):
        self.role       = "assistant"
        self.content    = _extract_text(response.content)
        self.tool_calls = _extract_tool_calls(response.content)


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_text(content: list) -> str:
    """Extract all text blocks from Anthropic response content."""
    return "\n".join(
        block.text
        for block in content
        if hasattr(block, "text")
    )


def _extract_tool_calls(content: list) -> list | None:
    """
    Extract tool use blocks and convert to OpenAI tool_call format.
    DAB uses tool_calls to execute database queries and Python code.
    """
    calls = []
    for block in content:
        if block.type == "tool_use":
            calls.append(ClaudeToolCall(block))
    return calls if calls else None


class ClaudeToolCall:
    """Mimics OpenAI's tool call object structure."""
    def __init__(self, block):
        self.id       = block.id
        self.type     = "function"
        self.function = ClaudeFunction(block)


class ClaudeFunction:
    def __init__(self, block):
        self.name      = block.name
        self.arguments = json.dumps(block.input)


def _convert_tools(openai_tools: list[dict]) -> list[dict]:
    """
    Convert OpenAI tool format to Anthropic tool format.

    OpenAI format:
    {
        "type": "function",
        "function": {
            "name": "...",
            "description": "...",
            "parameters": { "type": "object", "properties": {...} }
        }
    }

    Anthropic format:
    {
        "name": "...",
        "description": "...",
        "input_schema": { "type": "object", "properties": {...} }
    }
    """
    converted = []
    for tool in openai_tools:
        if tool.get("type") == "function":
            fn = tool["function"]
            converted.append({
                "name":         fn["name"],
                "description":  fn.get("description", ""),
                "input_schema": fn.get("parameters", {
                    "type":       "object",
                    "properties": {},
                }),
            })
    return converted


def _map_stop_reason(stop_reason: str | None) -> str:
    """Map Anthropic stop reasons to OpenAI finish reasons."""
    mapping = {
        "end_turn":    "stop",
        "tool_use":    "tool_calls",
        "max_tokens":  "length",
        "stop_sequence": "stop",
    }
    return mapping.get(stop_reason or "", "stop")


# ── patch DAB DataAgent ───────────────────────────────────────────────────────

def patch_data_agent():
    """
    Monkey-patch DAB's DataAgent to support Claude.
    Call this once before running any DAB evaluation.

    After patching, DataAgent accepts:
        deployment_name = "claude-sonnet-4-6"
    """
    import sys
    import os

    # ensure DAB is importable
    dab_path = os.getenv(
        "DAB_PATH",
        "/home/project/oracle-forge/DataAgentBench"
    )
    if dab_path not in sys.path:
        sys.path.insert(0, dab_path)

    from common_scaffold.DataAgent import DataAgent

    original_init = DataAgent.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

    def _init_client_with_claude(self, deployment_name: str):
        """Extended _init_client that adds Claude support."""
        if "claude" in deployment_name.lower():
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Add it to your .env file."
                )
            self.client = ClaudeClient(api_key=api_key)
            self.deployment_name = deployment_name
        else:
            # fall through to original client init for GPT / Gemini
            self._original_init_client(deployment_name)

    # save original and replace
    if hasattr(DataAgent, "_init_client"):
        DataAgent._original_init_client = DataAgent._init_client
        DataAgent._init_client = _init_client_with_claude
    else:
        # DataAgent initialises the client inline in __init__
        # wrap the whole __init__ instead
        def patched_full_init(self, *args, **kwargs):
            deployment_name = kwargs.get("deployment_name", "")
            if not deployment_name and len(args) >= 3:
                deployment_name = args[2]

            if "claude" in str(deployment_name).lower():
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError(
                        "ANTHROPIC_API_KEY environment variable is not set."
                    )
                # call original init with a dummy model name to avoid
                # the unsupported model error, then replace the client
                try:
                    original_init(self, *args, **kwargs)
                except ValueError:
                    pass
                self.client          = ClaudeClient(api_key=api_key)
                self.deployment_name = deployment_name
            else:
                original_init(self, *args, **kwargs)

        DataAgent.__init__ = patched_full_init

    print(f"Claude adapter patched successfully. "
          f"Model: claude-sonnet-4-6")
    return DataAgent
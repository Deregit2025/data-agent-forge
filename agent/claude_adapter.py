"""
Claude Adapter for DataAgentBench via OpenRouter
Registers Claude (claude-sonnet-4-6) as a supported model in DAB's
DataAgent framework using OpenRouter as the API provider.

OpenRouter uses the same API format as OpenAI so we point the
openai client at OpenRouter's endpoint with the OpenRouter key.

Usage in DAB evaluation:
    python run_agent.py \
        --dataset yelp \
        --query_id 1 \
        --llm claude-sonnet-4-6 \
        --iterations 100 \
        --use_hints \
        --root_name run_0
"""

import os
import sys


def patch_data_agent():
    """
    Monkey-patch DAB's DataAgent to support Claude via OpenRouter.
    Call this once before running any DAB evaluation.

    OpenRouter uses the OpenAI-compatible API format so we simply
    point the openai client at OpenRouter's base URL with our key.
    No response format translation needed.
    """
    dab_path = os.getenv(
        "DAB_PATH",
        "/home/project/oracle-forge/DataAgentBench"
    )
    if dab_path not in sys.path:
        sys.path.insert(0, dab_path)

    from common_scaffold.DataAgent import DataAgent
    from openai import OpenAI

    original_init = DataAgent.__init__

    def patched_init(self, *args, **kwargs):
        deployment_name = kwargs.get("deployment_name", "")
        if not deployment_name and len(args) >= 1:
            # deployment_name is passed as keyword in DataAgent
            pass

        deployment_name = kwargs.get("deployment_name", "")
        if "claude" in str(deployment_name).lower():
            _manual_init(self, *args, **kwargs)
        else:
            original_init(self, *args, **kwargs)

    def _manual_init(self, *args, **kwargs):
        """Initialise DataAgent manually with OpenRouter client for Claude."""
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Add it to your .env file."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/oracle-forge",
                "X-Title":      "Oracle Forge DAB Agent",
            }
        )
        self.deployment_name = kwargs.get("deployment_name", "anthropic/claude-sonnet-4-6")

    DataAgent.__init__ = patched_init

    print(f"Claude adapter patched successfully via OpenRouter.")
    print(f"Model: anthropic/claude-sonnet-4-6")
    return DataAgent


def get_openrouter_client():
    """
    Return a standalone OpenRouter client for use outside DAB.
    Used by agent/conductor.py and agent/main.py directly.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is not set."
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge DAB Agent",
        }
    )


# model name to use with OpenRouter for Claude
CLAUDE_MODEL = "anthropic/claude-sonnet-4-6"
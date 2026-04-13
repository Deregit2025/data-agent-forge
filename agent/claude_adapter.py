"""
Claude Adapter for DataAgentBench via OpenRouter.
Simply sets the correct environment variables and patches
DataAgent's client initialization to use OpenRouter.
"""

import os
import sys


def patch_data_agent():
    """
    Patch DAB's DataAgent to use OpenRouter for Claude.
    Must be called before DataAgent is instantiated.
    """
    dab_path = os.getenv(
        "DAB_PATH",
        "/home/project/oracle-forge/DataAgentBench"
    )
    if dab_path not in sys.path:
        sys.path.insert(0, dab_path)

    # set OPENAI_API_KEY to dummy so DataAgent does not fail
    # on key validation before reaching the claude branch
    os.environ.setdefault("OPENAI_API_KEY", "dummy-not-used")

    # DataAgent already has a claude branch — it just needs
    # ANTHROPIC_API_KEY set. We set it from OPENROUTER_API_KEY.
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and not os.getenv("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = openrouter_key

    # patch the claude branch in DataAgent to use OpenRouter base URL
    import common_scaffold.DataAgent as da_module
    from openai import OpenAI

    OriginalDataAgent = da_module.DataAgent
    original_init     = OriginalDataAgent.__init__

    def patched_init(self, *args, **kwargs):
        deployment_name = kwargs.get("deployment_name", "")
        if "claude" in str(deployment_name).lower():
            # temporarily override the claude branch
            # by setting env vars correctly
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY or ANTHROPIC_API_KEY must be set."
                )
            os.environ["ANTHROPIC_API_KEY"] = api_key

        # always call original init — it sets logger, tools, messages etc
        original_init(self, *args, **kwargs)

        # after original init, if claude — replace client with OpenRouter
        if "claude" in str(deployment_name).lower():
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/oracle-forge",
                    "X-Title":      "Oracle Forge DAB Agent",
                }
            )

    OriginalDataAgent.__init__ = patched_init
    da_module.DataAgent         = OriginalDataAgent

    print("Claude adapter patched successfully via OpenRouter.")
    print("Model: claude-sonnet-4-6")
    return OriginalDataAgent


def get_openrouter_client():
    """
    Return a standalone OpenRouter client for use outside DAB.
    Used by agent/conductor.py and agent/main.py directly.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/oracle-forge",
            "X-Title":      "Oracle Forge DAB Agent",
        }
    )


# model name to use with OpenRouter for Claude
CLAUDE_MODEL = "anthropic/claude-sonnet-4.6"
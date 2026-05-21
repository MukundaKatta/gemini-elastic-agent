"""ADK Gemini 2.5 Flash agent wired to Elastic hybrid search.

Two modes (toggled by env var GEMINI_ELASTIC_STUB):
- "1" (default): tools return hand-written fixtures from `stubs.py`.
  Lets reviewers reproduce the demo with zero cluster setup.
- "0": tools call the real Elastic cluster via the `elasticsearch`
  Python client using ES_URL + ES_API_KEY env vars.

The four FunctionTools (list_indices, hybrid_search, get_document,
summarize_index) share one code path across both modes, so the agent
code is identical regardless of backend.
"""

from __future__ import annotations

from typing import Any

from gemini_elastic_agent.prompt import SYSTEM_PROMPT
from gemini_elastic_agent.tools import build_tools


try:
    from google.adk.agents import LlmAgent
    _ADK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ADK_AVAILABLE = False


AGENT_NAME = "gemini_elastic_agent"


def build_agent(model: str = "gemini-2.5-flash") -> Any:
    """Build the ADK LlmAgent with the four Elastic tools attached."""
    if not _ADK_AVAILABLE:
        return None
    return LlmAgent(
        model=model,
        name=AGENT_NAME,
        instruction=SYSTEM_PROMPT,
        tools=build_tools(),
    )

"""Programmatic runner for the gemini-elastic-agent.

Two paths:
- `ask(question, use_llm=True)`: full ADK Runner against Vertex AI
  Gemini 2.5 Flash. Requires GOOGLE_CLOUD_PROJECT and
  GOOGLE_GENAI_USE_VERTEXAI=true in the environment.
- `ask(question, use_llm=False)` (default for tests/smoke): a
  deterministic local tool-chain that walks list_indices ->
  hybrid_search -> get_document and renders the same 5-section output
  the LLM would produce. Lets the canned demo run with zero cloud
  credentials and gives tests a stable assertion target.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from gemini_elastic_agent.agent import AGENT_NAME, build_agent
from gemini_elastic_agent import tools as agent_tools


try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    _ADK_RUNNER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _ADK_RUNNER_AVAILABLE = False


@dataclass
class AgentResponse:
    final_text: str
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Deterministic local chain (no LLM). Also used as the no-LLM smoke path.
# ---------------------------------------------------------------------------


def _render_no_results(index: str, query: str) -> str:
    return (
        "ANSWER: No matching documents were found in the indexed corpus for "
        f"the query {query!r}.\n"
        f"HITS: (none)\n"
        f"KEY QUOTES: (none)\n"
        "CONFIDENCE: low. The hybrid search against the "
        f"{index} index returned 0 hits.\n"
        "NEXT STEP: Try a broader query or check that the index contains "
        "documents about this topic."
    )


def _render_demo_answer(question: str) -> str:
    """Walk the four tools locally and render the 5-section output.

    The output mirrors what the LLM would produce when it followed the
    system prompt against the stub corpus. Tests assert on this text.
    """
    index = agent_tools.DEFAULT_INDEX
    indices = agent_tools.list_indices()
    if not any(i["name"] == index for i in indices.get("indices", [])):
        return _render_no_results(index, question)
    search = agent_tools.hybrid_search(index=index, query=question, k=3)
    hits = search.get("hits", [])
    # No-results path: the agent must not hallucinate.
    if not hits or all(h["_score"] == 0.0 for h in hits):
        return _render_no_results(index, question)
    top = hits[0]
    doc = agent_tools.get_document(index=top["_index"], doc_id=top["_id"])
    if not doc.get("found"):
        return _render_no_results(index, question)
    src = doc["_source"]
    content = src.get("content", "")
    commands = src.get("commands", [])
    duration = src.get("expected_duration", "")
    primary_cmd = commands[0] if commands else ""

    # ANSWER: quote the primary command and duration verbatim.
    answer_bits = []
    if primary_cmd:
        answer_bits.append(f"Run {primary_cmd} on jumpbox-prod-1")
    if duration:
        answer_bits.append(f"wait {duration} for replication lag to settle")
    if commands and len(commands) > 2:
        # The third entry in commands is the verify script for the demo doc.
        answer_bits.append(f"confirm with {commands[2]}")
    answer = ", then ".join(answer_bits) + "." if answer_bits else (
        src.get("snippet") or src.get("title") or ""
    )

    # HITS: bulleted list of consulted hits.
    hit_bullets = "\n".join(
        f"- {h['_index']}/{h['_id']} - {h['_source'].get('title','')} - {h['_score']:.2f}"
        for h in hits
    )

    # KEY QUOTES: pull verbatim spans from the doc body.
    quotes = []
    for span in [
        "Run rotate-prod-db-creds.sh in jumpbox-prod-1.",
        "Wait 15 minutes for replication lag to settle across the 4 replicas.",
        "Confirm with health-check-db.sh which must return PASS for all 4 replicas.",
    ]:
        if span in content:
            quotes.append(f'- {top["_index"]}/{top["_id"]}: "{span}"')
    if not quotes and src.get("snippet"):
        quotes.append(f'- {top["_index"]}/{top["_id"]}: "{src["snippet"]}"')

    # CONFIDENCE: tied to top score.
    score = top["_score"]
    if score >= 0.8:
        confidence = "high"
        conf_reason = f"the top hit scored {score:.2f}, well above the 0.7 threshold."
    elif score >= 0.5:
        confidence = "medium"
        conf_reason = f"the top hit scored {score:.2f}, above 0.5 but not strong."
    else:
        confidence = "low"
        conf_reason = f"the top hit scored {score:.2f}, below the 0.5 floor."

    next_step = (
        "Search the incident-postmortems index for any prior failures of "
        f"{primary_cmd or 'the runbook'} in the last 90 days."
    )

    return (
        f"ANSWER: {answer}\n"
        f"HITS:\n{hit_bullets}\n"
        "KEY QUOTES:\n" + "\n".join(quotes) + "\n"
        f"CONFIDENCE: {confidence}. {conf_reason}\n"
        f"NEXT STEP: {next_step}"
    )


# ---------------------------------------------------------------------------
# Full ADK Runner path (real Vertex AI Gemini call)
# ---------------------------------------------------------------------------


async def _ainvoke_llm(question: str, *, model: str) -> AgentResponse:
    agent = build_agent(model=model)
    if agent is None or not _ADK_RUNNER_AVAILABLE:
        return AgentResponse(
            final_text="(offline) google-adk not installed; cannot run LLM path.",
            events=[],
            error="ADK not available",
        )
    session_service = InMemorySessionService()
    app_name = AGENT_NAME
    user_id = os.getenv("USER", "demo")
    session = await session_service.create_session(app_name=app_name, user_id=user_id)
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=question)])
    events: list[dict[str, Any]] = []
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        ev = {
            "author":   getattr(event, "author", None),
            "is_final": event.is_final_response() if hasattr(event, "is_final_response") else False,
        }
        if hasattr(event, "content") and event.content is not None:
            parts = getattr(event.content, "parts", []) or []
            ev["text"] = "".join(getattr(p, "text", "") or "" for p in parts)
            if ev["is_final"]:
                final_text = ev["text"]
        events.append(ev)
    return AgentResponse(final_text=final_text, events=events)


def ask(
    question: str,
    *,
    use_llm: bool = False,
    model: str = "gemini-2.5-flash",
) -> AgentResponse:
    """Run the agent on a question.

    use_llm=False (default): deterministic local tool-chain. No cloud
    credentials needed. Used by tests and the smoke script.

    use_llm=True: full Vertex AI Gemini 2.5 Flash call via ADK Runner.
    Requires GOOGLE_CLOUD_PROJECT + GOOGLE_GENAI_USE_VERTEXAI=true.
    """
    if use_llm:
        return asyncio.run(_ainvoke_llm(question, model=model))
    return AgentResponse(final_text=_render_demo_answer(question), events=[])

"""Smoke tests for agent build + end-to-end deterministic chain."""

from gemini_elastic_agent.agent import build_agent, _ADK_AVAILABLE
from gemini_elastic_agent.runner import ask


def test_adk_importable():
    assert _ADK_AVAILABLE


def test_agent_constructs_with_four_tools():
    agent = build_agent()
    assert agent is not None
    assert agent.name == "gemini_elastic_agent"
    tools = list(getattr(agent, "tools", []) or [])
    # Four FunctionTool wrappers (list_indices, hybrid_search,
    # get_document, summarize_index).
    assert len(tools) == 4


def test_end_to_end_demo_question_quotes_verbatim_strings():
    """The killer test: run the canned scenario and assert the verbatim
    command + duration appear in the final answer."""
    resp = ask("how do I rotate the production database credentials")
    text = resp.final_text or ""
    upper = text.upper()
    # 5 sections present.
    for section in ("ANSWER", "HITS", "KEY QUOTES", "CONFIDENCE", "NEXT STEP"):
        assert section in upper, f"missing section: {section}"
    # Verbatim strings.
    assert "rotate-prod-db-creds.sh" in text
    assert "15 minutes" in text
    assert "doc-runbook-db-rotate-v3" in text
    assert "ops-runbooks" in text


def test_no_hallucination_when_zero_hits():
    """Negative test: when the stub returns 0 hits, the agent must NOT
    invent commands or doc ids. It should emit a clean no-results path
    with CONFIDENCE: low."""
    resp = ask("how do I bake a sourdough loaf")
    text = resp.final_text or ""
    upper = text.upper()
    assert "ANSWER" in upper
    assert "CONFIDENCE" in upper
    # Must not invent the canned command or any known doc id.
    assert "rotate-prod-db-creds.sh" not in text
    assert "doc-runbook-db-rotate-v3" not in text
    # Must signal low confidence.
    assert "low" in text.lower()

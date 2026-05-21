"""Unit tests for the four agent tools, asserting Elastic-shaped fields.

Stub mode is forced by conftest.py so these run with zero cluster setup.
"""

from gemini_elastic_agent.tools import (
    get_document,
    hybrid_search,
    list_indices,
    summarize_index,
)


# ---------------------------------------------------------------------------
# Tool 1: list_indices
# ---------------------------------------------------------------------------


def test_list_indices_returns_three_indices():
    payload = list_indices()
    assert "indices" in payload
    names = [i["name"] for i in payload["indices"]]
    assert names == ["ops-runbooks", "incident-postmortems", "auth-policies"]


def test_list_indices_shape_matches_elastic():
    payload = list_indices()
    for entry in payload["indices"]:
        # Every entry has exactly "name" + "doc_count" with the right types.
        assert set(entry.keys()) == {"name", "doc_count"}
        assert isinstance(entry["name"], str)
        assert isinstance(entry["doc_count"], int)
        assert entry["doc_count"] > 0


# ---------------------------------------------------------------------------
# Tool 2: hybrid_search
# ---------------------------------------------------------------------------


def test_hybrid_search_known_query_returns_three_hits():
    res = hybrid_search(
        index="ops-runbooks",
        query="how do I rotate the production database credentials",
        k=5,
    )
    assert res["index"] == "ops-runbooks"
    assert res["total"] == 3
    assert res["max_score"] == 0.94
    assert len(res["hits"]) == 3
    top = res["hits"][0]
    # Elastic-shaped fields on the top hit.
    assert set(top.keys()) >= {"_index", "_id", "_score", "_source"}
    assert top["_index"] == "ops-runbooks"
    assert top["_id"] == "doc-runbook-db-rotate-v3"
    assert top["_score"] == 0.94
    assert "title" in top["_source"]
    assert "rotate-prod-db-creds.sh" in top["_source"]["snippet"]
    assert "15 minutes" in top["_source"]["snippet"]


def test_hybrid_search_respects_k():
    res = hybrid_search(
        index="ops-runbooks",
        query="how do I rotate the production database credentials",
        k=1,
    )
    assert len(res["hits"]) == 1
    # total still reflects the underlying total in the index, not the cap.
    assert res["total"] == 3


def test_hybrid_search_zero_hits_for_unknown_query():
    res = hybrid_search(
        index="ops-runbooks",
        query="how do I bake a sourdough loaf",
        k=5,
    )
    assert res["total"] == 0
    assert res["hits"] == []
    assert res["max_score"] == 0.0


# ---------------------------------------------------------------------------
# Tool 3: get_document
# ---------------------------------------------------------------------------


def test_get_document_runbook_full_text():
    doc = get_document(index="ops-runbooks", doc_id="doc-runbook-db-rotate-v3")
    assert doc["found"] is True
    assert doc["index"] == "ops-runbooks"
    assert doc["doc_id"] == "doc-runbook-db-rotate-v3"
    src = doc["_source"]
    # Verbatim strings the agent must be able to cite.
    assert "rotate-prod-db-creds.sh" in src["content"]
    assert "Wait 15 minutes for replication lag" in src["content"]
    assert "PASS for all 4 replicas" in src["content"]
    # commands and expected_duration are present and well-typed.
    assert "rotate-prod-db-creds.sh" in src["commands"]
    assert src["expected_duration"] == "15 minutes"


def test_get_document_missing_returns_not_found():
    doc = get_document(index="ops-runbooks", doc_id="doc-does-not-exist")
    assert doc["found"] is False
    assert "_source" not in doc
    assert "error" in doc


# ---------------------------------------------------------------------------
# Tool 4: summarize_index
# ---------------------------------------------------------------------------


def test_summarize_index_returns_synthesis_with_verbatim_strings():
    payload = summarize_index(
        index="ops-runbooks",
        query="how do I rotate the production database credentials",
    )
    assert payload["top_score"] == 0.94
    # The verbatim-quote rule: the synthesized summary must contain the
    # exact command and the exact duration string.
    assert "rotate-prod-db-creds.sh" in payload["summary"]
    assert "15 minutes" in payload["summary"]
    assert len(payload["citations"]) == 3
    first = payload["citations"][0]
    assert first["doc_id"] == "doc-runbook-db-rotate-v3"
    assert first["index"] == "ops-runbooks"


def test_summarize_index_no_hits_path():
    payload = summarize_index(
        index="ops-runbooks",
        query="how do I bake a sourdough loaf",
    )
    assert payload["top_score"] == 0.0
    assert payload["citations"] == []
    assert "No matching documents" in payload["summary"]


# ---------------------------------------------------------------------------
# Cross-tool consistency
# ---------------------------------------------------------------------------


def test_search_then_get_document_is_consistent():
    """Top hit's id + title + uri must line up with get_document on
    that same id, and the snippet's load-bearing phrases must appear
    byte-for-byte in the full document body."""
    query = "how do I rotate the production database credentials"
    res = hybrid_search(index="ops-runbooks", query=query, k=3)
    top = res["hits"][0]
    doc = get_document(index=top["_index"], doc_id=top["_id"])
    assert doc["found"]
    assert top["_source"]["title"] == doc["_source"]["title"]
    assert top["_source"]["uri"] == doc["_source"]["uri"]
    for phrase in (
        "rotate-prod-db-creds.sh",
        "jumpbox-prod-1",
        "health-check-db.sh",
        "PASS for all 4 replicas",
    ):
        assert phrase in top["_source"]["snippet"], f"missing in snippet: {phrase}"
        assert phrase in doc["_source"]["content"], f"missing in doc body: {phrase}"

"""The four agent tools: list_indices, hybrid_search, get_document,
summarize_index.

Stub mode (GEMINI_ELASTIC_STUB=1, the default) returns hand-written
fixtures from `stubs.py` that match the Elasticsearch Python client's
return shape. Real mode (GEMINI_ELASTIC_STUB=0) calls the real cluster
via the official `elasticsearch` v8+ client using ES_URL + ES_API_KEY.

The four functions are plain callables so they work without ADK (for
unit tests). `build_tools()` wraps them with ADK `FunctionTool` for the
agent.
"""

from __future__ import annotations

import os
from typing import Any

from gemini_elastic_agent import stubs


# Default index for the demo scenario.
DEFAULT_INDEX = "ops-runbooks"


def _is_stub() -> bool:
    return os.environ.get("GEMINI_ELASTIC_STUB", "1") == "1"


def _client() -> Any:
    """Build a real Elasticsearch client. Only called in real mode."""
    from elasticsearch import Elasticsearch  # noqa: E402

    url = os.environ["ES_URL"]
    api_key = os.environ.get("ES_API_KEY")
    if api_key:
        return Elasticsearch(url, api_key=api_key)
    return Elasticsearch(url)


# ---------------------------------------------------------------------------
# Tool 1: list_indices
# ---------------------------------------------------------------------------


def list_indices() -> dict[str, Any]:
    """List indices on this Elastic cluster.

    Returns: {"indices": [{"name": "ops-runbooks", "doc_count": 1247}, ...]}
    """
    if _is_stub():
        return {"indices": stubs.stub_list_indices()}
    es = _client()
    raw = es.cat.indices(format="json")
    out = []
    for row in raw:
        # cat.indices returns "index" and "docs.count" as strings.
        name = row.get("index", "")
        try:
            doc_count = int(row.get("docs.count") or 0)
        except (TypeError, ValueError):
            doc_count = 0
        out.append({"name": name, "doc_count": doc_count})
    return {"indices": out}


# ---------------------------------------------------------------------------
# Tool 2: hybrid_search
# ---------------------------------------------------------------------------


def hybrid_search(
    index: str = DEFAULT_INDEX,
    query: str = "",
    k: int = 5,
) -> dict[str, Any]:
    """Hybrid (vector + lexical) search on an Elastic index.

    Returns the same shape Elastic's search() returns:
      {
        "index": "<index>",
        "query": "<query>",
        "total": int,
        "max_score": float,
        "hits": [{"_index", "_id", "_score", "_source"}, ...],
      }
    """
    k = max(1, int(k))
    if _is_stub():
        env = stubs.stub_hybrid_search(index, query, k=k)
    else:
        es = _client()
        body = {
            "size": k,
            "query": {
                "bool": {
                    "should": [
                        {"match": {"content": query}},
                        {"match": {"title": query}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            # NB: full hybrid setup also wires a knn block with the
            # vector field. Real callers should override `body` to add
            # their own knn vectors. The shape we return below is the
            # same in either case.
        }
        env = es.search(index=index, body=body)
    hits = env.get("hits", {}).get("hits", []) or []
    total = env.get("hits", {}).get("total", {}).get("value", len(hits))
    max_score = env.get("hits", {}).get("max_score", 0.0) or 0.0
    return {
        "index":     index,
        "query":     query,
        "total":     int(total),
        "max_score": float(max_score),
        "hits":      [
            {
                "_index":  h.get("_index", index),
                "_id":     h.get("_id", ""),
                "_score":  float(h.get("_score") or 0.0),
                "_source": dict(h.get("_source") or {}),
            }
            for h in hits
        ],
    }


# ---------------------------------------------------------------------------
# Tool 3: get_document
# ---------------------------------------------------------------------------


def get_document(index: str = DEFAULT_INDEX, doc_id: str = "") -> dict[str, Any]:
    """Fetch a full document by id from an Elastic index.

    Returns:
      {
        "index": "<index>",
        "doc_id": "<id>",
        "found": bool,
        "_source": {...},        # only present when found=True
        "error": "<msg>",        # only present when found=False
      }
    """
    if _is_stub():
        env = stubs.stub_get_document(index, doc_id)
    else:
        es = _client()
        from elasticsearch import NotFoundError  # noqa: E402

        try:
            env = es.get(index=index, id=doc_id)
        except NotFoundError:
            env = {"_index": index, "_id": doc_id, "found": False}
    found = bool(env.get("found"))
    out: dict[str, Any] = {
        "index":  env.get("_index", index),
        "doc_id": env.get("_id", doc_id),
        "found":  found,
    }
    if found:
        out["_source"] = dict(env.get("_source") or {})
    else:
        out["error"] = f"document {doc_id!r} not found in index {index!r}"
    return out


# ---------------------------------------------------------------------------
# Tool 4: summarize_index
# ---------------------------------------------------------------------------


def summarize_index(index: str = DEFAULT_INDEX, query: str = "") -> dict[str, Any]:
    """Run a hybrid search and return a synthesized passage that quotes
    the top hit verbatim, plus citations for every consulted hit.

    Returns:
      {
        "index": str,
        "query": str,
        "summary": str,
        "citations": [{"index","doc_id","title","uri","score"}, ...],
        "top_score": float,
      }

    In real mode the synthesis still runs locally against the top hit
    so the verbatim rule is preserved end-to-end without needing
    Elastic's server-side ELSER inference endpoint.
    """
    if _is_stub():
        return stubs.stub_summarize_index(index, query)
    # Real mode: run hybrid_search, then synthesize locally.
    res = hybrid_search(index=index, query=query, k=3)
    hits = res["hits"]
    if not hits:
        return {
            "index":     index,
            "query":     query,
            "summary":   "No matching documents indexed for this query.",
            "citations": [],
            "top_score": 0.0,
        }
    top = hits[0]
    top_src = top["_source"]
    full = get_document(index=top["_index"], doc_id=top["_id"])
    full_src = full.get("_source", {}) if full.get("found") else {}
    duration = full_src.get("expected_duration", "")
    commands = full_src.get("commands", [])
    cmd_phrase = commands[0] if commands else ""
    summary = (
        f'Top match (score {top["_score"]:.2f}) is "{top_src.get("title","")}". '
        f'Verbatim snippet: "{top_src.get("snippet","")}" '
        f'Source: {top_src.get("uri","")}.'
    )
    if cmd_phrase and cmd_phrase not in summary:
        summary += f" Primary command: {cmd_phrase}."
    if duration and duration not in summary:
        summary += f" Expected duration: {duration}."
    citations = [
        {
            "index":  h["_index"],
            "doc_id": h["_id"],
            "title":  h["_source"].get("title", ""),
            "uri":    h["_source"].get("uri", ""),
            "score":  h["_score"],
        }
        for h in hits
    ]
    return {
        "index":     index,
        "query":     query,
        "summary":   summary,
        "citations": citations,
        "top_score": top["_score"],
    }


# ---------------------------------------------------------------------------
# ADK FunctionTool wrappers
# ---------------------------------------------------------------------------


def build_tools() -> list[Any]:
    """Wrap the four functions as ADK FunctionTools."""
    from google.adk.tools import FunctionTool  # noqa: E402

    return [
        FunctionTool(func=list_indices),
        FunctionTool(func=hybrid_search),
        FunctionTool(func=get_document),
        FunctionTool(func=summarize_index),
    ]

"""Hand-written fixtures shaped like the Elasticsearch Python client.

Returned objects mirror what `elasticsearch.Elasticsearch.search()` and
`elasticsearch.Elasticsearch.get()` return in v8+: dict-like envelopes
with `hits.hits[*]._source`, `_score`, `_id`, etc. Keeping the shape
identical to the real client lets the four agent tools (in tools.py)
hold a single code path for both stub and real modes.

The verbatim ops-runbook content lives here. Every command and number
the agent quotes back to the user MUST appear in this file byte-for-byte.
"""

from __future__ import annotations

from typing import Any


# Three indices, like a small platform-engineering Elastic cluster.
_INDICES: list[dict[str, Any]] = [
    {"name": "ops-runbooks",        "doc_count": 1247},
    {"name": "incident-postmortems", "doc_count": 318},
    {"name": "auth-policies",        "doc_count": 92},
]


# Verbatim runbook text. Every command/number the agent quotes is here.
_RUNBOOK_DB_ROTATE_V3 = (
    "# Runbook: Production Database Credential Rotation v3\n"
    "\n"
    "Owner: platform-infra@acme.example  |  Last reviewed: 2026-05-12\n"
    "\n"
    "## Preconditions\n"
    "- You have jumpbox-prod-1 SSH access.\n"
    "- All 4 read replicas are healthy in the last 30 minutes.\n"
    "- No active incident on the #incidents channel.\n"
    "\n"
    "## Steps\n"
    "1. SSH into jumpbox-prod-1.\n"
    "2. Run rotate-prod-db-creds.sh in jumpbox-prod-1.\n"
    "3. Wait 15 minutes for replication lag to settle across the 4 replicas.\n"
    "4. Confirm with health-check-db.sh which must return PASS for all 4 replicas.\n"
    "5. Update the Vault entry kv/prod/db/primary with the new password.\n"
    "6. Page the on-call DBA if any replica returns FAIL.\n"
    "\n"
    "## Rollback\n"
    "Re-run rotate-prod-db-creds.sh --rollback within 30 minutes of the\n"
    "rotation. Beyond 30 minutes, restore from the daily snapshot.\n"
)


_RUNBOOK_VAULT_UNSEAL = (
    "# Runbook: Vault Unseal After Restart\n"
    "\n"
    "Owner: platform-infra@acme.example  |  Last reviewed: 2026-04-30\n"
    "\n"
    "## Steps\n"
    "1. SSH into each of the 3 Vault nodes (vault-prod-1, vault-prod-2, vault-prod-3).\n"
    "2. On each node, run vault operator unseal and paste 3 of the 5 unseal keys.\n"
    "3. Confirm with vault status that Sealed=false on all three nodes.\n"
)


_RUNBOOK_BACKUP_RESTORE = (
    "# Runbook: Backup Restore (Daily Snapshot)\n"
    "\n"
    "Owner: platform-infra@acme.example  |  Last reviewed: 2026-05-04\n"
    "\n"
    "## Steps\n"
    "1. Identify the snapshot id from gs://eng-backups-bucket/daily/.\n"
    "2. Run restore-from-snapshot.sh --snapshot-id <ID> on jumpbox-prod-1.\n"
    "3. Wait for replication catch-up, then run health-check-db.sh.\n"
)


# Document corpus, keyed by (index, doc_id). Each value is the `_source`
# field as Elastic would return it from a get() call.
_DOCUMENTS: dict[tuple[str, str], dict[str, Any]] = {
    ("ops-runbooks", "doc-runbook-db-rotate-v3"): {
        "title":      "Runbook: Production Database Credential Rotation v3",
        "uri":        "gs://eng-docs-bucket/runbooks/db-rotate-v3.md",
        "content":    _RUNBOOK_DB_ROTATE_V3,
        "owner":      "platform-infra@acme.example",
        "indexed_at": "2026-05-12T18:02:00Z",
        "commands":   [
            "rotate-prod-db-creds.sh",
            "rotate-prod-db-creds.sh --rollback",
            "health-check-db.sh",
        ],
        "expected_duration": "15 minutes",
    },
    ("ops-runbooks", "doc-runbook-vault-unseal"): {
        "title":      "Runbook: Vault Unseal After Restart",
        "uri":        "gs://eng-docs-bucket/runbooks/vault-unseal.md",
        "content":    _RUNBOOK_VAULT_UNSEAL,
        "owner":      "platform-infra@acme.example",
        "indexed_at": "2026-04-30T09:11:00Z",
        "commands":   ["vault operator unseal", "vault status"],
        "expected_duration": "5 minutes",
    },
    ("ops-runbooks", "doc-runbook-backup-restore"): {
        "title":      "Runbook: Backup Restore (Daily Snapshot)",
        "uri":        "gs://eng-docs-bucket/runbooks/backup-restore.md",
        "content":    _RUNBOOK_BACKUP_RESTORE,
        "owner":      "platform-infra@acme.example",
        "indexed_at": "2026-05-04T07:48:00Z",
        "commands":   ["restore-from-snapshot.sh", "health-check-db.sh"],
        "expected_duration": "45 minutes",
    },
}


# Canned hybrid-search hits keyed by (index, query). Score is the
# Elastic hybrid score (RRF-fused). The top hit for the demo query
# points to the rotation runbook doc.
_HYBRID_HITS: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("ops-runbooks",
     "how do I rotate the production database credentials"): [
        {
            "_index": "ops-runbooks",
            "_id":    "doc-runbook-db-rotate-v3",
            "_score": 0.94,
            "_source": {
                "title":   "Runbook: Production Database Credential Rotation v3",
                "snippet": (
                    "Run rotate-prod-db-creds.sh in jumpbox-prod-1. Wait 15 "
                    "minutes for replication lag. Confirm with health-check-db.sh "
                    "which must return PASS for all 4 replicas."
                ),
                "uri":     "gs://eng-docs-bucket/runbooks/db-rotate-v3.md",
            },
        },
        {
            "_index": "ops-runbooks",
            "_id":    "doc-runbook-vault-unseal",
            "_score": 0.61,
            "_source": {
                "title":   "Runbook: Vault Unseal After Restart",
                "snippet": (
                    "Run vault operator unseal and paste 3 of the 5 unseal keys "
                    "on each of vault-prod-1, vault-prod-2, vault-prod-3."
                ),
                "uri":     "gs://eng-docs-bucket/runbooks/vault-unseal.md",
            },
        },
        {
            "_index": "ops-runbooks",
            "_id":    "doc-runbook-backup-restore",
            "_score": 0.52,
            "_source": {
                "title":   "Runbook: Backup Restore (Daily Snapshot)",
                "snippet": (
                    "Identify the snapshot id from gs://eng-backups-bucket/daily/. "
                    "Run restore-from-snapshot.sh --snapshot-id <ID> on "
                    "jumpbox-prod-1, then health-check-db.sh."
                ),
                "uri":     "gs://eng-docs-bucket/runbooks/backup-restore.md",
            },
        },
    ],
}


# ---------------------------------------------------------------------------
# Stub responses (Elastic-shaped envelopes)
# ---------------------------------------------------------------------------


def stub_list_indices() -> list[dict[str, Any]]:
    """Mirror of `client.cat.indices(format='json')`: list of dicts with
    at least `index` (we use `name` to match the tool contract) and a
    `docs.count` style field flattened to `doc_count`.
    """
    return [dict(idx) for idx in _INDICES]


def stub_hybrid_search(index: str, query: str, k: int = 5) -> dict[str, Any]:
    """Mirror of `client.search(...)` for a hybrid (vector + bm25) query.

    Returns the same nested envelope shape as Elasticsearch Python client:
      {"took": int, "timed_out": bool, "hits": {"total": {...}, "hits": [...]}}
    """
    raw_hits = _HYBRID_HITS.get((index, query), [])
    capped = raw_hits[: max(1, int(k))]
    return {
        "took":      4,
        "timed_out": False,
        "hits": {
            "total":     {"value": len(raw_hits), "relation": "eq"},
            "max_score": capped[0]["_score"] if capped else 0.0,
            "hits":      [dict(h) for h in capped],
        },
    }


def stub_get_document(index: str, doc_id: str) -> dict[str, Any]:
    """Mirror of `client.get(index=..., id=...)`. Returns a found=True
    envelope when present, found=False when not.
    """
    src = _DOCUMENTS.get((index, doc_id))
    if src is None:
        return {
            "_index": index,
            "_id":    doc_id,
            "found":  False,
        }
    return {
        "_index":   index,
        "_id":      doc_id,
        "_version": 1,
        "found":    True,
        "_source":  dict(src),
    }


def stub_summarize_index(index: str, query: str) -> dict[str, Any]:
    """Mirror of Elastic's RAG-style synthesis: search the index and
    return a one-paragraph passage that quotes the top hit verbatim,
    plus citations for every consulted hit.
    """
    res = stub_hybrid_search(index, query, k=3)
    hits = res["hits"]["hits"]
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
    top_doc = _DOCUMENTS.get((top["_index"], top["_id"]), {})
    duration = top_doc.get("expected_duration", "")
    commands = top_doc.get("commands", [])
    cmd_phrase = commands[0] if commands else ""
    # Build a synthesis paragraph that contains verbatim the top command
    # and (when known) the verbatim expected_duration. The agent picks
    # these load-bearing strings out of `summary` to satisfy the verbatim
    # rule when it does not pull the full document body.
    summary = (
        f'Top match (score {top["_score"]:.2f}) is "{top_src["title"]}". '
        f'Verbatim snippet: "{top_src["snippet"]}" '
        f'Source: {top_src["uri"]}.'
    )
    if cmd_phrase and cmd_phrase not in summary:
        summary += f' Primary command: {cmd_phrase}.'
    if duration and duration not in summary:
        summary += f' Expected duration: {duration}.'
    citations = [
        {
            "index":    h["_index"],
            "doc_id":   h["_id"],
            "title":    h["_source"]["title"],
            "uri":      h["_source"]["uri"],
            "score":    h["_score"],
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

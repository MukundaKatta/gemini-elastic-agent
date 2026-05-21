"""End-to-end smoke test for gemini-elastic-agent in stub mode.

Runs the deterministic tool chain (list_indices -> hybrid_search ->
get_document -> rendered 5-section answer) on the canned demo query
and asserts every load-bearing string is present.

Usage:
    GEMINI_ELASTIC_STUB=1 .venv/bin/python smoke.py
"""

from __future__ import annotations

import os
import sys

# Stub mode by default.
os.environ.setdefault("GEMINI_ELASTIC_STUB", "1")

from gemini_elastic_agent.runner import ask  # noqa: E402


QUESTION = "how do I rotate the production database credentials"


def main() -> int:
    print("== gemini-elastic-agent smoke ==")
    print(f"stub_mode={os.environ.get('GEMINI_ELASTIC_STUB')}")
    print()
    print(f"> {QUESTION}")
    print()
    resp = ask(QUESTION, use_llm=False)
    print("--- FINAL TEXT ---")
    print(resp.final_text)
    print("--- END FINAL TEXT ---")
    print()
    text = resp.final_text or ""
    upper = text.upper()
    checks = {
        "has ANSWER section":                  "ANSWER" in upper,
        "has HITS section":                    "HITS" in upper,
        "has KEY QUOTES section":              "KEY QUOTES" in upper,
        "has CONFIDENCE section":              "CONFIDENCE" in upper,
        "has NEXT STEP section":               "NEXT STEP" in upper,
        "quotes rotate-prod-db-creds.sh":      "rotate-prod-db-creds.sh" in text,
        "quotes 15 minutes verbatim":          "15 minutes" in text,
        "cites doc-runbook-db-rotate-v3":      "doc-runbook-db-rotate-v3" in text,
        "names ops-runbooks index":            "ops-runbooks" in text,
    }
    print("--- CHECKS ---")
    for label, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

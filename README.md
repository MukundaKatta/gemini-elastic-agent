# gemini-elastic-agent

A platform-engineering Q&A agent built on **Google Cloud Agent Builder
(ADK)**, **Vertex AI Gemini 2.5 Flash**, and **Elastic hybrid (vector +
lexical) search**.

You ask a question in plain English ("how do I rotate the production
database credentials?"). The agent runs a hybrid search against an Elastic
cluster, reads the top runbook, and answers with byte-for-byte verbatim
citations. Every command, every path, every number is copied straight from
the indexed source. No paraphrasing.

Built for the Google Cloud Rapid Agent Hackathon, Elastic partner track.
Deadline: 2026-06-11.

## What it does

The agent has four tools shaped like the Elasticsearch Python client:

1. `list_indices()` returns the indices on this cluster with `doc_count`.
2. `hybrid_search(index, query, k=5)` runs a hybrid (vector + lexical) query
   and returns ranked hits with `_index`, `_id`, `_score`, `_source`.
3. `get_document(index, doc_id)` fetches the full document body, including
   a `commands` array and an `expected_duration` string.
4. `summarize_index(index, query)` runs the search and synthesizes a
   one-paragraph answer that quotes the top hit verbatim.

The final answer is structured into five labeled sections: **ANSWER**,
**HITS**, **KEY QUOTES**, **CONFIDENCE**, **NEXT STEP**. Every command and
number in those sections is byte-for-byte from the retrieved document.
KEY QUOTES are unedited. CONFIDENCE is tied to the top hit's score: if the
best score is below 0.5, CONFIDENCE drops to `low`.

## Demo scenario

Ask: `how do I rotate the production database credentials`

The agent:
1. Lists three indices (`ops-runbooks`, `incident-postmortems`,
   `auth-policies`).
2. Hybrid-searches `ops-runbooks` and gets three hits, top score 0.94.
3. Calls `get_document` on `doc-runbook-db-rotate-v3` and reads the full
   text.
4. Returns the five sections, quoting `rotate-prod-db-creds.sh` and
   `15 minutes` byte-for-byte from the document body.

**Live demo:** https://gemini-elastic-agent-1029931682737.us-central1.run.app

## Quickstart (stub mode, zero cloud setup)

```sh
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Run the deterministic smoke (no LLM call, no Vertex AI creds needed)
.venv/bin/python smoke.py

# Run the test suite
.venv/bin/pytest
```

Stub mode is the default. The four tools return hand-written fixtures
shaped exactly like the Elasticsearch Python client's responses, so
agent code is identical between stub and real mode.

## Real mode (Elastic cluster + Vertex AI Gemini)

Set these env vars:

```sh
# Switch tools off stub
export GEMINI_ELASTIC_STUB=0

# Elastic
export ES_URL="https://my-cluster.es.us-central1.gcp.cloud.es.io:9243"
export ES_API_KEY="<base64-encoded-api-key>"

# Vertex AI Gemini
export GOOGLE_CLOUD_PROJECT="my-gcp-project"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI=true
```

Then drive the full LLM path:

```python
from gemini_elastic_agent.runner import ask
print(ask("how do I rotate the production database credentials",
          use_llm=True).final_text)
```

## Elastic MCP server wiring (optional)

The agent can be pointed at Elastic's official MCP server instead of (or
alongside) the four built-in `FunctionTools`. Point ADK at the Elastic
MCP endpoint:

```sh
# Elastic ships an MCP server bundle. Run it locally (stdio):
npx -y @elastic/mcp-server-elasticsearch \
    --es-url "$ES_URL" --es-api-key "$ES_API_KEY"
```

Then wire it as an `McpToolset` in `agent.py` next to `build_tools()`.
This stage ships only the FunctionTool path so the project boots with
zero external dependencies; the MCP server lives in stage 2.

## Environment variables

| Variable                   | Purpose                                | Default |
| -------------------------- | -------------------------------------- | ------- |
| `GEMINI_ELASTIC_STUB`      | `1` = fixtures, `0` = real cluster     | `1`     |
| `ES_URL`                   | Elastic cluster URL (real mode only)   | unset   |
| `ES_API_KEY`               | Elastic API key (real mode only)       | unset   |
| `GOOGLE_CLOUD_PROJECT`     | Vertex AI project (LLM path only)      | unset   |
| `GOOGLE_CLOUD_LOCATION`    | Vertex AI region                       | unset   |
| `GOOGLE_GENAI_USE_VERTEXAI`| `true` to use Vertex AI Gemini         | unset   |

## System prompt contract

Five sections, in order. Pulled from `src/gemini_elastic_agent/prompt.py`.

- **ANSWER**: 1-2 sentences, every command/number copied verbatim.
- **HITS**: bulleted list of consulted Elastic hits, one per line:
  `- index/doc-id - title - score`.
- **KEY QUOTES**: 2-4 byte-for-byte quotes tagged with `index/doc-id`.
- **CONFIDENCE**: `high` / `medium` / `low` with one-sentence reason
  tied to the top hit's score.
- **NEXT STEP**: one concrete follow-up query.

## Repo layout

```
src/gemini_elastic_agent/
  __init__.py
  agent.py     # build_agent() -> ADK LlmAgent with four tools
  prompt.py    # 5-section system prompt (ANSWER/HITS/KEY QUOTES/...)
  runner.py    # ask() with use_llm toggle for tests vs Vertex AI
  stubs.py     # hand-written fixtures shaped like elasticsearch client
  tools.py     # 4 FunctionTools: list_indices, hybrid_search, ...

tests/
  conftest.py
  test_tools.py
  test_agent.py

smoke.py        # end-to-end stub-mode smoke test
pyproject.toml
LICENSE         # MIT
```

## Cloud Run deploy (TODO, later stage)

The hackathon judging requires a public Cloud Run URL. That deploy step
is intentionally left for stage 2. Sketch:

```sh
# (later) build container and push
gcloud run deploy gemini-elastic-agent \
  --source . \
  --region us-central1 \
  --set-env-vars GEMINI_ELASTIC_STUB=0,ES_URL=...,GOOGLE_GENAI_USE_VERTEXAI=true \
  --set-secrets ES_API_KEY=es-api-key:latest
```

## License

MIT, see `LICENSE`.

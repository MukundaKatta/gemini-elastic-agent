"""FastAPI entry for Cloud Run.

Wraps ``gemini_elastic_agent.runner.ask`` behind an HTTP surface:

- ``POST /ask`` with ``{"question": "..."}`` -> ``{"answer": "..."}``
- ``GET  /healthz`` -> ``{"status": "ok"}``
- ``GET  /`` -> tiny HTML demo form that POSTs to /ask via fetch

Defaults to stub mode so the demo works without Elastic creds.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from gemini_elastic_agent.runner import ask

# Ensure stub mode by default so /ask works without Elastic creds.
os.environ.setdefault("GEMINI_ELASTIC_STUB", "1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

app = FastAPI(title="gemini-elastic-agent", version="0.1.0")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.get("/healthz")
@app.get("/health")
def healthz() -> dict[str, str]:
    # Cloud Run's frontend has been observed to intercept /healthz on some
    # routings, so /health is exposed as an alias that always reaches us.
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def post_ask(req: AskRequest) -> AskResponse:
    # Only attempt the live Vertex AI path if a project is wired up.
    use_llm = bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
    try:
        result = ask(req.question, use_llm=use_llm)
        text = result.final_text or ""
    except Exception:
        # Fall back to the deterministic local renderer if Vertex AI fails.
        text = ask(req.question, use_llm=False).final_text
    return AskResponse(answer=text)


_INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>gemini-elastic-agent</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:.2rem}
input,button{font-size:1rem;padding:.5rem .7rem}
input{width:70%}
pre{background:#f4f4f4;padding:1rem;white-space:pre-wrap;border-radius:6px}
.muted{color:#666;font-size:.9rem}
</style></head><body>
<h1>gemini-elastic-agent</h1>
<p class="muted">Gemini 2.5 Flash + Elastic hybrid search. Try the demo question below.</p>
<form id="f"><input id="q" value="how do I rotate the production database credentials" />
<button>Ask</button></form>
<pre id="out">(answer will appear here)</pre>
<script>
const f=document.getElementById('f'),q=document.getElementById('q'),o=document.getElementById('out');
f.addEventListener('submit',async e=>{e.preventDefault();o.textContent='thinking...';
  try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q.value})});const j=await r.json();o.textContent=j.answer||JSON.stringify(j);}
  catch(err){o.textContent='error: '+err;}});
</script>
</body></html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _INDEX_HTML

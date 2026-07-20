# AtlasAgent

AtlasAgent is an experimental internal knowledge assistant. This first prototype keeps ingestion,
search, chat, and audit behavior in one FastAPI module so the product workflow can be validated
before extracting production services.

## Prototype scope

- ingest plain-text and Markdown policy documents;
- split documents into overlapping chunks;
- search with deterministic token-overlap ranking;
- answer questions with visible source excerpts;
- inspect fictional customers and orders;
- record an in-memory audit trail.

## Run the prototype

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

API documentation is available at <http://localhost:8000/docs>.

## Direction

The current architecture keeps state in memory. Production requirements include persistent
storage, typed provider interfaces, approval-gated writes, an operator console, deterministic
evaluations, containers, and continuous integration.


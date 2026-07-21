# Two-minute demo script

## Setup

Run the API, dashboard, and `make seed`. Open <http://localhost:5173>.

## Walkthrough

1. Ask **“What is our enterprise refund policy?”** Show the grounded answer, ranked evidence,
   retrieval score, and latency in the inspector.
2. Ask **“Show me order ORD-2048.”** Point out that the read-only order tool executes immediately.
3. Ask **“Create a support draft for CUST-1001.”** The agent proposes the write but does not execute it.
4. Copy the action ID and run:

   ```bash
   .venv/bin/python scripts/approval_token.py ACTION_ID
   ```

5. Paste the token into the inspector and approve. The UI changes to completed only after the API
   verifies the token and records the execution.
6. Open <http://localhost:8000/docs> to show typed API contracts, then show the checked-in
   55-case evaluation result.

## Talking points

- Local mode is deterministic and requires no paid API; OpenAI mode uses the Responses and
  Embeddings APIs behind the same interfaces.
- Writes are proposed, approved, and executed as separate states.
- Benchmark results are measured artifacts, not aspirational resume claims.

## Refresh the repository screenshot

With the seeded API and dashboard running, execute `cd frontend && npm run screenshot`. The
Playwright script performs a real policy query and replaces `assets/screenshots/dashboard.png`.

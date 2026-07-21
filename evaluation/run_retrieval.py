"""Run deterministic retrieval benchmarks against a live AtlasAgent API."""

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def seed(client: httpx.Client) -> None:
    documents = json.loads((ROOT / "datasets/knowledge.json").read_text())
    for document in documents:
        response = client.post(
            "/api/documents/text",
            json={**document, "source_type": "markdown", "chunk_size": 500, "chunk_overlap": 75},
        )
        response.raise_for_status()


def run(base_url: str, method: str, top_k: int, should_seed: bool) -> dict:
    cases = load_jsonl(ROOT / "datasets/retrieval_cases.jsonl")
    hits = 0
    true_negatives = 0
    latencies: list[float] = []
    failures: list[dict] = []
    with httpx.Client(base_url=base_url, timeout=10) as client:
        if should_seed:
            seed(client)
        for case in cases:
            started = time.perf_counter()
            response = client.post(
                "/api/search", json={"query": case["query"], "method": method, "top_k": top_k}
            )
            response.raise_for_status()
            latencies.append((time.perf_counter() - started) * 1000)
            names = [result["document_name"] for result in response.json()]
            expected = case["expected_document"]
            if expected is None:
                true_negatives += int(not response.json() or response.json()[0]["score"] < 0.15)
            elif expected in names:
                hits += 1
            else:
                failures.append({"id": case["id"], "expected": expected, "received": names})
    positive_count = sum(case["expected_document"] is not None for case in cases)
    return {
        "configuration": {"method": method, "top_k": top_k},
        "cases": len(cases),
        "recall_at_k": round(hits / positive_count, 4),
        "irrelevant_rejection_rate": round(true_negatives / (len(cases) - positive_count), 4),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 2),
        },
        "failures": failures,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--method", choices=["semantic", "lexical", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.base_url, arguments.method, arguments.top_k, arguments.seed), indent=2))

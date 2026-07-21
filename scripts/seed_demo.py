"""Seed the running API with the deterministic portfolio demo corpus."""

import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def seed(base_url: str) -> None:
    documents = json.loads((ROOT / "evaluation/datasets/knowledge.json").read_text())
    with httpx.Client(base_url=base_url, timeout=15) as client:
        stats = client.get("/api/stats")
        stats.raise_for_status()
        if stats.json()["documents"]:
            print("Knowledge base already contains documents; no duplicates were added.")
            return
        for document in documents:
            response = client.post(
                "/api/documents/text",
                json={**document, "source_type": "markdown"},
            )
            response.raise_for_status()
            print(f"Indexed {document['name']}")
    print(f"Demo ready at {base_url}: {len(documents)} documents indexed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    arguments = parser.parse_args()
    seed(arguments.base_url)

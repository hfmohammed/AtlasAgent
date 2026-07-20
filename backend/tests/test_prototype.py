from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def setup_function():
    client.delete("/api/prototype/reset")


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_and_search_policy():
    ingest = client.post(
        "/api/documents",
        json={
            "name": "refunds.md",
            "content": "Enterprise customers have a 45-day refund window.",
            "source_type": "markdown",
            "metadata": {"department": "support"},
        },
    )

    assert ingest.status_code == 201
    assert ingest.json()["chunks_created"] == 1

    search = client.post(
        "/api/search",
        json={
            "query": "enterprise refund",
            "metadata_filter": {"department": "support"},
        },
    )

    assert search.status_code == 200
    assert search.json()[0]["document_name"] == "refunds.md"
    assert "45-day" in search.json()[0]["excerpt"]


def test_chat_uses_read_only_order_tool():
    response = client.post("/api/chat", json={"query": "Show order ORD-2048"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["tool_calls"][0]["name"] == "get_order"
    assert payload["tool_calls"][0]["result"]["status"] == "shipped"


def test_search_respects_metadata_filter():
    client.post(
        "/api/documents",
        json={
            "name": "leave.md",
            "content": "Employees receive twenty days of annual leave.",
            "metadata": {"department": "people"},
        },
    )

    response = client.post(
        "/api/search",
        json={
            "query": "annual leave",
            "metadata_filter": {"department": "finance"},
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_audit_log_records_agent_response():
    client.post("/api/chat", json={"query": "unknown question"})

    response = client.get("/api/audit")

    assert response.status_code == 200
    assert response.json()[-1]["event_type"] == "agent_response"

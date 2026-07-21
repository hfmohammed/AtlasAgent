from app.services.tools import approval_token

POLICY = """# Refund policy

Enterprise customers may request a refund within 45 days of the invoice date.
Standard customers may request a refund within 14 days.
"""


def test_ingest_then_chat_returns_grounded_citation(client):
    ingest = client.post(
        "/api/documents/text",
        json={
            "name": "refunds.md",
            "content": POLICY,
            "source_type": "markdown",
            "metadata": {"department": "support"},
        },
    )
    assert ingest.status_code == 201

    response = client.post(
        "/api/chat",
        json={"query": "How long is the enterprise refund window?", "top_k": 5},
    )
    payload = response.json()

    assert response.status_code == 200
    assert "45 days" in payload["answer"]
    assert payload["citations"][0]["document_name"] == "refunds.md"
    assert payload["latency_ms"] >= 0


def test_metadata_filter_excludes_other_departments(client):
    client.post(
        "/api/documents/text",
        json={
            "name": "policy.txt",
            "content": "Annual leave allowance is twenty days.",
            "metadata": {"department": "hr"},
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


def test_system_stats_reflect_index_and_pending_actions(client):
    client.post(
        "/api/documents/text",
        json={"name": "policy.txt", "content": "A searchable policy document."},
    )
    client.post("/api/chat", json={"query": "Create a support draft for CUST-1001"})

    stats = client.get("/api/stats")

    assert stats.status_code == 200
    assert stats.json() == {
        "documents": 1,
        "chunks": 1,
        "conversations": 1,
        "pending_approvals": 1,
    }


def test_read_only_tool_executes_without_approval(client):
    response = client.post("/api/chat", json={"query": "Show order ORD-2048"})
    call = response.json()["tool_calls"][0]

    assert call["name"] == "get_order"
    assert call["status"] == "completed"
    assert call["result"]["status"] == "shipped"


def test_mutating_tool_rejects_missing_approval(client):
    response = client.post(
        "/api/chat", json={"query": "Create a support draft for CUST-1001"}
    )
    call = response.json()["tool_calls"][0]

    assert call["status"] == "approval_required"
    denied = client.post(
        f"/api/actions/{call['action_id']}/approve", json={"approval_token": "wrong"}
    )
    assert denied.status_code == 403


def test_mutating_tool_executes_once_with_valid_approval(client):
    response = client.post(
        "/api/chat", json={"query": "Create a support draft for order ORD-2048"}
    )
    action_id = response.json()["tool_calls"][0]["action_id"]
    token = approval_token(action_id, "test-secret")

    approved = client.post(
        f"/api/actions/{action_id}/approve", json={"approval_token": token}
    )
    duplicate = client.post(
        f"/api/actions/{action_id}/approve", json={"approval_token": token}
    )

    assert approved.status_code == 200
    assert approved.json()["result"]["status"] == "created"
    assert duplicate.status_code == 409


def test_audit_log_records_agent_and_tool_events(client):
    response = client.post("/api/chat", json={"query": "Show customer CUST-1001"})
    conversation_id = response.json()["conversation_id"]

    audit = client.get(f"/api/conversations/{conversation_id}/audit")

    assert audit.status_code == 200
    assert [event["event_type"] for event in audit.json()] == ["agent_response"]


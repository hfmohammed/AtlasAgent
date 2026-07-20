"""Single-module AtlasAgent API prototype."""

import math
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="AtlasAgent Prototype", version="0.0.1")


def identifier() -> str:
    return str(uuid4())


@dataclass
class Chunk:
    id: str
    document_id: str
    position: int
    content: str
    tokens: set[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    id: str
    name: str
    source_type: str
    metadata: dict[str, Any]
    created_at: str


@dataclass
class AuditRecord:
    id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str
    latency_ms: float | None = None


class IngestRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_type: Literal["text", "markdown"] = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=75, ge=0, le=500)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(SearchRequest):
    conversation_id: str | None = None


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    excerpt: str
    score: float


DOCUMENTS: dict[str, Document] = {}
CHUNKS: dict[str, Chunk] = {}
AUDIT_LOG: list[AuditRecord] = []

CUSTOMERS = {
    "CUST-1001": {
        "id": "CUST-1001",
        "name": "Northwind Health",
        "tier": "enterprise",
        "region": "north-america",
    },
    "CUST-1002": {
        "id": "CUST-1002",
        "name": "Acme Retail",
        "tier": "standard",
        "region": "north-america",
    },
}

ORDERS = {
    "ORD-2048": {
        "id": "ORD-2048",
        "customer_id": "CUST-1001",
        "status": "shipped",
        "total": 1200.0,
    },
    "ORD-4096": {
        "id": "ORD-4096",
        "customer_id": "CUST-1002",
        "status": "processing",
        "total": 89.0,
    },
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def normalize(value: str) -> str:
    value = value.replace("\r\n", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def split_text(value: str, size: int, overlap: int) -> list[str]:
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
    paragraphs = [paragraph.strip() for paragraph in value.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if len(candidate) <= size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        while len(paragraph) > size:
            chunks.append(paragraph[:size])
            paragraph = paragraph[size - overlap :]
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def lexical_score(query: str, content: str) -> float:
    query_tokens = tokenize(query)
    content_tokens = tokenize(content)
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(content_tokens))
    return overlap / math.sqrt(len(query_tokens) * len(content_tokens))


def metadata_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def excerpt(value: str, limit: int = 260) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}…"


def record_event(
    event_type: str,
    payload: dict[str, Any],
    latency_ms: float | None = None,
) -> AuditRecord:
    event = AuditRecord(
        id=identifier(),
        event_type=event_type,
        payload=payload,
        latency_ms=latency_ms,
        created_at=now(),
    )
    AUDIT_LOG.append(event)
    return event


def search_chunks(request: SearchRequest) -> list[Citation]:
    ranked: list[tuple[float, Chunk]] = []
    for chunk in CHUNKS.values():
        if not metadata_matches(chunk.metadata, request.metadata_filter):
            continue
        score = lexical_score(request.query, chunk.content)
        if score > 0:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    citations: list[Citation] = []
    for score, chunk in ranked[: request.top_k]:
        document = DOCUMENTS[chunk.document_id]
        citations.append(
            Citation(
                chunk_id=chunk.id,
                document_id=document.id,
                document_name=document.name,
                excerpt=excerpt(chunk.content),
                score=round(score, 4),
            )
        )
    return citations


def find_identifier(pattern: str, query: str) -> str | None:
    match = re.search(pattern, query, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def select_tool(query: str) -> dict[str, Any] | None:
    customer_id = find_identifier(r"CUST-\d+", query)
    order_id = find_identifier(r"ORD-\d+", query)
    if customer_id:
        return {
            "name": "get_customer",
            "arguments": {"customer_id": customer_id},
            "result": CUSTOMERS.get(customer_id, {"error": "customer not found"}),
        }
    if order_id:
        return {
            "name": "get_order",
            "arguments": {"order_id": order_id},
            "result": ORDERS.get(order_id, {"error": "order not found"}),
        }
    return None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.post("/api/documents", status_code=201)
def ingest(request: IngestRequest) -> dict[str, Any]:
    content = normalize(request.content)
    if not content:
        raise HTTPException(status_code=422, detail="document has no content")
    try:
        pieces = split_text(content, request.chunk_size, request.chunk_overlap)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    document = Document(
        id=identifier(),
        name=request.name,
        source_type=request.source_type,
        metadata=request.metadata,
        created_at=now(),
    )
    DOCUMENTS[document.id] = document
    for position, piece in enumerate(pieces):
        chunk = Chunk(
            id=identifier(),
            document_id=document.id,
            position=position,
            content=piece,
            tokens=tokenize(piece),
            metadata=request.metadata,
        )
        CHUNKS[chunk.id] = chunk
    record_event(
        "document_ingested",
        {"document_id": document.id, "name": document.name, "chunks": len(pieces)},
    )
    return {"document_id": document.id, "chunks_created": len(pieces)}


@app.post("/api/search", response_model=list[Citation])
def search(request: SearchRequest) -> list[Citation]:
    started = time.perf_counter()
    citations = search_chunks(request)
    record_event(
        "knowledge_searched",
        {"query": request.query, "results": len(citations)},
        (time.perf_counter() - started) * 1000,
    )
    return citations


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    started = time.perf_counter()
    citations = search_chunks(request)
    tool_call = select_tool(request.query)
    if citations:
        context = " ".join(item.excerpt for item in citations[:3])
        answer = f"Based on indexed knowledge: {context}"
    elif tool_call:
        answer = "I retrieved the requested business record."
    else:
        answer = "I could not find relevant indexed knowledge."
    conversation_id = request.conversation_id or identifier()
    latency_ms = (time.perf_counter() - started) * 1000
    record_event(
        "agent_response",
        {
            "conversation_id": conversation_id,
            "query": request.query,
            "citation_ids": [item.chunk_id for item in citations],
            "tool": tool_call,
        },
        latency_ms,
    )
    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "citations": citations,
        "tool_calls": [tool_call] if tool_call else [],
        "latency_ms": round(latency_ms, 2),
    }


@app.get("/api/audit")
def audit() -> list[dict[str, Any]]:
    return [asdict(event) for event in AUDIT_LOG]


@app.delete("/api/prototype/reset", status_code=204)
def reset() -> None:
    DOCUMENTS.clear()
    CHUNKS.clear()
    AUDIT_LOG.clear()


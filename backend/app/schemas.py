from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IngestTextRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_type: Literal["text", "markdown", "json", "csv"] = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=75, ge=0, le=500)


class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    excerpt: str
    score: float


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    method: Literal["semantic", "lexical", "hybrid"] = "hybrid"
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(SearchRequest):
    conversation_id: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
    status: Literal["completed", "approval_required", "failed"]
    result: dict[str, Any] | None = None
    action_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[Citation]
    tool_calls: list[ToolCall] = Field(default_factory=list)
    latency_ms: float


class ApprovalRequest(BaseModel):
    approval_token: str = Field(min_length=1)


class AuditEventResponse(BaseModel):
    id: str
    event_type: str
    payload: dict[str, Any]
    latency_ms: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    documents: int
    chunks: int
    conversations: int
    pending_approvals: int

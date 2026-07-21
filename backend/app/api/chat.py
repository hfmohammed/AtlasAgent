import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main_dependencies import get_answer_provider, get_embeddings
from app.models import AuditEvent, Chunk, Conversation, Document, PendingAction
from app.schemas import (
    ApprovalRequest,
    AuditEventResponse,
    ChatRequest,
    ChatResponse,
    Citation,
    SearchRequest,
    SystemStats,
)
from app.services.agent import decide
from app.services.answers import AnswerProvider
from app.services.embeddings import EmbeddingProvider
from app.services.retrieval import relevant_results, search, to_citation
from app.services.tools import execute_approved, verify_approval

router = APIRouter(tags=["agent"])


@router.get("/stats", response_model=SystemStats)
def system_stats(db: Annotated[Session, Depends(get_db)]) -> SystemStats:
    def count(model: type, *filters: object) -> int:
        statement = select(func.count()).select_from(model)
        if filters:
            statement = statement.where(*filters)
        return db.scalar(statement) or 0

    return SystemStats(
        documents=count(Document),
        chunks=count(Chunk),
        conversations=count(Conversation),
        pending_approvals=count(PendingAction, PendingAction.executed.is_(False)),
    )


@router.post("/search", response_model=list[Citation])
def search_knowledge(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    embeddings: Annotated[EmbeddingProvider, Depends(get_embeddings)],
) -> list[Citation]:
    results = search(db, embeddings, **request.model_dump())
    return [to_citation(result) for result in results]


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    embeddings: Annotated[EmbeddingProvider, Depends(get_embeddings)],
    answers: Annotated[AnswerProvider, Depends(get_answer_provider)],
) -> ChatResponse:
    started = time.perf_counter()
    conversation = (
        db.get(Conversation, request.conversation_id) if request.conversation_id else None
    )
    if not conversation:
        conversation = Conversation(title=request.query[:80])
        db.add(conversation)
        db.flush()

    ranked = search(
        db,
        embeddings,
        query=request.query,
        top_k=request.top_k,
        method=request.method,
        metadata_filter=request.metadata_filter,
    )
    citations = [to_citation(result) for result in relevant_results(ranked)]
    decision = decide(db, conversation, request.query)
    answer = answers.generate(
        request.query,
        citations,
        decision.tool_calls,
        decision.answer_prefix,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    db.add(
        AuditEvent(
            conversation_id=conversation.id,
            event_type="agent_response",
            latency_ms=latency_ms,
            payload={
                "query": request.query,
                "citation_ids": [item.chunk_id for item in citations],
                "tools": [call.model_dump(mode="json") for call in decision.tool_calls],
            },
        )
    )
    db.commit()
    return ChatResponse(
        conversation_id=conversation.id,
        answer=answer,
        citations=citations,
        tool_calls=decision.tool_calls,
        latency_ms=round(latency_ms, 2),
    )


@router.post("/actions/{action_id}/approve")
def approve_action(
    action_id: str,
    request: ApprovalRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    action = db.get(PendingAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    if not verify_approval(action.id, request.approval_token, settings.approval_secret):
        raise HTTPException(status_code=403, detail="invalid approval token")
    action.approved = True
    db.flush()
    try:
        result = execute_approved(db, action)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"action_id": action.id, "status": "executed", "result": result}


@router.get("/conversations/{conversation_id}/audit", response_model=list[AuditEventResponse])
def get_audit_log(
    conversation_id: str, db: Annotated[Session, Depends(get_db)]
) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.conversation_id == conversation_id)
            .order_by(AuditEvent.created_at)
        )
    )


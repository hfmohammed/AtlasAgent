import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main_dependencies import get_embeddings
from app.schemas import IngestResponse, IngestTextRequest
from app.services.embeddings import EmbeddingProvider
from app.services.ingestion import extract_pdf, ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/text", response_model=IngestResponse, status_code=201)
def ingest_text(
    request: IngestTextRequest,
    db: Annotated[Session, Depends(get_db)],
    embeddings: Annotated[EmbeddingProvider, Depends(get_embeddings)],
) -> IngestResponse:
    try:
        document = ingest_document(
            db,
            embeddings,
            name=request.name,
            content=request.content,
            source_type=request.source_type,
            metadata=request.metadata,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestResponse(document_id=document.id, chunks_created=len(document.chunks))


@router.post("/upload", response_model=IngestResponse, status_code=201)
def upload_document(
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    embeddings: Annotated[EmbeddingProvider, Depends(get_embeddings)],
    metadata: Annotated[str, Form()] = "{}",
) -> IngestResponse:
    suffix = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "text"
    source_type = {"md": "markdown", "txt": "text"}.get(suffix, suffix)
    if source_type not in {"pdf", "markdown", "text", "json", "csv"}:
        raise HTTPException(status_code=415, detail="unsupported document type")
    raw = file.file.read()
    try:
        content = extract_pdf(raw) if source_type == "pdf" else raw.decode("utf-8")
        document = ingest_document(
            db,
            embeddings,
            name=file.filename or "upload",
            content=content,
            source_type="text" if source_type == "pdf" else source_type,
            metadata=json.loads(metadata),
            chunk_size=500,
            chunk_overlap=75,
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestResponse(document_id=document.id, chunks_created=len(document.chunks))


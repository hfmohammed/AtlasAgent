import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.services.embeddings import EmbeddingProvider


@dataclass(frozen=True)
class ChunkDraft:
    position: int
    content: str


def normalize_content(content: str, source_type: str) -> str:
    if source_type == "json":
        parsed = json.loads(content)
        return json.dumps(parsed, indent=2, sort_keys=True)
    if source_type == "csv":
        rows = csv.DictReader(io.StringIO(content))
        return "\n".join(
            "; ".join(f"{key}: {value}" for key, value in row.items()) for row in rows
        )
    return re.sub(r"[ \t]+", " ", content).strip()


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def chunk_text(text: str, size: int = 500, overlap: int = 75) -> list[ChunkDraft]:
    if overlap >= size:
        raise ValueError("chunk overlap must be smaller than chunk size")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= size:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        while len(paragraph) > size:
            chunks.append(paragraph[:size])
            paragraph = paragraph[size - overlap :]
        current = paragraph
    if current:
        chunks.append(current)
    return [ChunkDraft(position=index, content=value) for index, value in enumerate(chunks)]


def ingest_document(
    db: Session,
    embeddings: EmbeddingProvider,
    *,
    name: str,
    content: str,
    source_type: str,
    metadata: dict,
    chunk_size: int,
    chunk_overlap: int,
) -> Document:
    normalized = normalize_content(content, source_type)
    if not normalized:
        raise ValueError("document has no extractable content")
    document = Document(name=Path(name).name, source_type=source_type, metadata_json=metadata)
    for draft in chunk_text(normalized, chunk_size, chunk_overlap):
        document.chunks.append(
            Chunk(
                position=draft.position,
                content=draft.content,
                embedding=embeddings.embed(draft.content),
                metadata_json=metadata,
            )
        )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.schemas import Citation
from app.services.embeddings import EmbeddingProvider, cosine_similarity


@dataclass(frozen=True)
class RankedChunk:
    chunk: Chunk
    document: Document
    score: float


def _lexical_score(query: str, content: str) -> float:
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    content_terms = re.findall(r"[a-z0-9]+", content.lower())
    if not query_terms or not content_terms:
        return 0.0
    matches = sum(1 for term in content_terms if term in query_terms)
    return matches / math.sqrt(len(content_terms) * len(query_terms))


def _matches(metadata: dict, expected: dict) -> bool:
    return all(metadata.get(key) == value for key, value in expected.items())


def search(
    db: Session,
    embeddings: EmbeddingProvider,
    *,
    query: str,
    top_k: int,
    method: str,
    metadata_filter: dict,
) -> list[RankedChunk]:
    rows = db.execute(select(Chunk, Document).join(Document)).all()
    query_vector = embeddings.embed(query)
    ranked: list[RankedChunk] = []
    for chunk, document in rows:
        if not _matches(chunk.metadata_json, metadata_filter):
            continue
        semantic = max(0.0, cosine_similarity(query_vector, chunk.embedding))
        lexical = _lexical_score(query, chunk.content)
        if method == "semantic":
            score = semantic
        elif method == "lexical":
            score = lexical
        else:
            score = semantic * 0.65 + lexical * 0.35
        ranked.append(RankedChunk(chunk=chunk, document=document, score=score))
    return sorted(ranked, key=lambda result: result.score, reverse=True)[:top_k]


def relevant_results(
    results: list[RankedChunk], *, absolute_floor: float = 0.05, relative_floor: float = 0.5
) -> list[RankedChunk]:
    if not results:
        return []
    threshold = max(absolute_floor, results[0].score * relative_floor)
    return [result for result in results if result.score >= threshold]


def to_citation(result: RankedChunk) -> Citation:
    excerpt = result.chunk.content[:280]
    if len(result.chunk.content) > 280:
        excerpt += "…"
    return Citation(
        chunk_id=result.chunk.id,
        document_id=result.document.id,
        document_name=result.document.name,
        excerpt=excerpt,
        score=round(result.score, 4),
    )

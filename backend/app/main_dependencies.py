from functools import lru_cache

from app.core.config import get_settings
from app.services.answers import AnswerProvider, DeterministicAnswerProvider, OpenAIAnswerProvider
from app.services.embeddings import (
    EmbeddingProvider,
    HashEmbeddingProvider,
    OpenAIEmbeddingProvider,
)


@lru_cache
def get_embeddings() -> EmbeddingProvider:
    settings = get_settings()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when ATLAS_LLM_PROVIDER=openai")
        return OpenAIEmbeddingProvider(settings.openai_api_key, settings.embedding_model)
    return HashEmbeddingProvider()


@lru_cache
def get_answer_provider() -> AnswerProvider:
    settings = get_settings()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when ATLAS_LLM_PROVIDER=openai")
        return OpenAIAnswerProvider(settings.openai_api_key, settings.chat_model)
    return DeterministicAnswerProvider()


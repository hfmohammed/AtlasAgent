from types import SimpleNamespace

import pytest

from app.services.embeddings import (
    HashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    cosine_similarity,
)


def test_embeddings_are_deterministic_and_normalized():
    provider = HashEmbeddingProvider()
    first = provider.embed("enterprise refund policy")
    second = provider.embed("enterprise refund policy")

    assert first == second
    assert cosine_similarity(first, first) == pytest.approx(1.0)


def test_related_text_scores_higher_than_unrelated_text():
    provider = HashEmbeddingProvider()
    query = provider.embed("refund policy enterprise")

    related = cosine_similarity(query, provider.embed("enterprise refund rules"))
    unrelated = cosine_similarity(query, provider.embed("office parking map"))

    assert related > unrelated


def test_openai_provider_requests_fixed_dimensions():
    class FakeEmbeddings:
        def create(self, **kwargs):
            assert kwargs == {
                "model": "text-embedding-3-small",
                "input": "policy",
                "encoding_format": "float",
                "dimensions": 128,
            }
            return SimpleNamespace(data=[SimpleNamespace(embedding=[0.5, 0.5])])

    client = SimpleNamespace(embeddings=FakeEmbeddings())
    provider = OpenAIEmbeddingProvider("unused", "text-embedding-3-small", client=client)

    assert provider.embed("policy") == [0.5, 0.5]

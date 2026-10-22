from types import SimpleNamespace

from app.schemas import Citation
from app.services.answers import DeterministicAnswerProvider, OpenAIAnswerProvider


def citation() -> Citation:
    return Citation(
        chunk_id="chunk-1",
        document_id="document-1",
        document_name="policy.md",
        excerpt="Enterprise refunds are available for 45 days.",
        score=0.9,
    )


def test_deterministic_answers_include_retrieved_evidence():
    answer = DeterministicAnswerProvider().generate("refund period", [citation()], [], "")

    assert "45 days" in answer


def test_openai_answers_use_responses_api_and_grounding_instructions():
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="The period is 45 days [1].")

    client = SimpleNamespace(responses=FakeResponses())
    provider = OpenAIAnswerProvider("unused", "test-model", client=client)

    answer = provider.generate("What is the refund period?", [citation()], [], "")

    assert answer == "The period is 45 days [1]."
    assert captured["model"] == "test-model"
    assert "Answer only from" in captured["instructions"]
    assert "policy.md" in captured["input"]

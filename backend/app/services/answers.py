from typing import Any, Protocol

from app.schemas import Citation, ToolCall


class AnswerProvider(Protocol):
    def generate(
        self,
        query: str,
        citations: list[Citation],
        tool_calls: list[ToolCall],
        answer_prefix: str,
    ) -> str: ...


class DeterministicAnswerProvider:
    def generate(
        self,
        query: str,
        citations: list[Citation],
        tool_calls: list[ToolCall],
        answer_prefix: str,
    ) -> str:
        del query
        context = " ".join(citation.excerpt for citation in citations[:3])
        if context:
            return f"{answer_prefix}Based on the indexed knowledge: {context}"
        if tool_calls:
            return f"{answer_prefix}No relevant knowledge-base passage was found."
        return "I could not find relevant indexed knowledge. Try adding a document first."


class OpenAIAnswerProvider:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
        self.client = client
        self.model = model

    def generate(
        self,
        query: str,
        citations: list[Citation],
        tool_calls: list[ToolCall],
        answer_prefix: str,
    ) -> str:
        evidence = "\n\n".join(
            f"[{index}] {citation.document_name}: {citation.excerpt}"
            for index, citation in enumerate(citations, start=1)
        )
        tool_results = "\n".join(
            f"- {call.name}: {call.result or call.status}" for call in tool_calls
        )
        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "You are an enterprise knowledge assistant. Answer only from the supplied "
                "evidence and tool results. Cite evidence using [1], [2], and so on. If the "
                "evidence is insufficient, say so. Never claim a pending action was executed."
            ),
            input=(
                f"Question: {query}\n\nEvidence:\n{evidence or 'None'}\n\n"
                f"Tool results:\n{tool_results or 'None'}"
            ),
        )
        return f"{answer_prefix}{response.output_text}".strip()

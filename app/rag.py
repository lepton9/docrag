from __future__ import annotations

from dataclasses import dataclass

from index_store import ChunkDoc
from model import Model, default_model


_SYSTEM = (
    "You are a RAG assistant. You MUST answer using ONLY the provided context extracted "
    "from the user-supplied websites. Do not use outside knowledge. If the context does "
    "not contain the answer, say you don't know based on the provided sites. "
    "When you make a factual claim, cite the supporting source."
)


@dataclass
class RagAnswer:
    answer: str
    sources: list[str]


ChatMessage = dict[str, str]


def _trim_history(history: list[ChatMessage], *, max_messages: int) -> list[ChatMessage]:
    if max_messages <= 0:
        return []
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def _history_user_questions(history: list[ChatMessage], max_items: int = 6) -> list[str]:
    qs: list[str] = []
    for m in reversed(history):
        if m.get("role") == "user":
            c = (m.get("content") or "").strip()
            if c:
                qs.append(c)
                if len(qs) >= max_items:
                    break
    qs.reverse()
    return qs


@dataclass
class RagService:
    model: Model | None
    system_prompt: str = ""
    max_history_messages: int = 20

    def __init__(self, model: Model | None = None, system_prompt: str | None = None) -> None:
        self.model = model
        self.system_prompt = system_prompt or _SYSTEM

    def _get_model(self) -> Model:
        return self.model or default_model()

    def answer(
        self,
        index_store,
        prompt: str,
        top_k: int,
        history: list[ChatMessage] | None = None,
    ) -> RagAnswer:
        """Generate an answer from user prompt"""

        # Add chat history to the prompt
        retrieval_text = prompt
        if history:
            qs = _history_user_questions(history)
            if qs:
                retrieval_text = prompt + "\n\nPrevious questions:\n" + \
                    "\n".join(f"- {q}" for q in qs)

        # Search for relevant info using the embeddings
        hits = index_store.search(top_k, retrieval_text)
        context, urls = _format_context(hits)

        # Create prompt
        messages: list[ChatMessage] = [
            {"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(_trim_history(
                history, max_messages=self.max_history_messages))

        user_text = ("CONTEXT\n" + context + "\n\n" + "QUESTION\n" + prompt)
        messages.append({"role": "user", "content": user_text})

        text = self._get_model().generate_response(messages, temperature=0.2)

        # Filter duplicate urls out
        seen: set[str] = set()
        unique: list[str] = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique.append(url)

        return RagAnswer(answer=text, sources=unique)


    def get_all_models(self):
        """Get all the models."""
        model = self._get_model()
        return model.get_models()


def _format_context(hits: list[tuple[float, ChunkDoc]]) -> tuple[str, list[str]]:
    """Make a formatted user prompt from the list of relevant info"""
    urls: list[str] = []
    blocks: list[str] = []
    for i, (_score, doc) in enumerate(hits, start=1):
        urls.append(doc.url)
        title = doc.title.strip() or doc.url
        blocks.append(f"[{i}] {title}\nURL: {doc.url}\nCONTENT: {doc.chunk}")
    return "\n\n".join(blocks), urls


rag_service = RagService()

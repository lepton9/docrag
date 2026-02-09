from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_CHAT_MODEL, OPENAI_EMBED_MODEL


@dataclass(frozen=True)
class ModelConfig:
    api_key: str
    base_url: str | None
    chat_model: str
    embed_model: str


class Model:
    def __init__(self, cfg: ModelConfig) -> None:
        if not cfg.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._cfg = cfg
        self._client: OpenAI | None = None

    @property
    def cfg(self) -> ModelConfig:
        return self._cfg

    def _get_client(self) -> OpenAI:
        if self._client is None:
            kwargs = {"api_key": self._cfg.api_key}
            if self._cfg.base_url:
                kwargs["base_url"] = self._cfg.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def chat(self, *, sys_prompt: str, user_text: str, temp: float = 0.2) -> str:
        """Get completion from the LLM"""
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self._cfg.chat_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=temp,
        )
        return (resp.choices[0].message.content or "").strip()

    def embed_texts(self, texts: list[str], *, batch_size: int = 128) -> list[list[float]]:
        """Create embeddings"""
        client = self._get_client()
        vecs: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = client.embeddings.create(model=self._cfg.embed_model, input=batch)
            vecs.extend([d.embedding for d in resp.data])
        return vecs

    @staticmethod
    def from_env() -> Model:
        """Create Model from env variables"""
        base_url = (OPENAI_BASE_URL or "").strip() or None
        cfg = ModelConfig(
            api_key=OPENAI_API_KEY,
            base_url=base_url,
            chat_model=OPENAI_CHAT_MODEL,
            embed_model=OPENAI_EMBED_MODEL,
        )
        return Model(cfg)

default_model = Model.from_env()

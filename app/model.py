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

    def generate_response(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        """Generate response from a list of messages"""
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self._cfg.chat_model,
            messages=messages,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()


    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings"""
        client = self._get_client()
        resp = client.embeddings.create(model=self._cfg.embed_model, input=texts)
        return [r.embedding for r in resp.data]

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

@lru_cache(maxsize=1)
def default_model() -> Model:
    return Model.from_env()

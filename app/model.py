from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from openai import NotFoundError, OpenAI, types

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_CHAT_MODEL, OPENAI_EMBED_MODEL

MAX_TOKENS_EMBED = 300_000


class ModelType(Enum):  # TODO: use the type
    OpenAI = 1


class ModelError(Enum):
    InvalidModel = 1


@dataclass
class ModelResponse:
    text: str
    tokens_used: int = 0


@dataclass(frozen=True)
class ModelConfig:
    model_type: ModelType
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
            api_key = self._cfg.api_key
            base_url = self._cfg.base_url
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def generate_response(
        self,
        messages: list[dict[str, str]],
    ) -> ModelResponse | ModelError:
        """Generate response from a list of messages"""
        client = self._get_client()
        try:
            resp = client.chat.completions.create(
                model=self._cfg.chat_model,
                messages=messages,
            )
        except NotFoundError:
            return ModelError.InvalidModel

        tokens_used = 0
        if (resp.usage):
            tokens_used = resp.usage.total_tokens
        return ModelResponse(
            (resp.choices[0].message.content or "").strip(),
            tokens_used
        )

    def get_embeddings(self, text_chunks: list[str]) -> list[list[float]]:
        """Generate embeddings"""
        client = self._get_client()

        if (text_chunks == []):
            return []

        # Calculate the amount of chunks to process in one request
        total_chunks = len(text_chunks)
        reference_chunk = text_chunks[0]
        tokens_per_chunk = calc_tokens_approx(reference_chunk)
        total_chunk_tokens = tokens_per_chunk * total_chunks
        batches: int = max(1, -(-total_chunk_tokens // MAX_TOKENS_EMBED))
        batch_len = total_chunks // batches

        # Get embeddings for the batches
        datas: list[types.Embedding] = []
        tokens_used = 0
        i = 0
        while (i < total_chunks):
            end = min(total_chunks, i + batch_len)
            batch: list[str] = text_chunks[i:end]
            resp = client.embeddings.create(
                model=self._cfg.embed_model,
                input=batch,
            )
            datas.extend(resp.data)
            if resp.usage:
                tokens_used += resp.usage.total_tokens
            i = end

        return [r.embedding for r in datas]

    def get_models(self):
        """Get all the models."""
        client = self._get_client()
        return client.models.list()

    @staticmethod
    def get_model(model_name: str) -> Model:
        """Create OpenAI Model from model name."""
        base_url = (OPENAI_BASE_URL or "").strip() or None
        cfg = ModelConfig(
            model_type=ModelType.OpenAI,
            api_key=OPENAI_API_KEY,
            base_url=base_url,
            chat_model=model_name,
            embed_model=OPENAI_EMBED_MODEL,
        )
        return Model(cfg)

    @staticmethod
    def from_env() -> Model:
        """Create Model from env variables."""
        return Model.get_model(OPENAI_CHAT_MODEL)


@lru_cache(maxsize=1)
def default_model() -> Model:
    return Model.from_env()


def calc_tokens_approx(text: str) -> int:
    """Approximate the token count of the text."""
    char_to_token = 5
    return len(text) // char_to_token

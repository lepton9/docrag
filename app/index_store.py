from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import faiss
import numpy as np

from app.config import DATA_DIR
from app.model import default_model


@dataclass
class ChunkDoc:
    id: str
    url: str
    title: str
    chunk: str


def _paths(data_dir: str | None = None) -> tuple[Path, Path]:
    """Return the paths to the stored embeddings data."""
    d = Path(data_dir or DATA_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d / "index.faiss", d / "docs.jsonl"


def _embed_texts(texts: list[str]) -> np.ndarray:
    """Create embeddings for the input"""
    model = default_model()
    vecs = model.get_embeddings(texts)
    arr = np.array(vecs, dtype="float32")
    faiss.normalize_L2(arr)
    return arr


class IndexStore:
    def __init__(
        self,
        index: faiss.Index,
        docs: list[ChunkDoc],
        data_dir: str | None = None,
    ):
        self.index = index
        self.docs = docs
        self.data_dir = data_dir

    @property
    def idx_path(self) -> Path:
        return _paths(self.data_dir)[0]

    @property
    def docs_path(self) -> Path:
        return _paths(self.data_dir)[1]

    @classmethod
    def build(
        cls,
        chunks: list[ChunkDoc],
        data_dir: str | None = None,
    ) -> IndexStore:
        texts = [c.chunk for c in chunks]
        emb = _embed_texts(texts)
        dim = int(emb.shape[1])
        index = faiss.IndexFlatIP(dim)
        index.add(emb)
        return cls(index=index, docs=chunks, data_dir=data_dir)

    def save(self) -> dict:
        """Write the embeddings to disk."""
        idx_path, docs_path = _paths(self.data_dir)
        faiss.write_index(self.index, str(idx_path))
        with docs_path.open("w", encoding="utf-8") as f:
            for c in self.docs:
                f.write(json.dumps(asdict(c), ensure_ascii=True) + "\n")

        return {
            "chunks": len(self.docs),
            "index_path": str(idx_path),
            "docs_path": str(docs_path),
        }

    @classmethod
    def load(cls, data_dir: str | None = None) -> IndexStore:
        """Load the embeddings from disk."""
        idx_path, docs_path = _paths(data_dir)
        if not idx_path.exists() or not docs_path.exists():
            raise FileNotFoundError(
                f"Index not found. Run ingest first (missing {idx_path} or {docs_path})."
            )

        index = faiss.read_index(str(idx_path))
        docs: list[ChunkDoc] = []
        with docs_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                docs.append(ChunkDoc(**obj))

        return cls(index=index, docs=docs, data_dir=data_dir)

    def search(self, top_k: int, query: str) -> list[tuple[float, ChunkDoc]]:
        """Search for relevant content from the embeddings."""
        query_vec = _embed_texts([query])
        scores, ids = self.index.search(query_vec, top_k)
        hits: list[tuple[float, ChunkDoc]] = []
        for score, idx in zip(scores[0].tolist(), ids[0].tolist()):
            if idx < 0 or idx >= len(self.docs):
                continue
            hits.append((float(score), self.docs[idx]))
        return hits


def build_and_save(
    chunks: list[ChunkDoc],
    data_dir: str | None = None,
) -> dict:
    store = IndexStore.build(chunks, data_dir=data_dir)
    return store.save()

from __future__ import annotations

from rag import ChatMessage, rag_service
from index_store import build_and_save, IndexStore
from crawler import crawl_async
from config import CHUNK_OVERLAP, CHUNK_SIZE, MAX_DEPTH, MAX_PAGES, TOP_K
from chunker import chunk_pages

from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

import sys
from pathlib import Path
import threading
import uuid
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


PORT = "8000"
HOST = "127.0.0.1"

_SESSIONS_LOCK = threading.Lock()
_SESSIONS: dict[str, list[ChatMessage]] = {}
_MAX_SESSION_MESSAGES = 20


load_dotenv()

app = FastAPI(title="chat-rag")

_STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


class IngestReq(BaseModel):
    urls: list[str] = Field(..., min_length=1)
    max_pages: int | None = None
    max_depth: int | None = None


class ChatReq(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = None
    session_id: str | None = None


def _allowed_urls(urls: list[str]) -> set[str]:
    """Filter allowed urls."""
    out: set[str] = set()
    for u in urls:
        try:
            p = urlparse(u, "https")
            netloc = (p.hostname or "").lower()
            out.add(p.scheme + "://" + netloc + "/" + p.path)
        except Exception:
            continue
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ingest")
async def ingest(req: IngestReq):
    """Add a list of domains to the data store."""
    urls = _allowed_urls(req.urls)
    if not urls:
        raise HTTPException(status_code=400, detail="No valid domains in urls")

    # Crawl the pages for contents
    pages = await crawl_async(
        urls=urls,
        max_pages=req.max_pages or MAX_PAGES,
        max_depth=req.max_depth or MAX_DEPTH,
    )

    # Split the page contents to smaller chunks
    chunks = chunk_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP)

    if not chunks:
        raise HTTPException(
            status_code=400, detail="No text extracted from provided sites")

    meta = build_and_save(chunks)
    return {
        "pages": len(pages),
        "chunks": meta["chunks"],
        "allowed_domains": sorted(urls),
    }


@app.post("/answer")
def answer(req: ChatReq):
    """Answer to a user query."""
    try:
        index_store = IndexStore.load()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Retrieve history
    sid = (req.session_id or "").strip() or uuid.uuid4().hex
    with _SESSIONS_LOCK:
        history = list(_SESSIONS.get(sid, []))

    # Generate answer
    ans = rag_service.answer(
        index_store,
        req.question,
        top_k=req.top_k or TOP_K,
        history=history,
    )

    # Add to history
    history.append({"role": "user", "content": req.question})
    history.append({"role": "assistant", "content": ans.answer})
    if len(history) > _MAX_SESSION_MESSAGES:
        history = history[-_MAX_SESSION_MESSAGES:]
    with _SESSIONS_LOCK:
        _SESSIONS[sid] = history

    return {"answer": ans.answer, "sources": ans.sources, "session_id": sid}


@app.get("/")
def home():
    path = _STATIC_DIR / "index.html"
    return FileResponse(path)


def _main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run the chat-rag API server")
    parser.add_argument("--host", default=os.getenv("HOST", HOST))
    parser.add_argument("--port", type=int,
                        default=int(os.getenv("PORT", PORT)))
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "info"))
    parser.add_argument("--reload", action="store_true", default=False)
    args = parser.parse_args()

    try:
        import uvicorn
    except Exception as e:
        raise SystemExit("uvicorn is required to run the server.") from e

    uvicorn.run(
        "app.server:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )


if __name__ == "__main__":
    _main()

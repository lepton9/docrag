from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks."""
    text = (text or "").strip()
    if not text:
        return []
    if chunk_size <= 0:
        return [text]

    overlap = max(0, min(overlap, chunk_size - 1))

    chunks: list[str] = []
    i = 0
    text_len = len(text)

    while i < text_len:
        j = min(text_len, i + chunk_size)
        chunk = text[i:j].strip()
        if chunk:
            chunks.append(chunk)
        if j >= text_len:
            break
        i = j - overlap

    return chunks

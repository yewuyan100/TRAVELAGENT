from __future__ import annotations

import re

from app.rag.ingestion.cleaner import clean_text


def split_document(
    document: dict,
    chunk_size: int = 700,
    overlap: int = 100,
) -> list[dict]:
    content = clean_text(document.get("content", ""))
    if not content:
        return []

    pieces = _split_by_structure(content)
    bodies = _pack_pieces(pieces, chunk_size=chunk_size, overlap=overlap)
    chunks = []

    for index, body in enumerate(bodies, start=1):
        chunk_id = f"{document['doc_id']}_chunk_{index:04d}"
        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": document["doc_id"],
            "id": document["doc_id"],
            "title": document.get("title", ""),
            "content": _render_chunk_content(document, body),
            "city": document.get("city", ""),
            "province": document.get("province", ""),
            "country": document.get("country", ""),
            "category": document.get("category", ""),
            "tags": document.get("tags", []),
            "source": document.get("source", ""),
            "source_url": document.get("source", ""),
            "source_type": document.get("source_type", ""),
            "updated_at": document.get("updated_at", ""),
            "content_hash": document.get("content_hash", ""),
        })
    return chunks


def chunk_documents(documents: list[dict], chunk_size: int = 700, overlap: int = 100) -> list[dict]:
    chunks = []
    for document in documents:
        chunks.extend(split_document(document, chunk_size=chunk_size, overlap=overlap))
    return chunks


def _split_by_structure(content: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    if len(paragraphs) > 1:
        return paragraphs

    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if len(lines) > 1:
        return lines

    sentences = re.split(r"(?<=[。！？；;])", content)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _pack_pieces(pieces: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for piece in pieces:
        if len(piece) > chunk_size:
            if current:
                chunks.append("\n".join(current).strip())
                current = []
                current_length = 0
            chunks.extend(_hard_split(piece, chunk_size=chunk_size, overlap=overlap))
            continue

        projected = current_length + len(piece) + (1 if current else 0)
        if current and projected > chunk_size:
            chunks.append("\n".join(current).strip())
            overlap_text = _tail_overlap(chunks[-1], overlap)
            current = [overlap_text, piece] if overlap_text else [piece]
            current_length = sum(len(part) for part in current)
        else:
            current.append(piece)
            current_length = projected

    if current:
        chunks.append("\n".join(current).strip())

    return [chunk for chunk in chunks if chunk]


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(text):
        chunks.append(text[start : start + chunk_size].strip())
        start += step
    return [chunk for chunk in chunks if chunk]


def _tail_overlap(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    return text[-overlap:].strip()


def _render_chunk_content(document: dict, body: str) -> str:
    header = [
        f"标题：{document.get('title', '')}",
        f"城市：{document.get('city', '')}",
        f"分类：{document.get('category', '')}",
    ]
    return "\n".join(header) + "\n\n" + body

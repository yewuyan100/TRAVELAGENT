from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.config import settings
from app.rag.embeddings import create_embedding_provider, embeddings_to_numpy
from app.rag.ingestion.chunker import chunk_documents
from app.rag.ingestion.loaders import load_raw_documents, read_jsonl, write_jsonl
from app.rag.ingestion.manifest import diff_documents, load_manifest, save_manifest, update_manifest
from app.rag.loader import VectorStore


VALID_MODES = {"full", "incremental"}


def run_ingestion_pipeline(mode: str = "incremental") -> dict:
    if mode not in VALID_MODES:
        raise ValueError(f"mode 只能是：{', '.join(sorted(VALID_MODES))}")

    documents = load_raw_documents()
    if not documents:
        raise ValueError("没有读取到任何 raw 文档，请检查 data/raw/static 或旧 knowledge 路径")

    manifest = load_manifest(settings.processed_manifest_path)
    changed_documents, removed_doc_ids = diff_documents(documents, manifest, mode=mode)
    index_exists = settings.new_index_path.exists() and settings.new_index_meta_path.exists()
    chunks_exist = settings.chunks_jsonl_path.exists()

    if mode == "incremental" and not changed_documents and not removed_doc_ids and index_exists and chunks_exist:
        return {
            "status": "skipped",
            "mode": mode,
            "reason": "manifest 未检测到资料变化，已跳过切片、embedding 和索引重建",
            "document_count": len(documents),
            "changed_document_count": 0,
            "removed_document_count": 0,
            "chunk_count": len(read_jsonl(settings.chunks_jsonl_path)),
            "index_path": str(settings.new_index_path),
            "chunks_path": str(settings.chunks_jsonl_path),
            "manifest_path": str(settings.processed_manifest_path),
        }

    # FAISS Flat index 没有便捷的按 doc_id 局部删除能力；资料有变化时采用整库重建。
    # 折中收益：无变化时完全跳过 embedding；有变化时保证索引与 manifest 一致。
    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("没有生成任何 chunk，请检查 raw 文档内容")

    write_jsonl(settings.processed_documents_path, documents)
    write_jsonl(settings.chunks_jsonl_path, chunks)

    chunk_counts = Counter(chunk["doc_id"] for chunk in chunks)
    manifest = update_manifest(
        manifest=manifest,
        documents=documents,
        chunk_counts=dict(chunk_counts),
        removed_doc_ids=removed_doc_ids,
    )
    save_manifest(settings.processed_manifest_path, manifest)

    embedding_provider = create_embedding_provider()
    embeddings = embeddings_to_numpy(embedding_provider.embed([chunk["content"] for chunk in chunks]))

    store = VectorStore(
        index_path=settings.new_index_path,
        chunks_path=settings.chunks_jsonl_path,
        index_meta_path=settings.new_index_meta_path,
    )
    store.build(embeddings, chunks)
    index_meta = {
        **embedding_provider.meta(),
        "chunk_count": len(chunks),
        "document_count": len(documents),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_documents_path": str(settings.processed_documents_path),
        "source_chunks_path": str(settings.chunks_jsonl_path),
        "chunks": [_chunk_metadata(chunk) for chunk in chunks],
    }
    store.save(index_meta=index_meta)

    return {
        "status": "completed",
        "mode": mode,
        "document_count": len(documents),
        "changed_document_count": len(changed_documents),
        "removed_document_count": len(removed_doc_ids),
        "chunk_count": len(chunks),
        "index_path": str(settings.new_index_path),
        "chunks_path": str(settings.chunks_jsonl_path),
        "documents_path": str(settings.processed_documents_path),
        "manifest_path": str(settings.processed_manifest_path),
        "index_metadata_path": str(settings.new_index_meta_path),
        "embedding_provider": index_meta["embedding_provider"],
        "embedding_model": index_meta["embedding_model"],
        "embedding_dimension": index_meta["embedding_dimension"],
    }


def _chunk_metadata(chunk: dict) -> dict:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "doc_id": chunk.get("doc_id"),
        "title": chunk.get("title"),
        "city": chunk.get("city"),
        "category": chunk.get("category"),
        "tags": chunk.get("tags", []),
        "source": chunk.get("source"),
        "updated_at": chunk.get("updated_at"),
    }

from __future__ import annotations

import json
import logging
from pathlib import Path

import faiss
import numpy as np

from app.config import settings


logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        index_path: Path = settings.index_path,
        chunks_path: Path = settings.chunks_path,
        index_meta_path: Path = settings.index_meta_path,
    ):
        self.index_path = Path(index_path)
        self.chunks_path = Path(chunks_path)
        self.index_meta_path = Path(index_meta_path)
        self.index = None
        self.chunks: list[dict | str] = []
        self.index_meta: dict = {}

    def build(self, embeddings: np.ndarray, chunks: list[dict | str]) -> None:
        embeddings = np.array(embeddings).astype("float32")
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self.chunks = chunks

    def save(self, index_meta: dict | None = None) -> None:
        if self.index is None:
            raise ValueError("当前没有 Index 可以保存。")

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_meta_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

        self._write_chunks()

        if index_meta is not None:
            self.index_meta = index_meta
            with open(self.index_meta_path, "w", encoding="utf-8") as file:
                json.dump(index_meta, file, ensure_ascii=False, indent=2)

    def load(self) -> None:
        self.index = None
        self.chunks = []
        self.index_meta = {}

        if self.chunks_path.exists():
            self.chunks = self._read_chunks()
        else:
            logger.warning("[RAG] chunks 文件不存在：%s", self.chunks_path)

        if self.index_meta_path.exists():
            with open(self.index_meta_path, "r", encoding="utf-8") as file:
                self.index_meta = json.load(file)
        else:
            logger.warning("[RAG] index_meta 文件不存在，将按关键词检索降级：%s", self.index_meta_path)

        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
            except Exception as exc:
                logger.warning("[RAG] FAISS index 读取失败，将按关键词检索降级：%s", exc)
                self.index = None
        else:
            logger.warning("[RAG] FAISS index 文件不存在，将按关键词检索降级：%s", self.index_path)

    def _read_chunks(self) -> list[dict | str]:
        if self.chunks_path.suffix.lower() == ".jsonl":
            chunks: list[dict | str] = []
            with open(self.chunks_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line:
                        chunks.append(json.loads(line))
            return chunks

        with open(self.chunks_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_chunks(self) -> None:
        with open(self.chunks_path, "w", encoding="utf-8") as file:
            if self.chunks_path.suffix.lower() == ".jsonl":
                for chunk in self.chunks:
                    file.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            else:
                json.dump(self.chunks, file, ensure_ascii=False, indent=2)

    def search(self, query_vector: np.ndarray, top_k: int = 3) -> list[dict]:
        if self.index is None:
            logger.warning("[RAG] FAISS index 不可用，本次跳过向量检索")
            return []

        query_vector = np.array(query_vector).astype("float32")
        distances, indices = self.index.search(query_vector, top_k)
        results = []

        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue

            item = self.chunks[idx]
            if isinstance(item, dict):
                content = item.get("content", "")
                metadata = {key: value for key, value in item.items() if key != "content"}
            else:
                content = str(item)
                metadata = {}

            results.append({
                "chunk_index": int(idx),
                "score": float(score),
                "chunk": content,
                "metadata": metadata,
            })

        return results


def load_knowledge_items(path: Path = settings.knowledge_json_path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"知识库文件不存在：{path}")

    with open(path, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("knowledge.json 最外层必须是列表")

    return data


def load_vector_store() -> VectorStore:
    if settings.new_index_path.exists() and settings.chunks_jsonl_path.exists() and settings.new_index_meta_path.exists():
        index_path = settings.new_index_path
        chunks_path = settings.chunks_jsonl_path
        index_meta_path = settings.new_index_meta_path
    else:
        index_path = settings.index_path
        chunks_path = settings.chunks_path
        index_meta_path = settings.index_meta_path

    store = VectorStore(
        index_path=index_path,
        chunks_path=chunks_path,
        index_meta_path=index_meta_path,
    )
    store.load()
    return store

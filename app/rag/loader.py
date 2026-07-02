from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingModel:
    def __init__(self, model_name: str = settings.embedding_model, cache_size: int = settings.embedding_cache_size):
        self.model = SentenceTransformer(model_name)
        self._embed_one_cached = lru_cache(maxsize=cache_size)(self._embed_one)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = self.model.encode([text], normalize_embeddings=True)[0]
        return tuple(float(value) for value in vector)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = [self._embed_one_cached(str(text)) for text in texts]
        return np.array(vectors, dtype="float32")

    def clear_cache(self) -> None:
        self._embed_one_cached.cache_clear()


class VectorStore:
    def __init__(self, index_path: Path = settings.index_path, chunks_path: Path = settings.chunks_path):
        self.index_path = Path(index_path)
        self.chunks_path = Path(chunks_path)
        self.index = None
        self.chunks: list[dict | str] = []

    def build(self, embeddings: np.ndarray, chunks: list[dict | str]) -> None:
        embeddings = np.array(embeddings).astype("float32")
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self.chunks = chunks

    def search(self, query_vector: np.ndarray, top_k: int = 3) -> list[dict]:
        if self.index is None:
            raise ValueError("FAISS Index 尚未建立，请先 build() 或 load()。")

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

    def save(self) -> None:
        if self.index is None:
            raise ValueError("当前没有 Index 可以保存。")

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

        with open(self.chunks_path, "w", encoding="utf-8") as file:
            json.dump(self.chunks, file, ensure_ascii=False, indent=2)

    def load(self) -> None:
        self.index = faiss.read_index(str(self.index_path))
        with open(self.chunks_path, "r", encoding="utf-8") as file:
            self.chunks = json.load(file)


def load_knowledge_items(path: Path = settings.knowledge_json_path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"知识库文件不存在：{path}")

    with open(path, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("knowledge.json 最外层必须是列表")

    return data


def load_vector_store() -> VectorStore:
    store = VectorStore()
    store.load()
    return store

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

import httpx
import numpy as np

from app.config import settings


logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    name = "base"

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def meta(self) -> dict[str, Any]:
        return {
            "embedding_provider": self.name,
            "embedding_model": self.model,
            "embedding_dimension": self.dimension,
        }


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) * float(value) for value in vector))
    if norm <= 0:
        return [float(value) for value in vector]
    return [float(value) / norm for value in vector]


def embeddings_to_numpy(vectors: list[list[float]]) -> np.ndarray:
    return np.array(vectors, dtype="float32")


class DashScopeEmbeddingProvider(EmbeddingProvider):
    name = "dashscope"

    def __init__(
        self,
        api_key: str | None = settings.embedding_api_key,
        base_url: str | None = settings.embedding_base_url,
        model: str = settings.embedding_model,
        dimension: int = settings.embedding_dimension,
        batch_size: int = settings.embedding_batch_size,
        timeout: float = settings.embedding_timeout,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
        self._model = model
        self._dimension = int(dimension)
        self.batch_size = max(1, int(batch_size))
        self.timeout = float(timeout)

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("缺少 EMBEDDING_API_KEY，无法调用百炼 Embedding API。")

        clean_texts = [str(text) for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(clean_texts), self.batch_size):
            batch = clean_texts[start : start + self.batch_size]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = self._endpoint()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "input": texts, "dimensions": self.dimension}

        response = httpx.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        vectors = self._parse_vectors(data)
        if len(vectors) != len(texts):
            raise RuntimeError(f"Embedding 返回数量不一致：请求 {len(texts)} 条，返回 {len(vectors)} 条")

        normalized = [normalize_vector(vector) for vector in vectors]
        for vector in normalized:
            if len(vector) != self.dimension:
                raise RuntimeError(
                    f"Embedding 维度不匹配：配置 {self.dimension}，接口返回 {len(vector)}。"
                    "请确认 EMBEDDING_API_MODEL 和 EMBEDDING_DIMENSION，并重新构建索引。"
                )
        return normalized

    def _endpoint(self) -> str:
        if self.base_url.endswith("/embeddings"):
            return self.base_url
        return f"{self.base_url}/embeddings"

    def _parse_vectors(self, data: dict[str, Any]) -> list[list[float]]:
        if isinstance(data.get("data"), list):
            ordered = sorted(data["data"], key=lambda item: item.get("index", 0))
            return [item["embedding"] for item in ordered if "embedding" in item]

        output = data.get("output") or {}
        embeddings = output.get("embeddings")
        if isinstance(embeddings, list):
            ordered = sorted(embeddings, key=lambda item: item.get("text_index", item.get("index", 0)))
            return [item["embedding"] for item in ordered if "embedding" in item]

        raise RuntimeError("Embedding API 返回格式无法识别。")


class LocalEmbeddingProvider(EmbeddingProvider):
    name = "local"

    def __init__(
        self,
        model: str = "BAAI/bge-m3",
        dimension: int = settings.embedding_dimension,
        cache_size: int = settings.embedding_cache_size,
    ):
        self._model = model
        self._dimension = int(dimension)
        self._sentence_transformer = None
        self._embed_one_cached = lru_cache(maxsize=cache_size)(self._embed_one)

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(self._embed_one_cached(str(text))) for text in texts]

    def clear_cache(self) -> None:
        self._embed_one_cached.cache_clear()

    def _load_model(self):
        if self._sentence_transformer is None:
            from sentence_transformers import SentenceTransformer

            logger.warning("[RAG] 正在加载本地 Embedding 模型：%s", self.model)
            self._sentence_transformer = SentenceTransformer(self.model)
        return self._sentence_transformer

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = self._load_model().encode([text], normalize_embeddings=True)[0]
        values = [float(value) for value in vector]
        if len(values) != self.dimension:
            raise RuntimeError(f"本地 Embedding 维度不匹配：配置 {self.dimension}，模型返回 {len(values)}")
        return tuple(values)


def create_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower().replace("-", "_")
    if provider in {"dashscope", "bailian", "aliyun"}:
        return DashScopeEmbeddingProvider()
    if provider in {"local", "sentence_transformer", "sentence_transformers"}:
        return LocalEmbeddingProvider(model=settings.embedding_model, dimension=settings.embedding_dimension)
    raise ValueError(f"不支持的 EMBEDDING_PROVIDER：{settings.embedding_provider}")

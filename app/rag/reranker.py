from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class RerankProvider(ABC):
    name = "base"

    @abstractmethod
    def rerank(self, question: str, candidates: list[dict]) -> list[dict]:
        raise NotImplementedError


class DashScopeRerankProvider(RerankProvider):
    name = "dashscope"

    def __init__(
        self,
        api_key: str | None = settings.rerank_api_key,
        base_url: str | None = settings.rerank_base_url,
        model: str = settings.rerank_model,
        top_n: int = settings.rerank_top_n,
        timeout: float = settings.rerank_timeout,
    ):
        self.api_key = api_key
        self.base_url = (
            base_url or "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
        ).rstrip("/")
        self.model = model
        self.top_n = max(1, int(top_n))
        self.timeout = float(timeout)

    def rerank(self, question: str, candidates: list[dict]) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("缺少 RERANK_API_KEY，无法调用百炼 Rerank API。")
        if not candidates:
            return []

        documents = [self._candidate_text(candidate) for candidate in candidates]
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "input": {
                "query": question,
                "documents": documents,
            },
            "parameters": {
                "top_n": min(self.top_n, len(documents)),
                "return_documents": False,
            },
        }
        response = httpx.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        ranked = self._parse_results(data)
        if not ranked:
            raise RuntimeError("Rerank API 没有返回排序结果。")

        seen_indexes = set()
        reranked: list[dict] = []
        for index, score in ranked:
            if index < 0 or index >= len(candidates) or index in seen_indexes:
                continue
            item = dict(candidates[index])
            item["rerank_score"] = float(score)
            item["final_score"] = float(score)
            item["rerank_provider"] = self.name
            reranked.append(item)
            seen_indexes.add(index)

        for index, candidate in enumerate(candidates):
            if index in seen_indexes:
                continue
            item = dict(candidate)
            item["final_score"] = float(item.get("score", item.get("hybrid_score", 0.0)) or 0.0)
            reranked.append(item)

        return reranked

    def _candidate_text(self, candidate: dict) -> str:
        metadata = candidate.get("metadata", {}) or {}
        fields = [
            metadata.get("title", ""),
            metadata.get("city", ""),
            metadata.get("category", ""),
            " ".join(str(tag) for tag in metadata.get("tags", []) or []),
            candidate.get("chunk", ""),
        ]
        return "\n".join(str(field) for field in fields if field)

    def _parse_results(self, data: dict[str, Any]) -> list[tuple[int, float]]:
        output = data.get("output") or {}
        results = output.get("results") or data.get("results") or []
        ranked = []
        for item in results:
            index = item.get("index", item.get("document_index"))
            score = item.get("relevance_score", item.get("score"))
            if index is None or score is None:
                continue
            ranked.append((int(index), float(score)))
        return ranked


def create_rerank_provider() -> RerankProvider | None:
    if not settings.rerank_enable:
        return None

    provider = settings.rerank_provider.lower().replace("-", "_")
    if provider in {"dashscope", "bailian", "aliyun"}:
        if not settings.rerank_api_key:
            logger.warning("[RAG] RERANK_API_KEY 未配置，Reranker 本次关闭并保留原始召回顺序")
            return None
        return DashScopeRerankProvider()
    raise ValueError(f"不支持的 RERANK_PROVIDER：{settings.rerank_provider}")

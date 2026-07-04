from __future__ import annotations

import logging

from app.config import settings
from app.rag.embeddings import create_embedding_provider
from app.rag.generator import LLMGenerator
from app.rag.loader import load_vector_store
from app.rag.prompt import build_prompt
from app.rag.reranker import create_rerank_provider
from app.rag.retriever import Retriever
from app.schemas import RAGResult, RetrievalReport, SourceRef


UNCERTAIN_ANSWER = "根据当前资料，我无法确认。"
logger = logging.getLogger(__name__)


def source_refs_from_results(results: list[dict]) -> list[SourceRef]:
    sources = []
    seen = set()

    for result in results:
        metadata = result.get("metadata", {})
        title = metadata.get("title") or metadata.get("city") or "本地知识片段"
        tags = metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        score = float(result.get("final_score", result.get("rerank_score", result.get("score", 0.0))) or 0.0)
        rerank_score = result.get("rerank_score")
        source = SourceRef(
            id=str(metadata.get("id") or metadata.get("doc_id") or "") or None,
            title=title,
            city=metadata.get("city"),
            country=metadata.get("country"),
            category=metadata.get("category"),
            score=score,
            vector_score=_optional_float(result.get("vector_score", result.get("faiss_score"))),
            bm25_score=_optional_float(result.get("bm25_score")),
            rerank_score=_optional_float(rerank_score),
            content=result.get("chunk"),
            source_url=metadata.get("source_url") or metadata.get("source"),
            freshness=metadata.get("freshness"),
            tags=[str(tag) for tag in tags],
        )
        source_key = (source.id, source.title, source.city, source.category)
        if source_key not in seen:
            sources.append(source)
            seen.add(source_key)

    return sources


def append_sources(answer: str, sources: list[SourceRef]) -> str:
    if not sources or "依据：" in answer:
        return answer
    source_line = "依据：" + " / ".join(source.title or "本地知识片段" for source in sources)
    return f"{answer.rstrip()}\n\n{source_line}"


def realtime_refusal() -> str:
    return (
        f"{UNCERTAIN_ANSWER}\n"
        "这个问题包含今天、现在、营业时间、票价、天气等实时信号，"
        "当前项目还没有接入实时搜索或官方接口，所以不能只凭本地知识库硬答。"
    )


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class RAGPipeline:
    def __init__(self, retriever: Retriever, generator: LLMGenerator):
        self.retriever = retriever
        self.generator = generator

    def run(self, question: str) -> RAGResult:
        question = question.strip()
        analysis = self.retriever.analyze_query(question)

        if analysis.question_type == "missing":
            return RAGResult(
                answer=UNCERTAIN_ANSWER,
                query_type=analysis.question_type,
                confident=False,
                refusal_reason="问题为空或缺少可分析内容",
                diagnostics={"analysis": analysis.to_dict()},
            )

        if analysis.needs_realtime:
            logger.info("[RAG] 实时问题不走本地 RAG 硬答：%s", analysis.to_dict())
            return RAGResult(
                answer=realtime_refusal(),
                query_type=analysis.question_type,
                confident=False,
                refusal_reason="问题需要实时信息，当前未接入实时工具",
                diagnostics={"analysis": analysis.to_dict()},
            )

        report = self.retriever.retrieve_with_report(question=question, top_k=settings.top_k)
        self._log_report(report)
        sources = source_refs_from_results(report.results)

        if not report.results:
            return RAGResult(
                answer=UNCERTAIN_ANSWER,
                query_type=report.analysis.question_type,
                confident=False,
                refusal_reason="没有召回任何资料",
                sources=sources,
                diagnostics=self._diagnostics(report),
            )

        if not report.is_confident:
            return RAGResult(
                answer=f"{UNCERTAIN_ANSWER}\n{report.confidence_reason}",
                query_type=report.analysis.question_type,
                confident=False,
                refusal_reason=report.confidence_reason,
                sources=sources,
                diagnostics=self._diagnostics(report),
            )

        contexts = [result["chunk"] for result in report.results if result.get("chunk")]
        if not contexts:
            return RAGResult(
                answer=UNCERTAIN_ANSWER,
                query_type=report.analysis.question_type,
                confident=False,
                refusal_reason="召回结果中没有可用 chunk",
                sources=sources,
                diagnostics=self._diagnostics(report),
            )

        prompt = build_prompt(contexts=contexts, question=question, sources=sources)
        try:
            answer = self.generator.generate(prompt)
        except Exception as exc:
            logger.warning("[RAG] LLM 生成失败，保留召回证据并返回降级回答：%s", exc)
            return RAGResult(
                answer=f"{UNCERTAIN_ANSWER}\n已召回相关资料，但生成模型暂时不可用：{exc}",
                query_type=report.analysis.question_type,
                confident=False,
                refusal_reason="LLM 生成失败",
                sources=sources,
                diagnostics=self._diagnostics(report),
            )
        return RAGResult(
            answer=append_sources(answer, sources),
            query_type=report.analysis.question_type,
            confident=True,
            sources=sources,
            diagnostics=self._diagnostics(report),
        )

    def _diagnostics(self, report: RetrievalReport) -> dict:
        return {
            "strategy": report.strategy,
            "candidate_count": report.candidate_count,
            "confidence_reason": report.confidence_reason,
            "analysis": report.analysis.to_dict(),
            "retrieval": report.diagnostics,
        }

    def _log_report(self, report: RetrievalReport) -> None:
        logger.info("[RAG] 用户问题：%s", report.question)
        logger.info("[RAG] Query Analysis：%s", report.analysis.to_dict())
        logger.info(
            "[RAG] 候选数量：%s | 置信度：%s | 原因：%s",
            report.candidate_count,
            report.is_confident,
            report.confidence_reason,
        )
        for index, result in enumerate(report.results, start=1):
            metadata = result.get("metadata", {})
            preview = result.get("chunk", "").replace("\n", " ")[:120]
            logger.info(
                "[RAG] 结果 %s | final=%.4f | hybrid=%.4f | faiss=%.4f | bm25=%.4f | match=%s | metadata=%s | content=%s",
                index,
                float(result.get("final_score", 0.0)),
                float(result.get("hybrid_score", 0.0)),
                float(result.get("faiss_norm", 0.0)),
                float(result.get("bm25_norm", 0.0)),
                result.get("match_info", {}),
                metadata,
                preview,
            )


def create_pipeline() -> RAGPipeline:
    store = load_vector_store()
    embedding_provider = None
    vector_enabled = _index_matches_current_embedding(store.index_meta)

    if not vector_enabled:
        logger.warning("[RAG] 当前 Embedding 配置与索引不一致或缺少元数据，本次服务降级为 BM25-only")

    try:
        if settings.rag_enable_vector and vector_enabled and store.index is not None:
            if _embedding_key_ready():
                embedding_provider = create_embedding_provider()
            else:
                logger.warning("[RAG] EMBEDDING_API_KEY 未配置，向量检索关闭并降级为 BM25-only")
    except Exception as exc:
        logger.warning("[RAG] Embedding Provider 初始化失败，降级为 BM25-only 检索：%s", exc)
        embedding_provider = None

    try:
        rerank_provider = create_rerank_provider()
    except Exception as exc:
        logger.warning("[RAG] Reranker Provider 初始化失败，保留原始召回顺序：%s", exc)
        rerank_provider = None

    retriever = Retriever(
        store=store,
        embedding_model=embedding_provider,
        rerank_provider=rerank_provider,
        vector_enabled=vector_enabled,
    )
    generator = LLMGenerator()
    return RAGPipeline(retriever=retriever, generator=generator)


def _index_matches_current_embedding(index_meta: dict) -> bool:
    if not settings.rag_enable_vector:
        return False
    if not index_meta:
        return False

    expected = {
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
    }
    actual = {
        "embedding_provider": index_meta.get("embedding_provider"),
        "embedding_model": index_meta.get("embedding_model"),
        "embedding_dimension": index_meta.get("embedding_dimension"),
    }
    try:
        actual_dimension = int(actual["embedding_dimension"] or 0)
    except (TypeError, ValueError):
        actual_dimension = 0

    matches = (
        str(actual["embedding_provider"]).lower() == str(expected["embedding_provider"]).lower()
        and str(actual["embedding_model"]) == str(expected["embedding_model"])
        and actual_dimension == int(expected["embedding_dimension"])
    )
    if not matches:
        logger.warning("[RAG] 索引配置不匹配，expected=%s actual=%s", expected, actual)
    return matches


def _embedding_key_ready() -> bool:
    provider = settings.embedding_provider.lower().replace("-", "_")
    if provider in {"dashscope", "bailian", "aliyun"}:
        return bool(settings.embedding_api_key)
    return True

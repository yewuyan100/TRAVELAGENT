from __future__ import annotations

import logging

from app.config import settings
from app.rag.generator import LLMGenerator
from app.rag.loader import EmbeddingModel, load_vector_store
from app.rag.prompt import build_prompt
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
        source = SourceRef(
            id=str(metadata.get("id", "")) or None,
            title=title,
            city=metadata.get("city"),
            country=metadata.get("country"),
            category=metadata.get("category"),
            score=score,
            content=result.get("chunk"),
            source_url=metadata.get("source_url"),
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
        answer = self.generator.generate(prompt)
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
    try:
        embedding_model = EmbeddingModel()
    except Exception as exc:
        logger.warning("[RAG] Embedding 模型加载失败，降级为 BM25-only 检索：%s", exc)
        embedding_model = None
    retriever = Retriever(store=store, embedding_model=embedding_model)
    generator = LLMGenerator()
    return RAGPipeline(retriever=retriever, generator=generator)

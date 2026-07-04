from __future__ import annotations

from app.rag.pipeline import RAGPipeline, UNCERTAIN_ANSWER
from app.schemas import SourceRef


def _confidence_from_diagnostics(diagnostics: dict, confident: bool) -> float:
    retrieval = diagnostics.get("retrieval", {}) if diagnostics else {}
    score = retrieval.get("best_rerank_score", 0.0)
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    if confident:
        return max(0.01, min(score, 1.0))
    return max(0.0, min(score, 1.0))


class RagTool:
    name = "rag_tool"

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline

    def run(self, question: str, city: str | None = None, category: str | None = None) -> dict:
        scoped_question = question
        if city and city not in question:
            scoped_question = f"{city} {scoped_question}"
        if category and category not in question:
            scoped_question = f"{scoped_question} {category}"

        try:
            result = self.pipeline.run(scoped_question)
        except Exception as exc:
            return {
                "answer": f"{UNCERTAIN_ANSWER}\nRAG 工具调用失败：{exc}",
                "confidence": 0.0,
                "sources": [],
                "retrieved_chunks": [],
                "metadata": {
                    "rerank_enabled": False,
                    "rerank_used": False,
                    "fallback_used": True,
                    "error": str(exc),
                },
                "refused": True,
            }

        sources = [source.model_dump() for source in result.sources]
        retrieved_chunks = [_source_to_chunk(source) for source in result.sources]
        retrieval = result.diagnostics.get("retrieval", {}) if result.diagnostics else {}
        rerank_used = any(source.rerank_score is not None for source in result.sources)

        return {
            "answer": result.answer,
            "confidence": _confidence_from_diagnostics(result.diagnostics, result.confident),
            "sources": sources,
            "retrieved_chunks": retrieved_chunks,
            "diagnostics": result.diagnostics,
            "metadata": {
                "rerank_enabled": bool(retrieval.get("rerank_enabled")),
                "rerank_used": rerank_used,
                "fallback_used": not result.confident,
                "refusal_reason": result.refusal_reason,
            },
            "refused": not result.confident,
        }


def source_dicts_to_refs(items: list[dict]) -> list[SourceRef]:
    return [SourceRef(**item) for item in items]


def _source_to_chunk(source: SourceRef) -> dict:
    content = source.content or ""
    preview = content.replace("\n", " ").strip()
    if len(preview) > 180:
        preview = preview[:180].rstrip() + "..."
    return {
        "chunk_id": source.id,
        "title": source.title,
        "city": source.city,
        "category": source.category,
        "score": source.score,
        "content_preview": preview,
    }

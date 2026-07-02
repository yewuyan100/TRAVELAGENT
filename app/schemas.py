from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None


class SourceRef(BaseModel):
    id: str = ""
    title: str = "本地知识片段"
    city: str = "未知城市"
    category: str = "unknown"
    score: float = 0.0
    tags: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    intent: str
    selected_tool: str
    confidence: float
    sources: list[SourceRef] = Field(default_factory=list)
    refused: bool


@dataclass(frozen=True)
class QueryAnalysis:
    question: str
    question_type: str
    needs_realtime: bool = False
    city: str | None = None
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    reason: str = ""
    analyzed_at: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "question_type": self.question_type,
            "needs_realtime": self.needs_realtime,
            "city": self.city,
            "categories": self.categories,
            "tags": self.tags,
            "entities": self.entities,
            "reason": self.reason,
            "analyzed_at": self.analyzed_at,
        }


@dataclass
class RetrievalReport:
    question: str
    analysis: QueryAnalysis
    results: list[dict]
    candidate_count: int
    is_confident: bool
    confidence_reason: str
    strategy: str = "hybrid_bm25_faiss_rerank"
    diagnostics: dict = field(default_factory=dict)


@dataclass
class RAGResult:
    answer: str
    query_type: str
    confident: bool
    sources: list[SourceRef] = field(default_factory=list)
    refusal_reason: str | None = None
    diagnostics: dict = field(default_factory=dict)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "query_type": self.query_type,
            "confident": self.confident,
            "sources": [source.model_dump() for source in self.sources],
            "refusal_reason": self.refusal_reason,
            "diagnostics": self.diagnostics,
        }


@dataclass
class AgentState:
    question: str
    session_id: str
    intent: str = "unsupported"
    selected_tool: str = "refuse"
    city: str | None = None
    category: str | None = None
    days: int | None = None
    places: list[str] = field(default_factory=list)
    tool_result: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    answer: str
    session_id: str
    intent: str
    selected_tool: str
    confidence: float = 0.0
    sources: list[SourceRef] = field(default_factory=list)
    refused: bool = False

    def to_response(self) -> ChatResponse:
        return ChatResponse(
            answer=self.answer,
            session_id=self.session_id,
            intent=self.intent,
            selected_tool=self.selected_tool,
            confidence=float(self.confidence),
            sources=self.sources,
            refused=bool(self.refused),
        )

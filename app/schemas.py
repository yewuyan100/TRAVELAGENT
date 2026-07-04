from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None


class SourceRef(BaseModel):
    id: str | None = None
    title: str | None = "本地知识片段"
    city: str | None = None
    country: str | None = None
    category: str | None = None
    score: float | None = None
    vector_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    content: str | None = None
    source_url: str | None = None
    freshness: str | None = None
    tags: list[str] = Field(default_factory=list)


class ResponseCard(BaseModel):
    type: str
    title: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class FoodRecommendation(BaseModel):
    name: str
    reason: str | None = None
    area: str | None = None
    tags: list[str] = Field(default_factory=list)


class TravelTip(BaseModel):
    title: str
    content: str


class ItineraryStop(BaseModel):
    name: str
    type: str | None = None
    description: str | None = None
    lat: float | None = None
    lng: float | None = None


class ItineraryDayPlan(BaseModel):
    day: int
    theme: str | None = None
    pace: str | None = None
    spots: list[ItineraryStop] = Field(default_factory=list)
    routes: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None


class TaskPlanStep(BaseModel):
    step: str
    tool: str
    reason: str


class ToolUsage(BaseModel):
    tool: str
    status: str
    summary: str


class RetrievedChunk(BaseModel):
    chunk_id: str | None = None
    title: str | None = None
    city: str | None = None
    category: str | None = None
    score: float | None = None
    content_preview: str | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    city: str | None = None
    itinerary: list[ItineraryDayPlan] = Field(default_factory=list)
    food_recommendations: list[FoodRecommendation] = Field(default_factory=list)
    tips: list[TravelTip] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    selected_tool: str
    confidence: float
    cards: list[ResponseCard] = Field(default_factory=list)
    task_plan: list[TaskPlanStep] = Field(default_factory=list)
    tools_used: list[ToolUsage] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] | None = None


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
    city: str | None = None
    itinerary: list[ItineraryDayPlan] = field(default_factory=list)
    food_recommendations: list[FoodRecommendation] = field(default_factory=list)
    tips: list[TravelTip] = field(default_factory=list)
    confidence: float = 0.0
    sources: list[SourceRef] = field(default_factory=list)
    cards: list[ResponseCard] = field(default_factory=list)
    task_plan: list[TaskPlanStep] = field(default_factory=list)
    tools_used: list[ToolUsage] = field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    refused: bool = False
    debug: dict[str, Any] | None = None

    def to_response(self) -> ChatResponse:
        return ChatResponse(
            answer=self.answer,
            intent=self.intent,
            city=self.city,
            itinerary=self.itinerary,
            food_recommendations=self.food_recommendations,
            tips=self.tips,
            selected_tool=self.selected_tool,
            confidence=float(self.confidence),
            sources=self.sources,
            cards=self.cards,
            task_plan=self.task_plan,
            tools_used=self.tools_used,
            retrieved_chunks=self.retrieved_chunks,
            metadata=self.metadata,
            debug=self.debug,
        )

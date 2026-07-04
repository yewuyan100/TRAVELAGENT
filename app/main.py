from contextlib import asynccontextmanager
import json
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents.travel_agent import TravelAgent, create_travel_agent
from app.config import settings
from app.rag.ingestion.pipeline import run_ingestion_pipeline
from app.schemas import ChatRequest, ChatResponse
from app.tools.weather_tool import WeatherTool
from app.utils.logger import get_logger, setup_logging


setup_logging()
logger = get_logger(__name__)
agent: TravelAgent | None = None


def get_agent() -> TravelAgent:
    global agent
    if agent is None:
        logger.info("初始化 Travel Agent")
        agent = create_travel_agent()
    return agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title="Travel Agent API",
    description="基于 RAG 与工具调用的智能旅游 Agent 系统",
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Travel Agent API is running", "version": "0.6.0"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "travel-agent"}


def _read_json_file(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


@app.get("/admin/knowledge/status")
def knowledge_status():
    manifest = _read_json_file(settings.processed_manifest_path) or {"documents": {}}
    index_meta = _read_json_file(settings.new_index_meta_path)
    active_docs = [
        doc for doc in manifest.get("documents", {}).values()
        if doc.get("status") == "active"
    ]
    inactive_docs = [
        doc for doc in manifest.get("documents", {}).values()
        if doc.get("status") == "inactive"
    ]
    return {
        "status": "ok",
        "paths": {
            "raw_static": str(settings.raw_static_knowledge_path),
            "documents": str(settings.processed_documents_path),
            "manifest": str(settings.processed_manifest_path),
            "chunks": str(settings.chunks_jsonl_path),
            "index": str(settings.new_index_path),
            "index_metadata": str(settings.new_index_meta_path),
            "legacy_index": str(settings.index_path),
        },
        "exists": {
            "documents": settings.processed_documents_path.exists(),
            "manifest": settings.processed_manifest_path.exists(),
            "chunks": settings.chunks_jsonl_path.exists(),
            "index": settings.new_index_path.exists(),
            "index_metadata": settings.new_index_meta_path.exists(),
        },
        "document_count": len(active_docs),
        "inactive_document_count": len(inactive_docs),
        "chunk_count": (index_meta or {}).get("chunk_count", 0),
        "embedding": {
            "provider": (index_meta or {}).get("embedding_provider"),
            "model": (index_meta or {}).get("embedding_model"),
            "dimension": (index_meta or {}).get("embedding_dimension"),
        },
        "updated_at": manifest.get("updated_at"),
    }


@app.post("/admin/knowledge/rebuild")
def knowledge_rebuild():
    # TODO: 生产环境接入鉴权后再开放此接口。
    global agent
    result = run_ingestion_pipeline(mode="full")
    agent = None
    return result


@app.post("/admin/knowledge/update")
def knowledge_update():
    # TODO: 生产环境接入鉴权后再开放此接口。
    global agent
    result = run_ingestion_pipeline(mode="incremental")
    if result.get("status") == "completed":
        agent = None
    return result


def _mock_weather(city: str) -> dict:
    return {
        "available": True,
        "provider": "mock",
        "city": city,
        "condition": "多云",
        "current_temperature": 22,
        "temp_min": 18,
        "temp_max": 26,
        "rain_probability": 20,
        "wind": "微风",
        "travel_advice": "适合城市漫游，建议随身带一件薄外套。",
        "summary": f"{city} 22°C，多云。适合轻松出行。",
        "forecast": [],
        "mock": True,
    }


@app.get("/api/weather")
def weather_api(city: str = Query("成都", min_length=1)):
    result = WeatherTool().run(city=city.strip(), question=f"{city} 天气")
    if result.get("available"):
        return result

    mock = _mock_weather(city.strip())
    mock["message"] = result.get("message", "真实天气服务暂不可用，已返回 mock 数据。")
    return mock


def _handle_chat(request: ChatRequest) -> ChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        result = get_agent().run(question=question, session_id=request.session_id)
        return result.to_response()
    except Exception as exc:
        logger.exception("[CHAT] 回答失败")
        raise HTTPException(status_code=500, detail=f"AI旅游助手暂时不可用：{str(exc)}") from exc


def _ndjson_event(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _split_answer(answer: str, chunk_size: int = 24):
    text = answer or ""
    for start in range(0, len(text), chunk_size):
        yield text[start : start + chunk_size]


def _stream_chat_events(request: ChatRequest):
    question = request.question.strip()
    if not question:
        yield _ndjson_event({"type": "error", "message": "问题不能为空"})
        yield _ndjson_event({"type": "done"})
        return

    status_events = [
        {"type": "status", "stage": "analyzing", "message": "正在分析问题"},
        {"type": "status", "stage": "routing", "message": "正在选择工具"},
        {"type": "status", "stage": "retrieving", "message": "正在调用 Agent 工具"},
        {"type": "status", "stage": "generating", "message": "正在生成回答"},
    ]
    for event in status_events:
        yield _ndjson_event(event)
        time.sleep(0.03)

    try:
        response = _handle_chat(request)
    except HTTPException as exc:
        yield _ndjson_event({"type": "error", "message": str(exc.detail)})
        yield _ndjson_event({"type": "done"})
        return
    except Exception as exc:
        logger.exception("[CHAT_STREAM] 回答失败")
        yield _ndjson_event({"type": "error", "message": f"AI旅游助手暂时不可用：{exc}"})
        yield _ndjson_event({"type": "done"})
        return

    for chunk in _split_answer(response.answer):
        yield _ndjson_event({"type": "chunk", "content": chunk})
        time.sleep(0.02)

    yield _ndjson_event(
        {
            "type": "metadata",
            "intent": response.intent,
            "selected_tool": response.selected_tool,
            "confidence": response.confidence,
            "sources": [source.model_dump() for source in response.sources],
            "cards": [card.model_dump() for card in response.cards],
            "city": response.city,
            "itinerary": [day.model_dump() for day in response.itinerary],
            "food_recommendations": [food.model_dump() for food in response.food_recommendations],
            "tips": [tip.model_dump() for tip in response.tips],
            "task_plan": [step.model_dump() for step in response.task_plan],
            "tools_used": [tool.model_dump() for tool in response.tools_used],
            "retrieved_chunks": [chunk.model_dump() for chunk in response.retrieved_chunks],
            "metadata": response.metadata,
            "debug": response.debug,
        }
    )
    yield _ndjson_event({"type": "done"})


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return _handle_chat(request)


@app.post("/api/chat", response_model=ChatResponse)
def chat_api_alias(request: ChatRequest):
    return _handle_chat(request)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(_stream_chat_events(request), media_type="application/x-ndjson")


@app.post("/api/chat/stream")
def chat_stream_api_alias(request: ChatRequest):
    return StreamingResponse(_stream_chat_events(request), media_type="application/x-ndjson")

from contextlib import asynccontextmanager
import json
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents.travel_agent import TravelAgent, create_travel_agent
from app.config import settings
from app.schemas import ChatRequest, ChatResponse
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

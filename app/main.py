from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        result = get_agent().run(question=question, session_id=request.session_id)
        return result.to_response()
    except Exception as exc:
        logger.exception("[CHAT] 回答失败")
        raise HTTPException(status_code=500, detail=f"AI旅游助手暂时不可用：{str(exc)}") from exc

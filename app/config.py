import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def get_int_env(name: str, default: int) -> int:
    value = get_env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"配置 {name} 必须是整数，当前值是：{value}") from exc


def get_float_env(name: str, default: float) -> float:
    value = get_env(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"配置 {name} 必须是浮点数，当前值是：{value}") from exc


def get_path_env(*names: str, default: Path | str, base_dir: Path = PROJECT_ROOT) -> Path:
    value = None
    for name in names:
        value = get_env(name)
        if value:
            break
    path = Path(value) if value else Path(default)
    if path.is_absolute():
        return path
    return base_dir / path


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    app_dir: Path = APP_DIR

    llm_provider: str = get_env("LLM_PROVIDER", "qwen") or "qwen"
    llm_api_key: str | None = get_env("LLM_API_KEY", get_env("DEEPSEEK_API_KEY"))
    llm_base_url: str = get_env("LLM_BASE_URL", get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")) or "https://api.deepseek.com"
    llm_model: str = get_env("LLM_MODEL", get_env("DEEPSEEK_MODEL", "deepseek-v4-flash")) or "deepseek-v4-flash"

    embedding_provider: str = get_env("EMBEDDING_PROVIDER", "local") or "local"
    embedding_api_key: str | None = get_env("EMBEDDING_API_KEY")
    embedding_base_url: str | None = get_env("EMBEDDING_BASE_URL")
    embedding_model: str = get_env("EMBEDDING_MODEL", "BAAI/bge-m3") or "BAAI/bge-m3"
    embedding_cache_size: int = get_int_env("EMBEDDING_CACHE_SIZE", 512)

    knowledge_json_path: Path = get_path_env(
        "KNOWLEDGE_PATH",
        "KNOWLEDGE_JSON_PATH",
        default=PROJECT_ROOT / "data" / "knowledge" / "travel_knowledge.json",
    )
    index_path: Path = get_path_env(
        "FAISS_INDEX_PATH",
        "INDEX_PATH",
        default=PROJECT_ROOT / "data" / "travel.index",
    )
    chunks_path: Path = get_path_env(
        "CHUNKS_PATH",
        default=PROJECT_ROOT / "data" / "chunks.json",
    )

    top_k: int = get_int_env("TOP_K", 3)
    candidate_k: int = get_int_env("CANDIDATE_K", 20)
    bm25_weight: float = get_float_env("BM25_WEIGHT", 0.45)
    faiss_weight: float = get_float_env("FAISS_WEIGHT", 0.55)
    query_cache_size: int = get_int_env("QUERY_CACHE_SIZE", 128)

    min_retrieval_score: float = get_float_env("MIN_RETRIEVAL_SCORE", 0.35)
    min_rerank_score: float = get_float_env("MIN_RERANK_SCORE", 0.42)
    min_result_agreement: float = get_float_env("MIN_RESULT_AGREEMENT", 0.18)

    weather_provider: str = get_env("WEATHER_PROVIDER", "open_meteo") or "open_meteo"
    weather_api_key: str | None = get_env("WEATHER_API_KEY", get_env("QWEATHER_API_KEY"))
    weather_base_url: str = get_env("WEATHER_BASE_URL", "https://api.open-meteo.com") or "https://api.open-meteo.com"
    qweather_api_key: str | None = get_env("QWEATHER_API_KEY")

    map_provider: str = get_env("MAP_PROVIDER", "amap") or "amap"
    map_api_key: str | None = get_env("MAP_API_KEY", get_env("AMAP_API_KEY"))
    map_base_url: str = get_env("MAP_BASE_URL", "https://restapi.amap.com") or "https://restapi.amap.com"
    amap_api_key: str | None = get_env("AMAP_API_KEY")

    frontend_origin: str = get_env("FRONTEND_ORIGIN", "http://localhost:5173") or "http://localhost:5173"
    log_level: str = get_env("LOG_LEVEL", "INFO") or "INFO"
    system_prompt: str = (
        get_env(
            "SYSTEM_PROMPT",
            "你是一个 AI 旅游助手。\n"
            "请严格根据【旅游资料】回答用户问题。\n"
            "如果资料中没有明确答案，请回答：根据当前资料，我无法确认。\n"
            "不要编造营业时间、票价、天气、实时拥挤程度或资料里没有的细节。",
        )
        or ""
    ).replace("\\n", "\n")


settings = Settings()

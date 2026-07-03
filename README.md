# TravelAgent

TravelAgent 是一个基于 FastAPI、React、RAG 和工具调用的智能旅游助手项目。系统支持本地旅游知识库问答、城市推荐、天气查询、地图行程规划、来源展示和低置信度拒答。

## 核心能力

- 本地旅游知识库问答。
- BM25 + FAISS 混合检索。
- 百炼 `text-embedding-v4` 外部 Embedding。
- 百炼 `qwen3-rerank` 外部 Rerank。
- 天气工具：Open-Meteo fallback，支持扩展 QWeather / AMap。
- 地图行程工具：规则行程 fallback，支持扩展 AMap 地理编码和路线规划。
- React 聊天界面，展示回答、意图、工具、置信度、来源和卡片。
- 支持 `/chat` 和伪流式 `/chat/stream`。

## 技术栈

后端：

- Python 3.11+
- FastAPI
- Pydantic
- FAISS
- BM25
- OpenAI-compatible LLM API
- DashScope / 阿里云百炼 API

前端：

- React
- TypeScript
- Vite
- 高德地图 JS API 2.0

## 系统架构

```text
React 前端
  ↓
FastAPI Backend
  ↓
TravelAgent
  ↓
Agent Router
  ├── RAG Tool
  ├── Weather Tool
  └── Map Itinerary Tool
```

## RAG 数据链路

```text
data/knowledge/travel_knowledge.json
  ↓
scripts/rebuild_index.py
  ↓
data/chunks.json
data/travel.index
data/index_meta.json
  ↓
Retriever
  ↓
RAG Tool
```

更新知识库后重新构建索引：

```bash
python scripts/rebuild_index.py
```

如果修改了 embedding provider、model 或 dimension，也需要重新构建索引。

## Agent 路由

系统会根据用户问题选择工具：

- 稳定旅游知识、美食、景点、交通建议：`rag_tool`
- 天气、下雨、温度、是否适合出门：`weather_tool`
- 几天怎么玩、路线顺序、从 A 到 B 怎么走：`map_itinerary_tool`
- 实时票价、实时开放时间、资料不足问题：拒答

## API

### GET `/health`

健康检查。

### POST `/chat`

请求：

```json
{
  "question": "我喜欢美食和慢节奏旅行，推荐去哪里？"
}
```

响应核心字段：

```json
{
  "answer": "...",
  "intent": "food_recommendation",
  "selected_tool": "rag_tool",
  "confidence": 0.82,
  "sources": [],
  "cards": []
}
```

### POST `/chat/stream`

返回 NDJSON。当前为伪流式输出，用于前端逐段展示。

## 环境变量

核心配置见 `.env.example`。

常用配置：

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

EMBEDDING_PROVIDER=dashscope
EMBEDDING_API_KEY=
EMBEDDING_API_BASE_URL=
EMBEDDING_API_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024

RERANK_ENABLE=true
RERANK_PROVIDER=dashscope
RERANK_API_KEY=
RERANK_API_BASE_URL=
RERANK_MODEL=qwen3-rerank

WEATHER_PROVIDER=openmeteo
QWEATHER_API_KEY=

MAP_PROVIDER=rule
AMAP_API_KEY=
```

## 本地运行

后端：

```bash
python -m venv .venv
pip install -r requirements.txt
python scripts/rebuild_index.py
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 测试

```bash
python -m compileall app scripts
python scripts/eval_rag.py
```

前端构建：

<<<<<<< HEAD
- RAG 城市推荐。
- RAG 景点推荐。
- 天气工具。
- 地图 / 行程工具。
- 地图路线。
- 实时开放时间拒答。
- 实时票价拒答。
- 低置信度拒答。
- 无关问题拒答。
- 流式接口事件结构。

当前 eval 是轻量规则校验，不做复杂语义评分。
=======
```bash
cd frontend
npm run build
```
>>>>>>> e2650a9 (use external embedding and rerank providers)

## 当前限制

- `/chat/stream` 仍是伪流式。
- 天气和地图正式 provider 依赖外部 API。
- 海外地图路线规划暂未实现。
- Eval 目前是轻量规则校验。

## 后续方向

- 接入 LLM 原生 streaming。
- 增强 Reranker 评估。
- 扩展 AMap 多交通方式路线规划。
- 增加前端地图交互。
- 增加 CI/CD。

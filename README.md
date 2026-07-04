# AI Travel Agent

AI Travel Agent 是一个基于 FastAPI + React + TypeScript + Tailwind CSS 的智能旅行助手项目。当前版本重点支持旅行问答、天气查询、路线/行程规划、RAG 知识库检索，以及可解释的 Agent 工具调用过程展示。

## 功能概览

- AI 旅行问答
- 本地 RAG 知识库检索
- 天气查询工具
- 地图/行程规划工具
- Agent Trace 可解释过程展示
- 前端本地对话历史
- 知识库审核过滤
- RAG Pipeline：raw -> documents -> chunks -> embeddings -> vector index
- manifest 增量更新判断

## 技术栈

后端：

- FastAPI
- FAISS
- DashScope / Qwen Embedding
- OpenAI-compatible LLM Client
- 本地 RAG Retriever
- Agent Tool Router

前端：

- React
- TypeScript
- Tailwind CSS
- Vite
- Zustand
- lucide-react

## 项目结构

```text
app/
  agents/
    router.py
    travel_agent.py
  rag/
    ingestion/
      loaders.py
      cleaner.py
      normalizer.py
      chunker.py
      manifest.py
      pipeline.py
    retriever.py
    pipeline.py
    loader.py
  tools/
    rag_tool.py
    weather_tool.py
    map_itinerary_tool.py
  main.py
  schemas.py

frontend/
  src/
    api/
    components/
    store/
    types/

data/
  raw/
    static/
      travel_knowledge.json
    dynamic/
  processed/
    documents.jsonl
    manifest.json
  chunks/
    chunks.jsonl
  index/
    travel.index
    index_metadata.json
  knowledge/
    travel_knowledge.json

scripts/
  rebuild_knowledge_base.py
  rebuild_index.py
  merge_knowledge_draft.py
```

## 后端启动

```bash
uvicorn app.main:app --reload
```

默认 API 地址：

```text
http://localhost:8000
```

健康检查：

```text
GET /health
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：

```text
http://localhost:5173
```

## 核心接口

### Chat

```text
POST /api/chat
```

请求：

```json
{
  "question": "成都明天适合去人民公园吗？"
}
```

响应会保持兼容旧字段：

```json
{
  "answer": "...",
  "intent": "travel_decision",
  "city": "成都",
  "selected_tool": "multi_tool",
  "confidence": 0.72,
  "sources": [],
  "cards": [],
  "task_plan": [],
  "tools_used": [],
  "retrieved_chunks": [],
  "metadata": {}
}
```

### Agent Trace 字段

```json
{
  "task_plan": [
    {
      "step": "retrieve_knowledge",
      "tool": "rag",
      "reason": "需要查询本地旅游知识库"
    }
  ],
  "tools_used": [
    {
      "tool": "rag",
      "status": "success",
      "summary": "召回 3 条知识片段"
    }
  ],
  "retrieved_chunks": [
    {
      "chunk_id": "chengdu_overview_001",
      "title": "成都旅行整体特点",
      "city": "成都",
      "category": "overview",
      "score": 0.82,
      "content_preview": "..."
    }
  ],
  "metadata": {
    "rerank_enabled": true,
    "rerank_used": false,
    "fallback_used": false
  }
}
```

## Intent 类型

当前后端主要返回：

- `knowledge_qa`
- `weather_query`
- `map_query`
- `travel_decision`
- `itinerary_plan`
- `fallback`

示例：

```text
成都适合喜欢美食和慢节奏旅行的人吗？
```

主要走 RAG。

```text
成都明天天气怎么样？
```

主要走天气工具。

```text
从春熙路到熊猫基地怎么走？
```

主要走地图/行程工具。

```text
成都明天适合去人民公园吗？
```

走综合决策，包含 RAG + 天气。

## 知识库 Pipeline

当前知识库流程：

```text
data/raw
  ↓
data/processed/documents.jsonl
  ↓
data/chunks/chunks.jsonl
  ↓
embedding
  ↓
data/index/travel.index
```

全量重建：

```bash
python scripts/rebuild_knowledge_base.py --mode full
```

增量更新：

```bash
python scripts/rebuild_knowledge_base.py --mode incremental
```

旧命令仍兼容：

```bash
python scripts/rebuild_index.py
```

## 审核过滤规则

如果资料中带有：

```json
{
  "review_status": "approved"
}
```

才会进入索引。

规则：

- `review_status="approved"`：进入索引
- `review_status="pending"`：跳过
- `review_status="rejected"`：跳过
- 没有 `review_status` 的历史人工资料：兼容导入

这可以避免 Excel/爬虫导入的未审核内容直接进入用户问答。

## 管理接口

```text
GET  /admin/knowledge/status
POST /admin/knowledge/rebuild
POST /admin/knowledge/update
```

注意：管理接口目前仅适合开发环境使用，生产环境需要补鉴权。

## 环境变量

常用配置：

```env
LLM_PROVIDER=qwen
LLM_API_KEY=your_key
LLM_BASE_URL=...
LLM_MODEL=...

EMBEDDING_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_key
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024

RERANK_ENABLE=true
RERANK_FALLBACK_TO_ORIGINAL_ORDER=true

WEATHER_PROVIDER=openmeteo
AMAP_API_KEY=your_key
FRONTEND_ORIGIN=http://localhost:5173
```

## 当前限制

- Rerank 是可选增强，失败时会 fallback 到原始 hybrid 检索结果。
- 天气、地图、LLM 等联网工具失败时不会让接口崩溃，会在 `tools_used` 和 `metadata` 中体现。
- 地图 API 未配置时，会基于知识库和规则生成 fallback 行程。
- 对话历史目前保存在浏览器 localStorage，不是后端多用户共享历史。
- 管理接口尚未做生产鉴权。
- 未引入 Redis、数据库、LangGraph。

## 验证命令

后端测试：

```bash
python -m pytest
```

后端语法检查：

```bash
python -m compileall app scripts
```

前端类型检查：

```bash
cd frontend
npx tsc -b
```

前端构建：

```bash
cd frontend
npm run build
```

## 版本说明

当前版本可以视为 V5.5：

- Agent 工具路由
- 可解释 Trace 返回
- 前端 Trace 展示
- RAG 审核过滤
- 知识库 Pipeline 增量更新

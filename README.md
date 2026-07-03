# TravelAgent 智能旅游 RAG Agent

TravelAgent 是一个基于 FastAPI + React + RAG + Agent 工具路由的 AI 旅行助手项目。它不是一个单纯的 ChatBot，而是一个围绕“本地旅游知识库 + 工具调用 + 低置信度拒答 + 来源解释”构建的 AI Travel Agent MVP。

项目支持旅游知识问答、城市推荐、天气查询、地图/行程规划、实时问题拒答、低置信度拒答、来源展示和伪流式输出。当前重点是保持结构清晰、接口稳定、可部署、可演示、方便面试讲解。

## 当前版本状态

当前项目已经完成到 V8 左右，具备线上可访问 MVP 到可演示生产级 AI Travel Agent 的核心链路。

- 已完成阿里云 ECS 部署。
- Nginx 托管 React 前端。
- FastAPI 后端通过 systemd 服务 `travelagent` 运行。
- Nginx 通过 `/api` 反向代理到后端。
- 支持非流式 `/api/chat`。
- 支持伪流式 `/api/chat/stream`。
- 天气工具支持 Open-Meteo fallback，并预留 QWeather provider。
- 地图工具支持规则行程 fallback，并预留 AMap provider。
- RAG 支持 sources、metadata、低置信度拒答和实时问题拒答。

线上访问示例：

```text
http://47.107.173.148
```

## 技术栈

后端：

- Python
- FastAPI
- Pydantic
- Uvicorn
- FAISS / BM25 / RAG
- systemd
- Nginx

前端：

- React
- TypeScript
- Vite
- Fetch / ReadableStream
- 组件化卡片展示

部署：

- 阿里云 ECS
- Nginx
- systemd
- GitHub 更新流程

第三方 API：

- DeepSeek 或兼容 OpenAI 的 LLM API
- QWeather 和风天气 API
- AMap 高德地图 Web 服务 API
- Open-Meteo fallback

## 系统架构

```text
浏览器
  ↓
React 前端
  ↓ /api/chat 或 /api/chat/stream
Nginx
  ↓
FastAPI Backend
  ↓
Agent Router
  ├── RAG Tool
  ├── Weather Tool
  └── Map Itinerary Tool
```

更细的后端链路：

```text
用户问题
  ↓
POST /chat 或 POST /chat/stream
  ↓
TravelAgent
  ↓
AgentRouter 分析 intent、city、category、days、places
  ↓
根据 intent 选择工具
  ├── rag_tool：本地知识库 RAG 问答
  ├── weather_tool：实时天气 / 明天天气 / 未来天气
  ├── map_itinerary_tool：规则行程 / 高德地理编码 / 高德路线规划
  └── refuse：实时开放时间、票价、无关问题等拒答
  ↓
统一返回 answer、intent、selected_tool、confidence、sources、cards
```

## RAG 与 Agent 工作流

1. FastAPI 接收用户问题。
2. AgentRouter 做 Query Analysis，识别城市、类别、意图、天数和地点。
3. AgentRouter 根据 intent 选择工具。
4. TravelAgent 调用对应工具。
5. 工具返回结构化结果。
6. TravelAgent 统一生成最终回答。
7. 前端展示回答、意图、工具、置信度、来源和卡片。

主要 intent：

- `knowledge_qa`：稳定知识问答。
- `food_recommendation`：美食或城市推荐。
- `itinerary_plan`：几天怎么玩、行程安排。
- `map_route_plan`：路线、景点顺序、从 A 到 B 怎么走。
- `transport_advice`：交通建议。
- `realtime_weather`：天气、下雨、温度、明天是否适合出门。
- `realtime_opening_hours`：实时开放时间、实时票价。
- `unsupported`：项目边界外的问题。

## 知识库说明

原始知识库：

```text
data/knowledge/travel_knowledge.json
```

构建产物：

```text
data/chunks.json
data/travel.index
```

每次更新知识库后需要重新构建索引：

```bash
python scripts/rebuild_index.py
```

每个 chunk 会保留 metadata：

```text
id、city、province、country、category、title、tags、suitable_for、updated_at、source_type
```

RAG 返回的 sources 会尽量包含：

```text
id、title、city、country、category、score、content、source_url
```

## 工具说明

### RAG Tool

RAG Tool 用于稳定旅游知识、美食推荐、景点推荐、交通建议和旅行建议。它基于本地知识库、BM25、FAISS 和置信度判断生成回答。

如果召回结果不足或置信度过低，系统会回答“根据当前资料，我无法确认”，避免让 LLM 编造。

### Weather Tool

Weather Tool 用于天气、下雨、温度、明天是否适合出门、未来几天天气等问题。

支持 provider：

- `openmeteo`：默认 fallback，无需 API Key。
- `qweather`：和风天气，需要 `QWEATHER_API_KEY`。
- `amap`：高德天气备用 provider，需要 `AMAP_API_KEY`。

无 Key 或外部 API 失败时，后端不会崩溃，会自动 fallback 或返回清晰提示。

### Map Itinerary Tool

Map Itinerary Tool 用于“几天怎么玩”“路线怎么安排”“从 A 到 B 怎么走”“景点顺序怎么排”等问题。

支持能力：

- 无 Key 时使用规则行程 fallback。
- 从知识库提取景点。
- 按景点类型和旅行节奏生成 Day 1 / Day 2 / Day 3。
- 配置 AMap Key 后可尝试地理编码和步行路线规划。
- 没有真实地图数据时，不编造精确距离、耗时或实时拥堵。

## 前端地图可视化

前端行程卡片支持高德地图 JS API 2.0 可视化展示。后端负责生成行程、景点经纬度和路线数据，前端负责 Marker、Polyline 和地图展示。

实现方式：

- 使用 `@amap/amap-jsapi-loader` 加载高德地图 JS API 2.0。
- 行程卡片读取后端 `cards` 中的 `itinerary` / `map_itinerary` 数据。
- 如果景点包含 `lng/lat` 或 `longitude/latitude`，前端会创建 Marker。
- 如果 route 中包含 `path`，前端会绘制 Polyline。
- 如果没有 route path，但至少有两个景点经纬度，会按景点顺序用简单折线连接。
- 如果没有经纬度或没有配置 JS API Key，自动降级为文字行程，不影响聊天回答。

前端环境变量：

```env
VITE_AMAP_JS_KEY=
VITE_AMAP_SECURITY_CODE=
```

本地开发可在 `frontend/.env.local` 中填写真实值，线上可在 `frontend/.env.production` 中填写真实值。不要把真实 Key 提交到 GitHub。

当前地图可视化主要用于国内城市，高德对国内场景更适合。后续可扩展前端路线规划插件、地图点击交互和地图主题样式。
## 接口文档

### GET /health

用于健康检查。

响应：

```json
{
  "status": "ok",
  "service": "travel-agent"
}
```

### POST /chat

请求：

```json
{
  "question": "我喜欢美食和慢节奏旅行，推荐去哪里？"
}
```

响应：

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

线上前端通过 Nginx 访问时，请求路径是：

```text
/api/chat
```

Nginx 会反向代理到后端 `/chat`。

### POST /chat/stream

请求：

```json
{
  "question": "成都三天怎么玩？"
}
```

响应格式：NDJSON。

```jsonl
{"type":"status","stage":"analyzing","message":"正在分析问题"}
{"type":"status","stage":"routing","message":"正在选择工具"}
{"type":"chunk","content":"根据你的需求，"}
{"type":"metadata","intent":"itinerary_plan","selected_tool":"map_itinerary_tool","confidence":0.78,"sources":[]}
{"type":"done"}
```

线上前端通过 Nginx 访问时，请求路径是：

```text
/api/chat/stream
```

## 关于伪流式

当前 `/chat/stream` 是伪流式。它的作用是验证前后端 ReadableStream、Nginx 转发、状态展示和 chunk 渲染链路。

当前实现方式是：后端先生成完整回答，再拆成多个 chunk 输出。后续真正 LLM 原生 streaming 会在 LLM 调用层实现，不属于当前阶段。

## 环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

`.env` 不允许提交到 GitHub。真实 Key 只放在本地和服务器的 `.env` 中。

推荐配置：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

WEATHER_PROVIDER=openmeteo
QWEATHER_API_KEY=

MAP_PROVIDER=rule
AMAP_API_KEY=
```

说明：

- 没有 `QWEATHER_API_KEY` 时使用 Open-Meteo fallback。
- 没有 `AMAP_API_KEY` 时使用规则行程 fallback。
- 不要把真实 API Key 写入 README、代码或提交记录。

## 本地运行方式

后端：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

本地前端地图配置示例，可写入 `frontend/.env.local`：

```env
VITE_AMAP_JS_KEY=你的高德Web端JSAPIKey
VITE_AMAP_SECURITY_CODE=你的高德安全密钥
```

访问：

```text
http://localhost:5173
```

## 服务器部署方式

当前阿里云部署方式：

- React 前端由 Nginx 托管。
- FastAPI 后端由 systemd 服务 `travelagent` 管理。
- Nginx 将 `/api` 反向代理到后端。

后端 systemd：

```bash
systemctl restart travelagent
systemctl status travelagent --no-pager
```

前端 build：

```bash
cd /www/TRAVELAGENT/frontend
npm install
npm run build
systemctl reload nginx
```

完整更新流程：

```bash
cd /www/TRAVELAGENT
git pull origin main
```

如果改后端：

```bash
systemctl restart travelagent
systemctl status travelagent --no-pager
```

如果改前端：

```bash
cd frontend
npm install
npm run build
systemctl reload nginx
```


如果需要开启前端地图可视化，线上前端构建前创建 `frontend/.env.production`：

```bash
cd /www/TRAVELAGENT/frontend
cat > .env.production <<'EOF'
VITE_API_BASE_URL=/api
VITE_AMAP_JS_KEY=你的高德Web端JSAPIKey
VITE_AMAP_SECURITY_CODE=你的高德安全密钥
EOF

npm install
npm run build
systemctl reload nginx
```

如果改知识库：

```bash
source .venv/bin/activate
python scripts/rebuild_index.py
systemctl restart travelagent
```

## 线上真实 API 联调说明

在服务器执行：

```bash
cd /www/TRAVELAGENT
vi .env
```

加入或修改：

```env
WEATHER_PROVIDER=qweather
QWEATHER_API_KEY=你的和风天气Key
MAP_PROVIDER=amap
AMAP_API_KEY=你的高德Web服务Key
```

重启后端：

```bash
systemctl restart travelagent
systemctl status travelagent --no-pager
```

测试天气：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"成都明天天气怎么样，适合去人民公园吗？"}'
```

测试地图：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"成都三天两晚怎么安排？"}'
```

测试公网反向代理：

```bash
curl -N http://47.107.173.148/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"成都明天天气怎么样，适合去人民公园吗？"}'
```

强调：不要把真实 Key 写进 README，不要提交 `.env`。

## Eval 测试

运行规则校验：

```bash
python scripts/eval_rag.py
```

Eval 覆盖：

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

## 当前限制

- 流式还是伪流式。
- 天气和地图正式 provider 依赖 API Key。
- 海外地图规划暂未接 Google Maps。
- Reranker 可后续增强。
- 前端地图可视化还可以继续增强。
- 当前地图可视化只消费后端返回的经纬度和路线数据，不在前端主动做路线规划搜索。
- Eval 目前是规则校验，不是完整自动评分系统。

## 后续规划

- 接入 LLM 原生 streaming。
- 细化 Agent 工具执行状态。
- 接入 QWeather 生活指数和灾害预警。
- 接入 AMap 路线规划更多交通方式。
- 增加 Reranker。
- 扩展前端路线规划插件、地图点击交互和地图主题样式。
- 增加 CI/CD。




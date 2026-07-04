from __future__ import annotations

from uuid import uuid4

from app.agents.router import AgentRouter
from app.rag.pipeline import RAGPipeline, UNCERTAIN_ANSWER, create_pipeline
from app.schemas import (
    AgentResult,
    AgentState,
    FoodRecommendation,
    ItineraryDayPlan,
    ItineraryStop,
    ResponseCard,
    RetrievedChunk,
    TaskPlanStep,
    ToolUsage,
    TravelTip,
)
from app.tools.map_itinerary_tool import MapItineraryTool
from app.tools.rag_tool import RagTool, source_dicts_to_refs
from app.tools.weather_tool import WeatherTool


class TravelAgent:
    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.router = AgentRouter(pipeline.retriever)
        self.rag_tool = RagTool(pipeline)
        self.weather_tool = WeatherTool()
        self.map_itinerary_tool = MapItineraryTool(pipeline)

    def run(self, question: str, session_id: str | None = None) -> AgentResult:
        session_id = session_id or str(uuid4())
        analysis = self.router.analyze_query(question)
        intent = analysis["intent"]
        selected_tool = self.router.route_task(intent)
        state = AgentState(
            question=question.strip(),
            session_id=session_id,
            intent=intent,
            selected_tool=selected_tool,
            city=analysis.get("city"),
            category=analysis.get("category"),
            days=analysis.get("days"),
            places=analysis.get("places") or [],
        )
        task_plan = self._task_plan_for(analysis, selected_tool)

        if selected_tool == "multi_tool":
            return self._answer_from_travel_decision(state, task_plan)

        state.tool_result = self._run_selected_tool(state)
        result = self.generate_final_answer(state)
        return self._with_trace(result, state, task_plan)

    def _run_selected_tool(self, state: AgentState) -> dict:
        try:
            if state.selected_tool == "rag_tool":
                return self.rag_tool.run(question=state.question, city=state.city, category=state.category)
            if state.selected_tool == "weather_tool":
                return self.weather_tool.run(city=state.city, question=state.question)
            if state.selected_tool == "map_itinerary_tool":
                return self.map_itinerary_tool.run(city=state.city, days=state.days, places=state.places, question=state.question)
            return self._refuse_tool_result(state.intent)
        except Exception as exc:
            return {
                "answer": f"{UNCERTAIN_ANSWER}\n工具调用失败：{exc}",
                "message": f"工具调用失败：{exc}",
                "refused": True,
                "error": str(exc),
            }

    def generate_final_answer(self, state: AgentState) -> AgentResult:
        if state.selected_tool == "rag_tool":
            return self._answer_from_rag(state)
        if state.selected_tool == "weather_tool":
            return self._answer_from_weather(state)
        if state.selected_tool == "map_itinerary_tool":
            return self._answer_from_map(state)
        return AgentResult(
            answer=state.tool_result.get("answer", UNCERTAIN_ANSWER),
            session_id=state.session_id,
            intent=self._public_intent(state.intent),
            selected_tool=state.selected_tool,
            city=state.city,
            tips=self._tips_for_city(state.city),
            confidence=0.0,
            sources=[],
            refused=True,
            debug={"refused": True},
        )

    def _answer_from_rag(self, state: AgentState) -> AgentResult:
        result = state.tool_result
        refused = bool(result.get("refused", True))
        return AgentResult(
            answer=result.get("answer", UNCERTAIN_ANSWER),
            session_id=state.session_id,
            intent=self._public_intent(state.intent),
            selected_tool=state.selected_tool,
            city=state.city,
            food_recommendations=self._food_recommendations_for_city(state.city),
            tips=self._tips_for_city(state.city),
            confidence=float(result.get("confidence", 0.0)),
            sources=source_dicts_to_refs(result.get("sources", [])),
            cards=[],
            refused=refused,
            debug={"refused": refused},
        )

    def _answer_from_weather(self, state: AgentState) -> AgentResult:
        result = state.tool_result
        card = ResponseCard(type="weather", title="天气工具状态", data=result)
        if not result.get("available"):
            message = result.get("message", "实时天气暂时无法确认。")
            if "实时天气暂时无法确认" not in message and "无法查询实时天气" not in message:
                message = f"实时天气暂时无法确认。{message}"
            return AgentResult(
                answer=message,
                session_id=state.session_id,
                intent=self._public_intent(state.intent),
                selected_tool=state.selected_tool,
                city=state.city or result.get("city"),
                tips=[TravelTip(title="天气提醒", content=message)],
                confidence=0.0,
                sources=[],
                cards=[card],
                refused=True,
                debug={"refused": True, "tool_available": False},
            )

        answer = result.get("summary") or f"{result.get('city', state.city or '')}实时天气已查询成功。"
        answer += "\n建议出行前再次确认天气变化，避免把实时结果当成长期旅行建议。"
        return AgentResult(
            answer=answer,
            session_id=state.session_id,
            intent=self._public_intent(state.intent),
            selected_tool=state.selected_tool,
            city=state.city or result.get("city"),
            tips=[TravelTip(title="出行天气", content=result.get("travel_advice", "出发前建议再次确认天气变化。"))],
            confidence=0.85,
            sources=[],
            cards=[ResponseCard(type="weather", title=f"{result.get('city', state.city or '')}天气", data=result)],
            refused=False,
            debug={"refused": False, "tool_available": True},
        )

    def _answer_from_map(self, state: AgentState) -> AgentResult:
        result = state.tool_result
        itinerary = result.get("itinerary", [])
        card = ResponseCard(type="itinerary", title="行程工具状态", data=result)
        if not itinerary:
            return AgentResult(
                answer=result.get("message", UNCERTAIN_ANSWER),
                session_id=state.session_id,
                intent=self._public_intent(state.intent),
                selected_tool=state.selected_tool,
                city=state.city or result.get("city"),
                tips=self._tips_for_city(state.city or result.get("city")),
                confidence=0.0,
                sources=[],
                cards=[card],
                refused=True,
                debug={"refused": True},
            )

        lines = [result.get("message", "已生成轻量行程建议。")]
        for day in itinerary:
            places = "、".join(day.get("places", []))
            lines.append(f"第 {day.get('day')} 天：{day.get('theme')}。建议安排：{places}。{day.get('note')}")
        lines.append("以上不包含实时拥堵、精确路程或精确耗时；出发前建议再用地图 App 核验。")

        return AgentResult(
            answer="\n".join(lines),
            session_id=state.session_id,
            intent=self._public_intent(state.intent),
            selected_tool=state.selected_tool,
            city=state.city or result.get("city"),
            itinerary=self._structured_itinerary(result.get("days", [])),
            food_recommendations=self._food_recommendations_for_city(state.city or result.get("city")),
            tips=self._tips_for_city(state.city or result.get("city")),
            confidence=0.62 if result.get("fallback") else 0.78,
            sources=[],
            cards=[ResponseCard(type="itinerary", title=f"{state.city or result.get('city', '')}行程建议", data=result)],
            refused=False,
            debug={"refused": False, "fallback": bool(result.get("fallback"))},
        )

    def _answer_from_travel_decision(self, state: AgentState, task_plan: list[TaskPlanStep]) -> AgentResult:
        static_question = self._static_decision_question(state)
        rag_result = self.rag_tool.run(question=static_question, city=state.city, category="attractions")
        weather_result = self.weather_tool.run(city=state.city, question=state.question)

        tools_used = [
            self._tool_usage("rag", rag_result),
            self._tool_usage("weather", weather_result),
        ]
        retrieved_chunks = self._retrieved_chunks_from_tool_result(rag_result)
        sources = source_dicts_to_refs(rag_result.get("sources", []))
        cards = [ResponseCard(type="weather", title=f"{state.city or weather_result.get('city', '')}天气", data=weather_result)]
        answer = self._compose_decision_answer(state, rag_result, weather_result, retrieved_chunks)
        fallback_used = any(tool.status in {"failed", "fallback"} for tool in tools_used)
        rag_meta = rag_result.get("metadata", {}) or {}

        return AgentResult(
            answer=answer,
            session_id=state.session_id,
            intent="travel_decision",
            selected_tool="multi_tool",
            city=state.city or weather_result.get("city"),
            food_recommendations=self._food_recommendations_for_city(state.city),
            tips=self._tips_for_city(state.city),
            confidence=0.72 if not fallback_used else 0.46,
            sources=sources,
            cards=cards,
            task_plan=task_plan,
            tools_used=tools_used,
            retrieved_chunks=retrieved_chunks,
            metadata={
                "rerank_enabled": bool(rag_meta.get("rerank_enabled")),
                "rerank_used": bool(rag_meta.get("rerank_used")),
                "fallback_used": fallback_used or bool(rag_meta.get("fallback_used")) or bool(weather_result.get("fallback")),
                "query_analysis": {
                    "intent": state.intent,
                    "city": state.city,
                    "places": state.places,
                },
            },
            refused=False,
            debug={"refused": False, "composite": True},
        )

    def _compose_decision_answer(
        self,
        state: AgentState,
        rag_result: dict,
        weather_result: dict,
        chunks: list[RetrievedChunk],
    ) -> str:
        city = state.city or weather_result.get("city") or "目的地"
        place = state.places[0] if state.places else "这个地点"
        lines = [f"我会把天气和本地知识一起看：{city}{place}的出行建议如下。"]

        if weather_result.get("available"):
            lines.append(f"天气：{weather_result.get('summary') or weather_result.get('travel_advice')}")
            rain = weather_result.get("rain_probability")
            condition = str(weather_result.get("condition") or "")
            if isinstance(rain, (int, float)) and rain >= 60:
                lines.append("判断：降水概率偏高，更适合降低户外停留强度，准备室内备选或改到雨小的时段。")
            elif "雨" in condition:
                lines.append("判断：天气可能影响户外体验，建议带伞，并把茶馆、博物馆这类室内点作为备选。")
            else:
                lines.append("判断：天气没有明显阻碍，整体可以安排，但出发前仍建议再确认实时预报。")
        else:
            lines.append(f"天气：{weather_result.get('message', '实时天气暂时无法确认。')}")

        if chunks:
            preview = chunks[0].content_preview or ""
            lines.append(f"本地知识：{preview}")
        elif rag_result.get("answer"):
            lines.append(f"本地知识：{self._short_text(str(rag_result.get('answer')), place)}")
        else:
            lines.append("本地知识：当前没有召回足够可靠的地点资料。")

        lines.append("建议：如果你的目标是慢节奏体验，可以把停留时间放宽，避免把行程排得太满。")
        return "\n".join(line for line in lines if line)

    def _static_decision_question(self, state: AgentState) -> str:
        place_text = " ".join(state.places) if state.places else ""
        city_text = state.city or ""
        return f"{city_text} {place_text} 景点 体验 适合人群 旅行建议".strip()

    def _with_trace(self, result: AgentResult, state: AgentState, task_plan: list[TaskPlanStep]) -> AgentResult:
        result.task_plan = task_plan
        result.tools_used = [self._tool_usage(self._trace_tool_name(state.selected_tool), state.tool_result)]
        result.retrieved_chunks = self._retrieved_chunks_from_tool_result(state.tool_result)
        trace_metadata = self._trace_metadata(state)
        result.metadata = {**(result.metadata or {}), **trace_metadata}
        return result

    def _task_plan_for(self, analysis: dict, selected_tool: str) -> list[TaskPlanStep]:
        intent = analysis.get("intent")
        if selected_tool == "multi_tool":
            return [
                TaskPlanStep(step="retrieve_knowledge", tool="rag", reason="需要查询本地旅游知识库判断地点体验和适合人群"),
                TaskPlanStep(step="query_weather", tool="weather", reason="问题包含明天、天气或是否适合出行等实时因素"),
                TaskPlanStep(step="synthesize_decision", tool="agent", reason="融合静态知识和天气结果给出旅行决策建议"),
            ]
        if selected_tool == "rag_tool":
            return [TaskPlanStep(step="retrieve_knowledge", tool="rag", reason="需要查询本地旅游知识库")]
        if selected_tool == "weather_tool":
            return [TaskPlanStep(step="query_weather", tool="weather", reason="需要查询天气信息")]
        if selected_tool == "map_itinerary_tool":
            step = "query_route" if intent == "map_route_plan" else "plan_itinerary"
            return [TaskPlanStep(step=step, tool="map", reason="需要根据地点或天数生成路线/行程建议")]
        return [TaskPlanStep(step="fallback", tool="agent", reason="问题超出当前工具能力边界")]

    def _tool_usage(self, tool: str, result: dict) -> ToolUsage:
        if tool == "rag":
            count = len(result.get("retrieved_chunks", []) or result.get("sources", []) or [])
            metadata = result.get("metadata", {}) or {}
            status = "failed" if metadata.get("error") else "fallback" if result.get("refused") else "success"
            summary = f"召回 {count} 条知识片段" if count else result.get("answer", "未召回知识片段")
            return ToolUsage(tool="rag", status=status, summary=self._preview(summary, 80))

        if tool == "weather":
            status = "success" if result.get("available") else "failed"
            if result.get("fallback"):
                status = "fallback"
            summary = result.get("summary") or result.get("message") or "天气工具已返回"
            return ToolUsage(tool="weather", status=status, summary=self._preview(summary, 80))

        if tool == "map":
            has_itinerary = bool(result.get("itinerary"))
            status = "success" if result.get("available") else "fallback" if has_itinerary or result.get("fallback") else "failed"
            summary = result.get("message") or ("已生成路线/行程建议" if has_itinerary else "地图工具未返回结果")
            return ToolUsage(tool="map", status=status, summary=self._preview(summary, 80))

        return ToolUsage(tool=tool or "agent", status="fallback", summary=self._preview(result.get("answer") or result.get("message") or "使用兜底回答", 80))

    def _trace_metadata(self, state: AgentState) -> dict:
        result = state.tool_result or {}
        rag_meta = result.get("metadata", {}) or {}
        tool_failed = (
            (state.selected_tool == "weather_tool" and result.get("available") is False)
            or (state.selected_tool == "map_itinerary_tool" and result.get("available") is False and not result.get("itinerary"))
        )
        fallback_used = bool(result.get("fallback") or result.get("refused") or rag_meta.get("fallback_used") or result.get("error") or tool_failed)
        return {
            "rerank_enabled": bool(rag_meta.get("rerank_enabled")),
            "rerank_used": bool(rag_meta.get("rerank_used")),
            "fallback_used": fallback_used,
            "query_analysis": {
                "intent": state.intent,
                "city": state.city,
                "category": state.category,
                "days": state.days,
                "places": state.places,
            },
        }

    def _retrieved_chunks_from_tool_result(self, result: dict) -> list[RetrievedChunk]:
        chunks = []
        for item in result.get("retrieved_chunks", []) or []:
            try:
                chunks.append(RetrievedChunk(**item))
            except TypeError:
                continue
        return chunks

    def _trace_tool_name(self, selected_tool: str) -> str:
        if "rag" in selected_tool:
            return "rag"
        if "weather" in selected_tool:
            return "weather"
        if "map" in selected_tool or "itinerary" in selected_tool:
            return "map"
        return "agent"

    def _refuse_tool_result(self, intent: str) -> dict:
        if intent == "realtime_opening_hours":
            return {
                "answer": f"{UNCERTAIN_ANSWER}\n这个问题涉及实时开放时间或票价，当前系统未接入对应官方实时工具，不能用本地知识库编造。",
                "refused": True,
            }
        if intent == "unsupported":
            return {
                "answer": f"{UNCERTAIN_ANSWER}\n当前系统暂不支持酒店价格、航班价格、用户账号或其他超出旅游知识库的问题。",
                "refused": True,
            }
        return {"answer": UNCERTAIN_ANSWER, "refused": True}

    def _public_intent(self, intent: str) -> str:
        if intent == "itinerary_plan":
            return "itinerary_plan"
        if intent == "map_route_plan":
            return "map_query"
        if intent in {"food_recommendation", "transport_advice", "knowledge_qa"}:
            return "knowledge_qa"
        if intent == "realtime_weather":
            return "weather_query"
        if intent == "travel_decision":
            return "travel_decision"
        return "fallback"

    def _preview(self, text: str, limit: int) -> str:
        clean = " ".join(str(text).split())
        return clean[:limit].rstrip() + ("..." if len(clean) > limit else "")

    def _knowledge_items(self, city: str | None, category: str) -> list[dict]:
        if not city:
            return []
        return [
            item
            for item in self.pipeline.retriever.store.chunks
            if isinstance(item, dict) and item.get("city") == city and item.get("category") == category
        ]

    def _food_recommendations_for_city(self, city: str | None) -> list[FoodRecommendation]:
        items = self._knowledge_items(city, "food")
        recommendations: list[FoodRecommendation] = []
        for item in items:
            content = str(item.get("content", ""))
            tags = [str(tag) for tag in item.get("tags", []) if str(tag).strip()]
            names = tags[:4] or [str(item.get("title") or "当地特色美食")]
            for name in names:
                recommendations.append(
                    FoodRecommendation(
                        name=name,
                        reason=self._short_text(content, name),
                        area=self._detect_food_area(content),
                        tags=tags[:3],
                    )
                )
                if len(recommendations) >= 4:
                    return recommendations
        return recommendations

    def _tips_for_city(self, city: str | None) -> list[TravelTip]:
        items = self._knowledge_items(city, "tips")
        if not items:
            return [
                TravelTip(title="行前确认", content="出发前再次确认天气、交通和景区预约信息。"),
                TravelTip(title="节奏建议", content="行程不要排得过满，给用餐、休息和临时调整留出空间。"),
            ]

        content = str(items[0].get("content", ""))
        sentences = [part.strip() for part in content.replace("；", "。").split("。") if part.strip()]
        titles = ["最佳季节", "实用提醒", "避坑建议"]
        tips = []
        for index, sentence in enumerate(sentences[:3]):
            tips.append(TravelTip(title=titles[min(index, len(titles) - 1)], content=sentence + "。"))
        return tips

    def _structured_itinerary(self, days: list[dict]) -> list[ItineraryDayPlan]:
        result: list[ItineraryDayPlan] = []
        for day in days or []:
            spots = []
            for spot in day.get("spots", []):
                if isinstance(spot, dict):
                    spots.append(
                        ItineraryStop(
                            name=str(spot.get("name") or spot.get("title") or "未命名地点"),
                            type=spot.get("type"),
                            lat=spot.get("lat"),
                            lng=spot.get("lng"),
                        )
                    )
                elif spot:
                    spots.append(ItineraryStop(name=str(spot)))
            result.append(
                ItineraryDayPlan(
                    day=int(day.get("day") or len(result) + 1),
                    theme=day.get("theme"),
                    pace=day.get("pace"),
                    spots=spots,
                    routes=day.get("routes", []),
                    notes=day.get("notes"),
                )
            )
        return result

    def _short_text(self, content: str, name: str) -> str:
        if not content:
            return f"{name} 是当地值得尝试的特色体验。"
        sentences = [part.strip() for part in content.split("。") if part.strip()]
        for sentence in sentences:
            if name in sentence:
                return sentence[:80] + ("..." if len(sentence) > 80 else "")
        if sentences:
            return sentences[0][:80] + ("..." if len(sentences[0]) > 80 else "")
        return f"{name} 是当地值得尝试的特色体验。"

    def _detect_food_area(self, content: str) -> str | None:
        for marker in ["街", "路", "巷", "商圈", "市场"]:
            index = content.find(marker)
            if index > 0:
                start = max(0, index - 8)
                return content[start : index + len(marker)]
        return None


def create_travel_agent() -> TravelAgent:
    return TravelAgent(create_pipeline())

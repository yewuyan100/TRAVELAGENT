from __future__ import annotations

from uuid import uuid4

from app.agents.router import AgentRouter
from app.rag.pipeline import RAGPipeline, UNCERTAIN_ANSWER, create_pipeline
from app.schemas import AgentResult, AgentState, ResponseCard, SourceRef
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

        if selected_tool == "rag_tool":
            state.tool_result = self.rag_tool.run(question=state.question, city=state.city, category=state.category)
        elif selected_tool == "weather_tool":
            state.tool_result = self.weather_tool.run(city=state.city, question=state.question)
        elif selected_tool == "map_itinerary_tool":
            state.tool_result = self.map_itinerary_tool.run(city=state.city, days=state.days, places=state.places, question=state.question)
        else:
            state.tool_result = self._refuse_tool_result(intent)

        return self.generate_final_answer(state)

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
            intent=state.intent,
            selected_tool=state.selected_tool,
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
            intent=state.intent,
            selected_tool=state.selected_tool,
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
                intent=state.intent,
                selected_tool=state.selected_tool,
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
            intent=state.intent,
            selected_tool=state.selected_tool,
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
                intent=state.intent,
                selected_tool=state.selected_tool,
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
            intent=state.intent,
            selected_tool=state.selected_tool,
            confidence=0.62 if result.get("fallback") else 0.78,
            sources=[],
            cards=[ResponseCard(type="itinerary", title=f"{state.city or result.get('city', '')}行程建议", data=result)],
            refused=False,
            debug={"refused": False, "fallback": bool(result.get("fallback"))},
        )

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


def create_travel_agent() -> TravelAgent:
    return TravelAgent(create_pipeline())

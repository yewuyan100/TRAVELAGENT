from __future__ import annotations

import re

from app.rag.retriever import Retriever


FOOD_KEYWORDS = ["美食", "吃", "小吃", "餐厅", "火锅", "菜", "好吃"]
WEATHER_KEYWORDS = ["天气", "下雨", "降雨", "气温", "温度", "冷", "热", "明天", "后天", "带伞", "雨具", "适合出门", "适不适合出门"]
DECISION_KEYWORDS = ["适合去", "适不适合去", "适合吗", "适不适合", "要不要去", "能不能去", "能去", "值得去", "推荐去"]
OPENING_HOURS_KEYWORDS = ["几点开门", "几点关门", "营业时间", "开放时间", "闭园", "开园", "票价", "门票"]
MAP_ROUTE_KEYWORDS = ["几天", "行程", "路线", "自由行", "规划", "几天怎么玩", "怎么玩", "三日游", "两日游", "一日游", "顺序", "排序", "景点排序", "怎么安排", "Day 1", "Day1", "第1天", "从", "到", "怎么走"]
TRANSPORT_KEYWORDS = ["交通", "地铁", "公交", "打车", "自驾", "机场", "火车站", "高铁"]
UNSUPPORTED_KEYWORDS = [
    "酒店价格",
    "航班价格",
    "机票价格",
    "实时房价",
    "用户登录",
    "注册",
    "股票",
    "量化交易",
    "交易策略",
    "基金",
    "证券",
]
CATEGORY_BY_INTENT = {
    "food_recommendation": "food",
    "transport_advice": "transport",
}


def detect_days(question: str) -> int | None:
    patterns = [
        (r"(\d+)\s*天", lambda value: int(value)),
        (r"([一二两三四五六七])日游", _cn_day_to_int),
        (r"([一二两三四五六七])天", _cn_day_to_int),
    ]
    for pattern, converter in patterns:
        match = re.search(pattern, question)
        if match:
            return max(1, min(converter(match.group(1)), 7))
    return None


def _cn_day_to_int(value: str) -> int:
    return {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}.get(value, 1)


class AgentRouter:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.city_names = sorted(set(retriever.available_cities) | {"东京", "大阪", "京都", "首尔", "新加坡", "曼谷", "巴黎", "伦敦"}, key=len, reverse=True)

    def analyze_query(self, question: str) -> dict:
        rag_analysis = self.retriever.analyze_query(question)
        city = rag_analysis.city or self._detect_city(question) or self._infer_city_from_known_place(question)
        intent = self._detect_intent(question, rag_analysis.needs_realtime)
        return {
            "question": question,
            "city": city,
            "category": CATEGORY_BY_INTENT.get(intent, self._category_from_analysis(rag_analysis.categories)),
            "intent": intent,
            "days": detect_days(question),
            "places": self._detect_places(question, city),
            "rag_analysis": rag_analysis,
        }

    def route_task(self, intent: str) -> str:
        if intent in {"knowledge_qa", "food_recommendation", "transport_advice"}:
            return "rag_tool"
        if intent == "realtime_weather":
            return "weather_tool"
        if intent in {"itinerary_plan", "map_route_plan"}:
            return "map_itinerary_tool"
        if intent == "travel_decision":
            return "multi_tool"
        return "refuse"

    def _detect_intent(self, question: str, needs_realtime: bool) -> str:
        if any(keyword in question for keyword in UNSUPPORTED_KEYWORDS):
            return "unsupported"
        if any(keyword in question for keyword in OPENING_HOURS_KEYWORDS):
            return "realtime_opening_hours"
        has_weather_signal = any(keyword in question for keyword in WEATHER_KEYWORDS)
        has_decision_signal = any(keyword in question for keyword in DECISION_KEYWORDS)
        if has_weather_signal and has_decision_signal:
            return "travel_decision"
        if has_weather_signal:
            return "realtime_weather"
        if any(keyword in question for keyword in MAP_ROUTE_KEYWORDS):
            if "从" in question and ("到" in question or "怎么走" in question):
                return "map_route_plan"
            return "itinerary_plan"
        if any(keyword in question for keyword in TRANSPORT_KEYWORDS):
            return "transport_advice"
        if any(keyword in question for keyword in FOOD_KEYWORDS):
            return "food_recommendation"
        if needs_realtime:
            return "unsupported"
        return "knowledge_qa"

    def _detect_city(self, question: str) -> str | None:
        for city in self.city_names:
            if city in question:
                return city
        return None

    def _infer_city_from_known_place(self, question: str) -> str | None:
        for item in self.retriever.store.chunks:
            if not isinstance(item, dict) or not item.get("city"):
                continue
            title = str(item.get("title", ""))
            content = str(item.get("content", ""))
            tags = [str(tag) for tag in item.get("tags", []) or []]
            candidates = [title, *tags]
            candidates.extend(
                re.findall(r"[\u4e00-\u9fffA-Za-z0-9·]{2,12}?(?:公园|博物馆|寺|街|路|巷|湖|山|塔|城|基地|广场|景区|古镇|市场|商圈|迪士尼)", content)
            )
            if any(candidate and candidate in question for candidate in candidates):
                return str(item.get("city"))
        return None

    def _detect_places(self, question: str, city: str | None) -> list[str]:
        places = []
        for item in self.retriever.store.chunks:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", ""))
            item_city = str(item.get("city", ""))
            if item_city and item_city in question and item_city != city:
                places.append(item_city)
            if title and title in question:
                places.append(title)

            content = str(item.get("content", ""))
            for match in re.findall(r"[\u4e00-\u9fffA-Za-z0-9·]{2,12}?(?:公园|博物馆|寺|街|路|巷|湖|山|塔|城|基地|广场|景区|古镇|市场|商圈|迪士尼)", content):
                if match in question:
                    places.append(match)

        for city_name in self.city_names:
            if city_name in question and city_name != city:
                places.append(city_name)

        seen = set()
        unique = []
        for place in places:
            if place not in seen:
                unique.append(place)
                seen.add(place)
        return unique[:8]

    def _category_from_analysis(self, categories: list[str]) -> str | None:
        if not categories:
            return None
        return categories[0]

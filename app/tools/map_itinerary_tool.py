from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import settings
from app.rag.pipeline import RAGPipeline


class AMapAdapter:
    def __init__(self, api_key: str | None = settings.map_api_key, base_url: str = settings.map_base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def geocode(self, city: str, place: str) -> dict[str, Any]:
        if not self.api_key:
            return {"available": False, "message": "地图工具暂未配置。"}

        url = f"{self.base_url}/v3/geocode/geo"
        params = {"key": self.api_key, "city": city, "address": place}
        try:
            response = httpx.get(url, params=params, timeout=8.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"available": False, "message": f"地图服务暂时无法确认：{exc}", "raw": {}}

        return {"available": True, "raw": data}


class MapItineraryTool:
    name = "map_itinerary_tool"

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.map_adapter = AMapAdapter()

    def run(self, city: str | None, days: int | None = None, places: list[str] | None = None) -> dict[str, Any]:
        city = city or ""
        days = max(1, min(days or 1, 7))
        places = [place for place in (places or []) if place]

        if not places and city:
            places = self._places_from_knowledge(city)

        if not city:
            return {
                "available": False,
                "fallback": True,
                "city": city,
                "days": days,
                "itinerary": [],
                "message": "缺少城市信息，无法生成可靠路线建议。",
            }

        if not places:
            return {
                "available": False,
                "fallback": True,
                "city": city,
                "days": days,
                "itinerary": [],
                "message": "当前知识库没有足够景点信息，无法生成可靠路线建议。",
            }

        itinerary = self._build_rule_based_itinerary(city=city, days=days, places=places)
        message = "地图工具暂未配置，已基于知识库和规则生成行程建议。"
        available = False
        fallback = True

        if self.map_adapter.configured:
            geocoded = [self.map_adapter.geocode(city, place) for place in places[:8]]
            if any(item.get("available") for item in geocoded):
                available = True
                fallback = False
                message = "已调用地图服务做基础地点查询；路线顺序仍采用轻量规则建议，不包含实时拥堵或精确耗时。"
            else:
                message = "地图服务暂时无法确认，已基于知识库和规则生成行程建议。"

        return {
            "available": available,
            "fallback": fallback,
            "city": city,
            "days": days,
            "itinerary": itinerary,
            "message": message,
        }

    def _places_from_knowledge(self, city: str) -> list[str]:
        places = []
        for item in self.pipeline.retriever.store.chunks:
            if not isinstance(item, dict):
                continue
            if item.get("city") != city:
                continue
            if item.get("category") not in {"attractions", "itinerary", "transport", "tips"}:
                continue
            content = str(item.get("content", ""))
            places.extend(self._extract_places_from_text(content))

        seen = set()
        unique_places = []
        for place in places:
            if place not in seen and len(place) >= 2:
                unique_places.append(place)
                seen.add(place)
        return unique_places[:12]

    def _extract_places_from_text(self, text: str) -> list[str]:
        candidates = []
        for marker in ["包括：", "推荐：", "景点：", "路线："]:
            if marker in text:
                segment = text.split(marker, 1)[1].split("。", 1)[0]
                candidates.extend(re.split(r"、|，|,|/|和", segment))
        for match in re.findall(r"[\u4e00-\u9fffA-Za-z0-9·]{2,12}(?:公园|博物馆|寺|街|巷|湖|山|塔|城|基地|广场|景区|古镇|市场|商圈)", text):
            candidates.append(match)
        return [item.strip() for item in candidates if item.strip()]

    def _build_rule_based_itinerary(self, city: str, days: int, places: list[str]) -> list[dict[str, Any]]:
        groups = [[] for _ in range(days)]
        for index, place in enumerate(places):
            groups[index % days].append(place)

        itinerary = []
        for index, group in enumerate(groups, start=1):
            if not group:
                group = places[: min(2, len(places))]
            theme = self._theme_for_day(index)
            itinerary.append({
                "day": index,
                "theme": theme,
                "places": group[:4],
                "note": "根据知识库景点、区域相近和旅行节奏做轻量排序；不包含实时拥堵、精确路程或精确耗时。",
            })
        return itinerary

    def _theme_for_day(self, day: int) -> str:
        themes = ["城市经典景点", "文化街区与美食", "轻松休闲与补充游览", "深度体验", "弹性安排"]
        return themes[min(day - 1, len(themes) - 1)]

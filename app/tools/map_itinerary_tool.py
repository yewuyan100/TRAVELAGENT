from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import settings
from app.rag.pipeline import RAGPipeline


DOMESTIC_CITIES = {
    "成都", "重庆", "北京", "上海", "杭州", "西安", "南京", "苏州", "广州", "深圳", "厦门", "青岛", "长沙", "武汉", "昆明", "三亚"
}

SPOT_TYPE_KEYWORDS = {
    "亲子": ["熊猫", "乐园", "动物", "海洋", "科技馆", "迪士尼"],
    "自然": ["湖", "山", "公园", "湿地", "海", "岛", "森林", "景区"],
    "美食": ["小吃", "美食", "餐厅", "夜市", "市场", "火锅", "茶馆"],
    "文化": ["博物馆", "寺", "祠", "古镇", "古城", "遗址", "塔", "故宫", "天安门", "天坛", "颐和园", "长城", "恭王府", "纪念堂", "历史", "文化"],
    "城市漫游": ["街", "巷", "广场", "商圈", "步行街", "里", "坊", "胡同"],
}

PACE_KEYWORDS = {
    "轻松": ["轻松", "慢", "休闲", "不累", "亲子", "老人"],
    "紧凑": ["紧凑", "多玩", "打卡", "效率", "赶"],
}


class AmapMapProvider:
    name = "amap"

    def __init__(self, api_key: str | None = settings.amap_api_key, base_url: str = settings.map_base_url):
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

        if str(data.get("status")) != "1" or not data.get("geocodes"):
            return {"available": False, "message": data.get("info", "地理编码无结果"), "raw": data}

        geocode = data["geocodes"][0]
        location = geocode.get("location", "")
        try:
            lng, lat = [float(value) for value in location.split(",", 1)]
        except ValueError:
            lng, lat = None, None
        return {"available": True, "name": place, "lat": lat, "lng": lng, "raw": data}

    def walking_route(self, origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            return {"available": False, "message": "地图工具暂未配置。"}
        if origin.get("lng") is None or destination.get("lng") is None:
            return {"available": False, "message": "缺少经纬度，无法规划路线。"}

        params = {
            "key": self.api_key,
            "origin": f"{origin['lng']},{origin['lat']}",
            "destination": f"{destination['lng']},{destination['lat']}",
        }
        try:
            response = httpx.get(f"{self.base_url}/v3/direction/walking", params=params, timeout=8.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"available": False, "message": f"路线规划暂时无法确认：{exc}", "raw": {}}

        route = (data.get("route") or {}).get("paths", [{}])[0]
        if str(data.get("status")) != "1" or not route:
            return {"available": False, "message": data.get("info", "路线规划无结果"), "raw": data}

        distance = _to_int(route.get("distance"))
        duration = _to_int(route.get("duration"))
        return {
            "available": True,
            "from": origin.get("name"),
            "to": destination.get("name"),
            "distance_m": distance,
            "duration_min": round(duration / 60) if duration is not None else None,
            "mode": "walking",
            "raw": data,
        }


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class MapItineraryTool:
    name = "map_itinerary_tool"

    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        self.map_provider = AmapMapProvider()
        self.provider_name = settings.map_provider.lower().replace("-", "_")

    def run(self, city: str | None, days: int | None = None, places: list[str] | None = None, question: str = "") -> dict[str, Any]:
        city = city or ""
        days = max(1, min(days or self._detect_days(question) or 1, 7))
        pace = self._detect_pace(question)
        places = [place for place in (places or []) if place]

        if not city:
            return self._empty_result(city, days, "缺少城市信息，无法生成可靠路线建议。")

        if not places:
            places = [spot["name"] for spot in self._spots_from_knowledge(city)]

        if not places:
            return self._empty_result(city, days, "当前知识库没有足够景点信息，无法生成可靠路线建议。")

        spots = self._normalize_spots(city, places)
        grouped_days = self._build_rule_days(city=city, days=days, spots=spots, pace=pace)
        provider = "rules"
        available = False
        fallback = True
        message = "地图工具暂未配置，已基于知识库和规则生成行程建议。"

        if city not in DOMESTIC_CITIES:
            message = "海外城市暂时使用规则行程 fallback；海外路线规划后续可接入 Google Maps。"
        elif self.provider_name == "amap" and self.map_provider.configured:
            provider = "amap"
            enriched = self._enrich_with_amap(city, grouped_days)
            if enriched["available"]:
                grouped_days = enriched["days"]
                available = True
                fallback = False
                message = "已调用高德地图进行地理编码和基础步行路线规划；不包含实时拥堵。"
            else:
                provider = "rules"
                message = "高德地图暂时无法确认，已基于知识库和规则生成行程建议。"
        elif self.provider_name == "amap" and not self.map_provider.configured:
            message = "AMap API Key 未配置，已基于知识库和规则生成行程建议。"

        return {
            "available": available,
            "fallback": fallback,
            "provider": provider,
            "city": city,
            "days_count": days,
            "days": grouped_days,
            "itinerary": self._legacy_itinerary(grouped_days),
            "message": message,
        }

    def _empty_result(self, city: str, days: int, message: str) -> dict[str, Any]:
        return {
            "available": False,
            "fallback": True,
            "provider": "rules",
            "city": city,
            "days_count": days,
            "days": [],
            "itinerary": [],
            "message": message,
        }

    def _detect_days(self, question: str) -> int | None:
        match = re.search(r"(\d+)\s*天", question)
        if match:
            return max(1, min(int(match.group(1)), 7))
        cn = re.search(r"([一二两三四五六七])(?:日游|天)", question)
        if cn:
            return {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}.get(cn.group(1), 1)
        return None

    def _detect_pace(self, question: str) -> str:
        for pace, keywords in PACE_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                return pace
        return "均衡"

    def _spots_from_knowledge(self, city: str) -> list[dict[str, Any]]:
        spots = []
        generic_tags = {
            "第一次到访北京", "第一次来成都", "美食", "慢生活", "休闲", "城市漫游", "亲子", "文化", "购物",
            "历史", "皇家建筑", "胡同", "首都", "现代都市", "慢旅行", "第一次到访",
        }
        for item in self.pipeline.retriever.store.chunks:
            if not isinstance(item, dict) or item.get("city") != city:
                continue
            if item.get("category") not in {"attractions", "itinerary", "food", "overview", "tips"}:
                continue
            title = str(item.get("title", ""))
            content = str(item.get("content", ""))
            tags = item.get("tags", []) or []
            for tag in tags:
                tag_text = str(tag).strip()
                tag_looks_like_place = any(marker in tag_text for marker in ["宫", "园", "门", "湖", "山", "街", "巷", "城", "寺", "塔", "基地", "广场"])
                if 2 <= len(tag_text) <= 8 and tag_text not in generic_tags and (item.get("category") in {"attractions", "itinerary"} or tag_looks_like_place):
                    spots.append({"name": tag_text, "type": self._classify_spot(tag_text, content, tags)})
            for place in self._extract_places_from_text(f"{title}\n{content}"):
                spots.append({"name": place, "type": self._classify_spot(place, content, tags)})

        seen = set()
        unique = []
        for spot in spots:
            name = spot["name"].strip()
            if name and name not in seen and len(name) >= 2:
                unique.append({**spot, "name": name})
                seen.add(name)
        return unique[:18]

    def _normalize_spots(self, city: str, places: list[str]) -> list[dict[str, Any]]:
        knowledge_spots = {spot["name"]: spot for spot in self._spots_from_knowledge(city)}
        normalized = []
        seen = set()
        for place in places:
            name = place.strip()
            if not name or name in seen:
                continue
            spot = knowledge_spots.get(name) or {"name": name, "type": self._classify_spot(name, "", [])}
            normalized.append({"name": spot["name"], "type": spot.get("type", "城市漫游")})
            seen.add(name)
        return normalized[:18]

    def _extract_places_from_text(self, text: str) -> list[str]:
        candidates = []
        for marker in ["包括：", "推荐：", "景点：", "路线：", "比如", "如"]:
            if marker in text:
                segment = text.split(marker, 1)[1].split("。", 1)[0]
                candidates.extend(re.split(r"、|，|,|/|和", segment))
        pattern = (
            r"[\u4e00-\u9fffA-Za-z0-9·]{0,10}"
            r"(?:故宫博物院|故宫|天安门广场|人民英雄纪念碑|毛主席纪念堂|天坛|颐和园|"
            r"八达岭长城|慕田峪长城|长城|北海公园|景山公园|恭王府|南锣鼓巷|王府井|前门大街|什刹海|"
            r"公园|博物馆|博物院|寺|街|巷|湖|塔|基地|广场|景区|古镇|市场|商圈|乐园|迪士尼)"
        )
        for match in re.findall(pattern, text):
            candidates.append(match)
        cleaned_places = []
        for item in candidates:
            cleaned = self._clean_place(item)
            if not cleaned:
                continue
            if "和" in cleaned and len(cleaned) >= 8:
                cleaned_places.extend(self._clean_place(part) for part in cleaned.split("和") if self._clean_place(part))
            else:
                cleaned_places.append(cleaned)
        return cleaned_places

    def _clean_place(self, value: str) -> str:
        cleaned = re.sub(r"^[可以去到游览体验随后进入前往这里拥有上午下午晚上和\s，。]+", "", value.strip())
        cleaned = re.sub(r"[等以及附近周边的\s，。]+$", "", cleaned)
        cleaned = cleaned.replace("其独特", "").replace("大约需要四五个小时下午从", "")
        return cleaned

    def _classify_spot(self, name: str, content: str, tags: list[str]) -> str:
        for spot_type, keywords in SPOT_TYPE_KEYWORDS.items():
            if any(keyword in name for keyword in keywords):
                return spot_type
        text = f"{name} {content} {' '.join(str(tag) for tag in tags)}"
        for spot_type, keywords in SPOT_TYPE_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return spot_type
        return "城市漫游"

    def _build_rule_days(self, city: str, days: int, spots: list[dict[str, Any]], pace: str) -> list[dict[str, Any]]:
        per_day = {"轻松": 2, "均衡": 3, "紧凑": 4}.get(pace, 3)
        ordered = self._order_spots(spots)
        result = []
        cursor = 0
        for day in range(1, days + 1):
            day_spots = ordered[cursor : cursor + per_day]
            cursor += per_day
            if not day_spots:
                day_spots = ordered[: min(per_day, len(ordered))]
            theme = self._theme_for_spots(day, day_spots)
            result.append(
                {
                    "day": day,
                    "theme": theme,
                    "pace": pace,
                    "spots": [{"name": spot["name"], "type": spot.get("type", "城市漫游")} for spot in day_spots],
                    "routes": [],
                    "notes": f"基于{city}知识库景点类型和{pace}旅行节奏生成；没有真实地图数据时不提供精确距离和耗时。",
                }
            )
        return result

    def _order_spots(self, spots: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority = ["文化", "城市漫游", "美食", "自然", "亲子"]
        return sorted(spots, key=lambda spot: priority.index(spot.get("type")) if spot.get("type") in priority else len(priority))

    def _theme_for_spots(self, day: int, spots: list[dict[str, Any]]) -> str:
        types = [spot.get("type") for spot in spots]
        if "美食" in types and "城市漫游" in types:
            return "城市慢生活与美食"
        if "文化" in types:
            return "历史文化与城市经典"
        if "自然" in types:
            return "自然景观与轻松游览"
        if "亲子" in types:
            return "亲子友好游览"
        return ["城市经典景点", "文化街区与美食", "轻松休闲与补充游览", "深度体验", "弹性安排"][min(day - 1, 4)]

    def _enrich_with_amap(self, city: str, days: list[dict[str, Any]]) -> dict[str, Any]:
        any_geocoded = False
        enriched_days = []
        for day in days:
            geocoded_spots = []
            for spot in day["spots"]:
                geocode = self.map_provider.geocode(city, spot["name"])
                if geocode.get("available"):
                    any_geocoded = True
                    geocoded_spots.append({**spot, "lat": geocode.get("lat"), "lng": geocode.get("lng")})
                else:
                    geocoded_spots.append(spot)

            routes = []
            for origin, destination in zip(geocoded_spots, geocoded_spots[1:]):
                route = self.map_provider.walking_route(origin, destination)
                if route.get("available"):
                    routes.append({key: route.get(key) for key in ["from", "to", "distance_m", "duration_min", "mode"]})

            enriched_days.append({**day, "spots": geocoded_spots, "routes": routes})
        return {"available": any_geocoded, "days": enriched_days}

    def _legacy_itinerary(self, days: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "day": item["day"],
                "theme": item["theme"],
                "places": [spot["name"] for spot in item.get("spots", [])],
                "note": item.get("notes", ""),
            }
            for item in days
        ]

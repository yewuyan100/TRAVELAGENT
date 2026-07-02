from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings


CITY_COORDS = {
    "成都": (30.5728, 104.0668),
    "重庆": (29.5630, 106.5516),
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "杭州": (30.2741, 120.1551),
    "西安": (34.3416, 108.9398),
    "南京": (32.0603, 118.7969),
    "苏州": (31.2989, 120.5853),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "厦门": (24.4798, 118.0894),
    "青岛": (36.0671, 120.3826),
    "长沙": (28.2282, 112.9388),
    "武汉": (30.5928, 114.3055),
    "昆明": (25.0389, 102.7183),
    "三亚": (18.2528, 109.5119),
    "东京": (35.6762, 139.6503),
    "大阪": (34.6937, 135.5023),
    "京都": (35.0116, 135.7681),
    "首尔": (37.5665, 126.9780),
    "新加坡": (1.3521, 103.8198),
    "曼谷": (13.7563, 100.5018),
    "巴黎": (48.8566, 2.3522),
    "伦敦": (51.5072, -0.1276),
}

WEATHER_CODE_TEXT = {
    0: "晴朗",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴天",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "较强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "阵雨",
    81: "较强阵雨",
    82: "强阵雨",
    95: "雷暴",
}


@dataclass(frozen=True)
class WeatherQuery:
    city: str


class WeatherProvider:
    def query(self, query: WeatherQuery) -> dict[str, Any]:
        raise NotImplementedError


class OpenMeteoProvider(WeatherProvider):
    def __init__(self, base_url: str = settings.weather_base_url):
        self.base_url = base_url.rstrip("/")

    def query(self, query: WeatherQuery) -> dict[str, Any]:
        coords = CITY_COORDS.get(query.city)
        if not coords:
            return {
                "available": False,
                "city": query.city,
                "message": "天气工具暂未覆盖该城市，无法确认实时天气。",
                "raw": {},
            }

        latitude, longitude = coords
        url = f"{self.base_url}/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        }

        try:
            response = httpx.get(url, params=params, timeout=8.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {
                "available": False,
                "city": query.city,
                "message": f"实时天气暂时无法确认：{exc}",
                "raw": {},
            }

        current = data.get("current", {})
        temperature = current.get("temperature_2m")
        weather_code = current.get("weather_code")
        weather_text = WEATHER_CODE_TEXT.get(weather_code, "未知天气")
        wind_speed = current.get("wind_speed_10m")
        summary = f"{query.city}当前天气：{weather_text}，气温约 {temperature}°C，风速约 {wind_speed} km/h。"

        return {
            "available": True,
            "city": query.city,
            "summary": summary,
            "temperature": "" if temperature is None else f"{temperature}°C",
            "weather": weather_text,
            "raw": data,
        }


class QWeatherProvider(WeatherProvider):
    def __init__(self, api_key: str | None = settings.weather_api_key, base_url: str = settings.weather_base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def query(self, query: WeatherQuery) -> dict[str, Any]:
        if not self.api_key:
            return {"available": False, "city": query.city, "message": "天气工具暂未配置，无法查询实时天气。", "raw": {}}

        coords = CITY_COORDS.get(query.city)
        if not coords:
            return {"available": False, "city": query.city, "message": "天气工具暂未覆盖该城市，无法确认实时天气。", "raw": {}}

        latitude, longitude = coords
        url = f"{self.base_url}/v7/weather/now"
        params = {"location": f"{longitude},{latitude}", "key": self.api_key}

        try:
            response = httpx.get(url, params=params, timeout=8.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"available": False, "city": query.city, "message": f"实时天气暂时无法确认：{exc}", "raw": {}}

        now = data.get("now", {})
        text = now.get("text", "未知天气")
        temp = now.get("temp")
        summary = f"{query.city}当前天气：{text}，气温约 {temp}°C。"
        return {"available": True, "city": query.city, "summary": summary, "temperature": f"{temp}°C" if temp else "", "weather": text, "raw": data}


class WeatherTool:
    name = "weather_tool"

    def __init__(self):
        provider = settings.weather_provider.lower()
        if provider == "qweather":
            self.provider: WeatherProvider = QWeatherProvider()
        else:
            self.provider = OpenMeteoProvider()

    def run(self, city: str | None) -> dict[str, Any]:
        if not city:
            return {"available": False, "message": "缺少城市信息，无法查询实时天气。", "raw": {}}
        return self.provider.query(WeatherQuery(city=city))

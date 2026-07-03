from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
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

CN_DAY_MAP = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7}


@dataclass(frozen=True)
class WeatherQuery:
    city: str
    question: str = ""
    forecast_days: int = 3
    target_offset: int = 0

    @property
    def target_date(self) -> str:
        return (date.today() + timedelta(days=self.target_offset)).isoformat()


class WeatherProvider:
    name = "base"

    @property
    def configured(self) -> bool:
        return True

    def query(self, query: WeatherQuery) -> dict[str, Any]:
        raise NotImplementedError


def _to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    number = _to_number(value)
    if number is None:
        return None
    return int(round(number))


def _wind_text(value: Any, unit: str = "km/h") -> str | None:
    if value is None or value == "":
        return None
    return f"{value} {unit}"


def _travel_advice(condition: str | None, temp_min: float | None, temp_max: float | None, rain_probability: int | None) -> str:
    condition_text = condition or "天气待确认"
    advice = []
    if rain_probability is not None and rain_probability >= 60:
        advice.append("降水概率较高，建议携带雨具并预留室内备选行程")
    elif rain_probability is not None and rain_probability >= 30:
        advice.append("可能有降水，建议随身带伞")
    elif "雨" in condition_text or "雷" in condition_text:
        advice.append("天气可能影响户外活动，建议携带雨具")

    if temp_max is not None and temp_max >= 33:
        advice.append("气温偏高，适合减少暴晒时段的户外步行")
    elif temp_min is not None and temp_min <= 5:
        advice.append("气温偏低，建议注意保暖")

    if not advice:
        advice.append("整体适合城市漫游，出发前仍建议再次确认实时天气")
    return "；".join(advice) + "。"


def _forecast_scope(question: str) -> tuple[int, int]:
    question = question or ""
    target_offset = 1 if "明天" in question else 0
    forecast_days = 3

    digit_match = re.search(r"未来?\s*(\d+)\s*天|近\s*(\d+)\s*天", question)
    if digit_match:
        value = next(group for group in digit_match.groups() if group)
        forecast_days = max(1, min(int(value), 7))
    else:
        cn_match = re.search(r"未来?\s*([一二两三四五六七])\s*天|近\s*([一二两三四五六七])\s*天", question)
        if cn_match:
            value = next(group for group in cn_match.groups() if group)
            forecast_days = CN_DAY_MAP.get(value, 3)
        elif "一周" in question or "7天" in question or "七天" in question:
            forecast_days = 7
        elif "明天" in question:
            forecast_days = 2
        elif "后天" in question:
            target_offset = 2
            forecast_days = 3

    forecast_days = max(forecast_days, target_offset + 1)
    return min(forecast_days, 7), min(target_offset, 6)


class OpenMeteoProvider(WeatherProvider):
    name = "openmeteo"

    def __init__(self, base_url: str = settings.openmeteo_base_url):
        self.base_url = base_url.rstrip("/")

    def query(self, query: WeatherQuery) -> dict[str, Any]:
        coords = CITY_COORDS.get(query.city)
        if not coords:
            return {
                "available": False,
                "provider": self.name,
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
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
            "forecast_days": query.forecast_days,
            "timezone": "auto",
        }

        try:
            response = httpx.get(url, params=params, timeout=8.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {
                "available": False,
                "provider": self.name,
                "city": query.city,
                "message": f"实时天气暂时无法确认：{exc}",
                "raw": {},
            }

        current = data.get("current", {})
        daily = data.get("daily", {})
        forecast = self._build_forecast(daily)
        target = forecast[min(query.target_offset, max(len(forecast) - 1, 0))] if forecast else {}
        condition = target.get("condition") or WEATHER_CODE_TEXT.get(current.get("weather_code"), "未知天气")
        current_temperature = _to_number(current.get("temperature_2m"))
        temp_min = _to_number(target.get("temp_min"))
        temp_max = _to_number(target.get("temp_max"))
        rain_probability = _to_int(target.get("rain_probability"))
        wind = target.get("wind") or _wind_text(current.get("wind_speed_10m"))
        travel_advice = _travel_advice(condition, temp_min, temp_max, rain_probability)
        summary = self._summary(query.city, target.get("date") or query.target_date, condition, temp_min, temp_max, rain_probability, wind, travel_advice)

        return {
            "available": True,
            "provider": self.name,
            "city": query.city,
            "date": target.get("date") or query.target_date,
            "condition": condition,
            "current_temperature": current_temperature,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "rain_probability": rain_probability,
            "wind": wind,
            "travel_advice": travel_advice,
            "summary": summary,
            "forecast": forecast,
            "raw": data,
        }

    def _build_forecast(self, daily: dict[str, Any]) -> list[dict[str, Any]]:
        dates = daily.get("time", []) or []
        codes = daily.get("weather_code", []) or []
        temp_max = daily.get("temperature_2m_max", []) or []
        temp_min = daily.get("temperature_2m_min", []) or []
        rain = daily.get("precipitation_probability_max", []) or []
        wind = daily.get("wind_speed_10m_max", []) or []

        forecast = []
        for index, forecast_date in enumerate(dates):
            forecast.append(
                {
                    "date": forecast_date,
                    "condition": WEATHER_CODE_TEXT.get(codes[index] if index < len(codes) else None, "未知天气"),
                    "temp_min": _to_number(temp_min[index] if index < len(temp_min) else None),
                    "temp_max": _to_number(temp_max[index] if index < len(temp_max) else None),
                    "rain_probability": _to_int(rain[index] if index < len(rain) else None),
                    "wind": _wind_text(wind[index] if index < len(wind) else None),
                }
            )
        return forecast

    def _summary(self, city: str, forecast_date: str, condition: str, temp_min: float | None, temp_max: float | None, rain_probability: int | None, wind: str | None, advice: str) -> str:
        temp_text = "温度待确认" if temp_min is None or temp_max is None else f"{temp_min:g}-{temp_max:g}°C"
        rain_text = "降水概率待确认" if rain_probability is None else f"降水概率约 {rain_probability}%"
        wind_text = wind or "风速待确认"
        return f"{city} {forecast_date} 天气：{condition}，{temp_text}，{rain_text}，风速/风力：{wind_text}。{advice}"


class QWeatherProvider(WeatherProvider):
    name = "qweather"

    def __init__(self, api_key: str | None = settings.qweather_api_key, base_url: str = settings.qweather_base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def query(self, query: WeatherQuery) -> dict[str, Any]:
        if not self.api_key:
            return {"available": False, "provider": self.name, "city": query.city, "message": "QWeather API Key 未配置。", "raw": {}}

        coords = CITY_COORDS.get(query.city)
        if not coords:
            return {"available": False, "provider": self.name, "city": query.city, "message": "天气工具暂未覆盖该城市。", "raw": {}}

        latitude, longitude = coords
        location = f"{longitude},{latitude}"
        days_path = "7d" if query.forecast_days > 3 else "3d"
        try:
            now_data = self._request("/v7/weather/now", {"location": location})
            daily_data = self._request(f"/v7/weather/{days_path}", {"location": location})
        except Exception as exc:
            return {"available": False, "provider": self.name, "city": query.city, "message": f"QWeather 查询失败：{exc}", "raw": {}}

        now = now_data.get("now", {})
        forecast = self._build_forecast(daily_data.get("daily", []))
        target = forecast[min(query.target_offset, max(len(forecast) - 1, 0))] if forecast else {}
        condition = target.get("condition") or now.get("text") or "未知天气"
        temp_min = _to_number(target.get("temp_min"))
        temp_max = _to_number(target.get("temp_max"))
        rain_probability = _to_int(target.get("rain_probability"))
        wind = target.get("wind") or now.get("windScale") or now.get("windSpeed")
        if wind and str(wind).isdigit():
            wind = f"{wind}级"
        advice = _travel_advice(condition, temp_min, temp_max, rain_probability)
        summary = OpenMeteoProvider._summary(self, query.city, target.get("date") or query.target_date, condition, temp_min, temp_max, rain_probability, wind, advice)

        return {
            "available": True,
            "provider": self.name,
            "city": query.city,
            "date": target.get("date") or query.target_date,
            "condition": condition,
            "current_temperature": _to_number(now.get("temp")),
            "temp_min": temp_min,
            "temp_max": temp_max,
            "rain_probability": rain_probability,
            "wind": wind,
            "travel_advice": advice,
            "summary": summary,
            "forecast": forecast,
            "raw": {"now": now_data, "daily": daily_data},
        }

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = httpx.get(f"{self.base_url}{path}", params={**params, "key": self.api_key}, timeout=8.0)
        response.raise_for_status()
        data = response.json()
        code = str(data.get("code", "200"))
        if code != "200":
            raise RuntimeError(f"QWeather 返回 code={code}")
        return data

    def _build_forecast(self, daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
        forecast = []
        for item in daily:
            rain = item.get("pop") or item.get("precip")
            forecast.append(
                {
                    "date": item.get("fxDate"),
                    "condition": item.get("textDay") or item.get("textNight"),
                    "temp_min": _to_number(item.get("tempMin")),
                    "temp_max": _to_number(item.get("tempMax")),
                    "rain_probability": _to_int(rain),
                    "wind": item.get("windScaleDay") or item.get("windSpeedDay") or item.get("windDirDay"),
                }
            )
        return forecast


class AmapWeatherProvider(WeatherProvider):
    name = "amap"

    def __init__(self, api_key: str | None = settings.amap_api_key, base_url: str = settings.map_base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def query(self, query: WeatherQuery) -> dict[str, Any]:
        if not self.api_key:
            return {"available": False, "provider": self.name, "city": query.city, "message": "AMap API Key 未配置。", "raw": {}}

        try:
            response = httpx.get(
                f"{self.base_url}/v3/weather/weatherInfo",
                params={"key": self.api_key, "city": query.city, "extensions": "all"},
                timeout=8.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {"available": False, "provider": self.name, "city": query.city, "message": f"高德天气查询失败：{exc}", "raw": {}}

        if str(data.get("status")) != "1":
            return {"available": False, "provider": self.name, "city": query.city, "message": data.get("info", "高德天气返回失败"), "raw": data}

        casts = (data.get("forecasts") or [{}])[0].get("casts", [])
        forecast = [
            {
                "date": item.get("date"),
                "condition": item.get("dayweather") or item.get("nightweather"),
                "temp_min": _to_number(item.get("nighttemp")),
                "temp_max": _to_number(item.get("daytemp")),
                "rain_probability": None,
                "wind": item.get("daywind") or item.get("daypower"),
            }
            for item in casts
        ]
        target = forecast[min(query.target_offset, max(len(forecast) - 1, 0))] if forecast else {}
        condition = target.get("condition") or "未知天气"
        advice = _travel_advice(condition, target.get("temp_min"), target.get("temp_max"), None)
        summary = OpenMeteoProvider._summary(self, query.city, target.get("date") or query.target_date, condition, target.get("temp_min"), target.get("temp_max"), None, target.get("wind"), advice)
        return {
            "available": True,
            "provider": self.name,
            "city": query.city,
            "date": target.get("date") or query.target_date,
            "condition": condition,
            "current_temperature": None,
            "temp_min": target.get("temp_min"),
            "temp_max": target.get("temp_max"),
            "rain_probability": None,
            "wind": target.get("wind"),
            "travel_advice": advice,
            "summary": summary,
            "forecast": forecast,
            "raw": data,
        }


class WeatherTool:
    name = "weather_tool"

    def __init__(self):
        self.openmeteo = OpenMeteoProvider()
        self.providers: dict[str, WeatherProvider] = {
            "openmeteo": self.openmeteo,
            "open_meteo": self.openmeteo,
            "qweather": QWeatherProvider(),
            "amap": AmapWeatherProvider(),
        }
        self.provider_name = settings.weather_provider.lower().replace("-", "_")

    def run(self, city: str | None, question: str = "") -> dict[str, Any]:
        if not city:
            return {"available": False, "provider": self.provider_name, "message": "缺少城市信息，无法查询实时天气。", "raw": {}}

        forecast_days, target_offset = _forecast_scope(question)
        query = WeatherQuery(city=city, question=question, forecast_days=forecast_days, target_offset=target_offset)
        provider = self.providers.get(self.provider_name, self.openmeteo)
        result = provider.query(query)
        if result.get("available"):
            return result

        if provider is not self.openmeteo:
            fallback = self.openmeteo.query(query)
            if fallback.get("available"):
                fallback["fallback"] = True
                fallback["message"] = f"{provider.name} 不可用，已自动降级到 Open-Meteo。"
                return fallback

        return result

"""Weather API client for New Haven using Open-Meteo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import requests


# Hard-coded coordinates for New Haven, CT
NEW_HAVEN_COORDS = {
    "latitude": 41.3083,
    "longitude": -72.9279,
}


@dataclass
class HourlyForecast:
    time: datetime
    temperature_c: float
    humidity: int
    weather_code: int
    summary: str


@dataclass
class WeatherReport:
    location: str
    fetched_at: datetime
    temperature_c: float
    feels_like_c: float
    humidity: int
    wind_speed_kph: float
    wind_direction_deg: int
    weather_code: int
    summary: str
    hourly: List[HourlyForecast]


class WeatherClient:
    """Fetches weather data for New Haven from Open-Meteo."""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()

    def fetch_weather(self) -> WeatherReport:
        params = {
            "latitude": NEW_HAVEN_COORDS["latitude"],
            "longitude": NEW_HAVEN_COORDS["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m",
            "hourly": "temperature_2m,relative_humidity_2m,weather_code",
            "forecast_days": 1,
            "timezone": "auto",
        }

        response = self.session.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()

        current = payload.get("current")
        hourly = payload.get("hourly")

        if not current or not hourly:
            raise ValueError("Unexpected API response structure")

        weather_code = int(current.get("weather_code", -1))

        report = WeatherReport(
            location="New Haven, CT",
            fetched_at=_parse_iso_datetime(payload.get("current", {}).get("time")) or datetime.utcnow(),
            temperature_c=float(current["temperature_2m"]),
            feels_like_c=float(current.get("apparent_temperature", current["temperature_2m"])),
            humidity=int(current.get("relative_humidity_2m", 0)),
            wind_speed_kph=float(current.get("wind_speed_10m", 0.0)),
            wind_direction_deg=int(current.get("wind_direction_10m", 0)),
            weather_code=weather_code,
            summary=_code_to_summary(weather_code),
            hourly=_build_hourly(hourly),
        )
        return report


def _build_hourly(data: dict) -> List[HourlyForecast]:
    times = data.get("time") or []
    temps = data.get("temperature_2m") or []
    humidities = data.get("relative_humidity_2m") or []
    codes = data.get("weather_code") or []

    items: List[HourlyForecast] = []
    for time_str, temp, humidity, code in zip(times, temps, humidities, codes):
        dt = _parse_iso_datetime(time_str)
        if dt is None:
            continue
        code_int = int(code)
        items.append(
            HourlyForecast(
                time=dt,
                temperature_c=float(temp),
                humidity=int(humidity),
                weather_code=code_int,
                summary=_code_to_summary(code_int),
            )
        )

    # Only keep upcoming hours (including current hour) and limit to next 6 entries
    now = datetime.utcnow()
    upcoming = [item for item in items if item.time >= now][:6]
    return upcoming


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def _code_to_summary(code: int) -> str:
    return WEATHER_CODE_MAP.get(code, "Unknown conditions")


WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

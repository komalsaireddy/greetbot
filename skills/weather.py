"""
GreetBot Weather Skill
=======================
Fetches current weather using the OpenWeatherMap API.
Falls back gracefully if no API key is configured.
"""

import requests
from typing import Optional

from config import WEATHER_API_KEY, WEATHER_CITY
from utils.logger import get_logger

log = get_logger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: Optional[str] = None) -> Optional[dict]:
    """
    Fetch current weather for a city.

    Parameters
    ----------
    city:
        City name (defaults to ``WEATHER_CITY`` from config).

    Returns
    -------
    dict or None
        Weather info dict, or None on failure.
        Keys: city, temp_c, feels_like_c, description, humidity, wind_speed.
    """
    if not WEATHER_API_KEY:
        log.warning("WEATHER_API_KEY not set — weather skill unavailable")
        return None

    target_city = city or WEATHER_CITY

    try:
        resp = requests.get(
            _BASE_URL,
            params={
                "q":     target_city,
                "appid": WEATHER_API_KEY,
                "units": "metric",
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "city":         data.get("name", target_city),
            "country":      data.get("sys", {}).get("country", ""),
            "temp_c":       round(data["main"]["temp"], 1),
            "feels_like_c": round(data["main"]["feels_like"], 1),
            "description":  data["weather"][0]["description"].capitalize(),
            "humidity":     data["main"]["humidity"],
            "wind_speed":   data.get("wind", {}).get("speed", 0),
        }

    except requests.exceptions.Timeout:
        log.warning("Weather API timed out")
        return None
    except requests.exceptions.HTTPError as exc:
        log.error(f"Weather API HTTP error: {exc}")
        return None
    except Exception as exc:
        log.error(f"Weather fetch error: {exc}")
        return None


def format_weather(info: Optional[dict]) -> str:
    """
    Format weather info as a natural-language TTS-ready string.

    Parameters
    ----------
    info:
        Dict from ``get_weather()``.

    Returns
    -------
    str
        Spoken weather summary.
    """
    if not info:
        return (
            "I'm sorry, I couldn't get the weather right now. "
            "Make sure the WEATHER_API_KEY is set in your .env file."
        )

    return (
        f"Currently in {info['city']}, it's {info['temp_c']} degrees Celsius "
        f"with {info['description'].lower()}. "
        f"It feels like {info['feels_like_c']} degrees. "
        f"Humidity is {info['humidity']} percent "
        f"and wind speed is {info['wind_speed']} meters per second."
    )


def extract_city(text: str) -> Optional[str]:
    """
    Try to extract a city name from a weather query.

    Examples::

        "What's the weather in Mumbai?" → "Mumbai"
        "How's the weather?" → None

    Parameters
    ----------
    text:
        User's message.

    Returns
    -------
    str or None
        Extracted city name, or None if not found.
    """
    import re
    patterns = [
        r"weather (?:in|at|for) ([A-Za-z\s]+?)(?:\?|$|\.)",
        r"(?:in|at) ([A-Za-z\s]+?) (?:weather|forecast)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return None


def is_weather_query(text: str) -> bool:
    """
    Detect if a user message is asking about weather.

    Parameters
    ----------
    text:
        User's message.

    Returns
    -------
    bool
        True if the message is a weather query.
    """
    keywords = ["weather", "temperature", "forecast", "rain", "sunny",
                "cloudy", "humid", "how hot", "how cold", "climate"]
    lower = text.lower()
    return any(kw in lower for kw in keywords)

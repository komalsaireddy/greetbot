"""
GreetBot System Skill
======================
Provides system information: CPU, RAM, temperature, and uptime.
Used when users ask about the robot's health or performance status.
"""

import time
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

_START_TIME = time.time()


def get_system_info() -> dict:
    """
    Gather current system statistics using psutil.

    Returns
    -------
    dict
        Keys: cpu_percent, ram_percent, ram_used_mb, ram_total_mb,
              temperature_c (if available), uptime_seconds, uptime_str.
        Values are None for unavailable metrics.
    """
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        uptime = time.time() - _START_TIME

        # Temperature (Raspberry Pi specific)
        temp: Optional[float] = None
        try:
            temps = psutil.sensors_temperatures()
            if "cpu_thermal" in temps:
                temp = temps["cpu_thermal"][0].current
            elif "coretemp" in temps:
                temp = temps["coretemp"][0].current
        except Exception:
            pass

        from utils.helpers import format_duration
        return {
            "cpu_percent":    round(cpu, 1),
            "ram_percent":    round(mem.percent, 1),
            "ram_used_mb":    mem.used // (1024 * 1024),
            "ram_total_mb":   mem.total // (1024 * 1024),
            "temperature_c":  round(temp, 1) if temp else None,
            "uptime_seconds": int(uptime),
            "uptime_str":     format_duration(uptime),
        }

    except ImportError:
        log.warning("psutil not installed — system info unavailable")
        return {}
    except Exception as exc:
        log.error(f"System info error: {exc}")
        return {}


def format_system_info(info: dict) -> str:
    """
    Format system info dict as a natural language summary for TTS.

    Parameters
    ----------
    info:
        Dict from ``get_system_info()``.

    Returns
    -------
    str
        Human-readable summary.
    """
    if not info:
        return "I couldn't retrieve system information right now."

    parts = [
        f"CPU is at {info.get('cpu_percent', 'N/A')} percent.",
        f"Memory usage is {info.get('ram_percent', 'N/A')} percent.",
    ]

    if info.get("temperature_c"):
        parts.append(f"My CPU temperature is {info['temperature_c']} degrees Celsius.")

    if info.get("uptime_str"):
        parts.append(f"I've been running for {info['uptime_str']}.")

    return " ".join(parts)


def is_system_query(text: str) -> bool:
    """
    Detect if a user message is asking about system status.

    Parameters
    ----------
    text:
        User's message.

    Returns
    -------
    bool
        True if the message is a system status query.
    """
    keywords = [
        "cpu", "memory", "ram", "temperature", "temp", "status",
        "how are you doing", "system", "health", "performance",
        "battery", "uptime", "how long", "running for",
    ]
    lower = text.lower()
    return any(kw in lower for kw in keywords)

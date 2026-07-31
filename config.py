"""
GreetBot Configuration
======================
Central configuration module. All paths, constants, and settings live here.
Import from this module — never use hardcoded values elsewhere.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ==========================
# PROJECT PATHS
# ==========================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)

# ==========================
# API KEYS
# ==========================

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
WEATHER_CITY: str = os.getenv("WEATHER_CITY", "Hyderabad")

# Telegram Bot API (for visitor alerts and file sharing)
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ==========================
# ROBOT IDENTITY
# ==========================

ROBOT_NAME: str = "GreetBot"
VERSION: str = "2.0"

# ==========================
# AI MODEL
# ==========================

LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "256"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "false").lower() == "true"
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

# ==========================
# CAMERA
# ==========================

# Camera device index (0 = default, 1 = external USB cam)
CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_ENABLED: bool = os.getenv("CAMERA_ENABLED", "true").lower() == "true"

# How many frames to skip between full face-recognition passes (reduces CPU)
CAMERA_RECOGNITION_SKIP: int = int(os.getenv("CAMERA_RECOGNITION_SKIP", "3"))

# Camera resolution
CAMERA_WIDTH: int = int(os.getenv("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT: int = int(os.getenv("CAMERA_HEIGHT", "480"))

# ==========================
# AUDIO
# ==========================

SAMPLE_RATE: int = 16000
CHANNELS: int = 1

# Whisper model size: tiny.en, base, small, medium, large
STT_MODEL: str = os.getenv("STT_MODEL", "tiny.en")

# Voice activity detection safeguards.  A value of 0 disables the limit.
LISTEN_TIMEOUT_SECONDS: float = float(os.getenv("LISTEN_TIMEOUT_SECONDS", "20"))
MAX_RECORDING_SECONDS: float = float(os.getenv("MAX_RECORDING_SECONDS", "12"))
AUDIO_QUEUE_MAX_FRAMES: int = int(os.getenv("AUDIO_QUEUE_MAX_FRAMES", "200"))

# TTS engine: "edge" (online, better quality) or "piper" (offline, local)
TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge")

# Edge TTS voice
EDGE_TTS_VOICE: str = "en-US-AndrewNeural"

# Piper TTS model path (download from https://github.com/rhasspy/piper)
PIPER_MODEL_PATH: str = os.getenv(
    "PIPER_MODEL_PATH",
    str(BASE_DIR / "assets" / "voices" / "en_US-lessac-medium.onnx")
)

# ==========================
# AVATAR
# ==========================

# Enable the pygame robot face avatar window
AVATAR_ENABLED: bool = os.getenv("AVATAR_ENABLED", "true").lower() == "true"

AVATAR_WIDTH: int = 800
AVATAR_HEIGHT: int = 600
AVATAR_FPS: int = 60

# ==========================
# MEMORY
# ==========================

DATABASE_PATH: Path = BASE_DIR / "database" / "greetbot.db"

# Max conversation turns to keep in short-term memory per session
SHORT_TERM_MAX_TURNS: int = 20

# ==========================
# ASSETS
# ==========================

ASSETS_DIR: Path = BASE_DIR / "assets"
FACE_DIR: Path = ASSETS_DIR / "faces"
SOUNDS_DIR: Path = ASSETS_DIR / "sounds"
VOICES_DIR: Path = ASSETS_DIR / "voices"

# ==========================
# VISION
# ==========================

# Face recognition confidence threshold (lower = stricter)
FACE_RECOGNITION_THRESHOLD: float = float(os.getenv("FACE_RECOGNITION_THRESHOLD", "0.48"))

# dlib face encoding is CPU-heavy.  A quarter-size frame is a good Pi 5
# starting point; boxes are scaled back to the camera's original resolution.
FACE_RECOGNITION_SCALE: float = float(os.getenv("FACE_RECOGNITION_SCALE", "0.25"))

# Face dir inside vision module (for backward compat)
VISION_FACES_DIR: Path = BASE_DIR / "vision" / "faces"

# Number of frames an unknown face must persist before being saved
UNKNOWN_FACE_SAVE_THRESHOLD: int = 15

# ==========================
# LOGGING
# ==========================

LOG_DIR: Path = BASE_DIR / "logs"
LOG_FILE: Path = LOG_DIR / "app.log"
ERROR_LOG: Path = LOG_DIR / "errors.log"

DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ==========================
# PLATFORM & HARDWARE
# ==========================

IS_RASPBERRY_PI: bool = os.path.exists("/proc/device-tree/model") and "Raspberry Pi" in open(
    "/proc/device-tree/model", "r", errors="ignore"
).read()

IS_LINUX: bool = sys.platform.startswith("linux")

# Enable servo motors (disabled by default unless explicitly started with --servo)
SERVO_ENABLED: bool = os.getenv("SERVO_ENABLED", "false").lower() == "true"

# ==========================
# ENSURE DIRECTORIES EXIST
# ==========================

for _dir in [ASSETS_DIR, FACE_DIR, SOUNDS_DIR, VOICES_DIR, LOG_DIR,
             VISION_FACES_DIR, DATABASE_PATH.parent]:
    _dir.mkdir(parents=True, exist_ok=True)

# ==========================
# STARTUP DEBUG PRINT
# ==========================

if DEBUG:
    print("=" * 50)
    print(f"{ROBOT_NAME} v{VERSION} — Configuration Loaded")
    print(f"Base Directory : {BASE_DIR}")
    print(f"Platform       : {'Raspberry Pi' if IS_RASPBERRY_PI else sys.platform}")
    print(f"API Key        : {'✓ Found' if GROQ_API_KEY else '✗ Missing'}")
    print(f"LLM Model      : {LLM_MODEL}")
    print(f"TTS Engine     : {TTS_ENGINE}")
    print(f"Camera Index   : {CAMERA_INDEX}")
    print(f"Avatar         : {'Enabled' if AVATAR_ENABLED else 'Disabled'}")
    print("=" * 50)

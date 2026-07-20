from pathlib import Path
import os
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

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ==========================
# AI MODEL
# ==========================

LLM_MODEL = "llama-3.3-70b-versatile"

# ==========================
# ROBOT SETTINGS
# ==========================

ROBOT_NAME = "GreetBot"

VERSION = "2.0"

# ==========================
# WINDOW
# ==========================

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

# ==========================
# AUDIO
# ==========================

SAMPLE_RATE = 16000
CHANNELS = 1

# ==========================
# CAMERA
# ==========================

CAMERA_INDEX = 0

# ==========================
# MEMORY
# ==========================

DATABASE_PATH = BASE_DIR / "database" / "greetbot.db"

# ==========================
# ASSETS
# ==========================

ASSETS_DIR = BASE_DIR / "assets"

FACE_DIR = ASSETS_DIR / "faces"

SOUNDS_DIR = ASSETS_DIR / "sounds"

# ==========================
# LOGGING
# ==========================

LOG_DIR = BASE_DIR / "logs"

LOG_FILE = LOG_DIR / "app.log"

ERROR_LOG = LOG_DIR / "errors.log"

# ==========================
# DEBUG
# ==========================

DEBUG = True

if DEBUG:
    print("=" * 50)
    print("GreetBot Configuration Loaded")
    print("Base Directory :", BASE_DIR)
    print("Env File       :", ENV_FILE)
    print("API Key Found  :", "YES" if GROQ_API_KEY else "NO")
    print("Model          :", LLM_MODEL)
    print("=" * 50)

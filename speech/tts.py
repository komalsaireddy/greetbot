"""
GreetBot Text-to-Speech
========================
Dual-engine TTS: EdgeTTS (online, high quality) and PiperTTS (offline, local).
Choose the engine via ``TTS_ENGINE`` in config or the ``.env`` file.

Both engines expose the same ``speak(text)`` interface.
The ``create_tts()`` factory selects the appropriate engine automatically.
"""

import asyncio
import os
import sys
import subprocess
import tempfile
import threading
from abc import ABC, abstractmethod
from typing import Optional

from config import TTS_ENGINE, EDGE_TTS_VOICE, PIPER_MODEL_PATH
from utils.helpers import clean_text
from utils.logger import get_logger

log = get_logger(__name__)


# ── Abstract Base ─────────────────────────────────────────────────────────────

class BaseTTS(ABC):
    """Abstract base class for all TTS engines."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._player: Optional[subprocess.Popen] = None

    @abstractmethod
    def speak(self, text: str) -> None:
        """Convert text to speech and play it. Blocks until done."""
        ...

    def stop(self) -> None:
        """Interrupt currently playing speech."""
        with self._lock:
            if self._player and self._player.poll() is None:
                self._player.terminate()
                try:
                    self._player.wait(timeout=1)
                except Exception:
                    pass
                self._player = None

    def is_speaking(self) -> bool:
        """Return True if audio is currently playing."""
        with self._lock:
            return (
                self._player is not None
                and self._player.poll() is None
            )

    def _play_file(self, filename: str) -> None:
        """Play an audio file using mpg123 or aplay depending on format."""
        ext = os.path.splitext(filename)[1].lower()

        if sys.platform == "darwin":
            cmd = ["afplay", filename]
        else:
            if ext == ".mp3":
                cmd = ["mpg123", "-q", filename]
            elif ext in (".wav", ".ogg"):
                cmd = ["aplay", filename]
            else:
                cmd = ["mpg123", "-q", filename]

        try:
            with self._lock:
                self._player = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            self._player.wait()
        except FileNotFoundError:
            log.error(f"Audio player not found. Install {'afplay' if sys.platform == 'darwin' else 'mpg123/aplay'}.")
        except Exception as e:
            log.error(f"Audio playback error: {e}")
        finally:
            with self._lock:
                self._player = None

        try:
            os.remove(filename)
        except Exception:
            pass


# ── Edge TTS (Online) ─────────────────────────────────────────────────────────

class EdgeTTS(BaseTTS):
    """
    Microsoft Edge TTS via the edge-tts library.

    Requires internet connection. Produces high-quality neural voice output.
    Uses ``mpg123`` to play the generated MP3 file.

    Parameters
    ----------
    voice:
        Edge TTS voice identifier (e.g. ``"en-US-AndrewNeural"``).
    rate:
        Speaking rate adjustment (e.g. ``"+5%"``).
    pitch:
        Pitch adjustment (e.g. ``"+0Hz"``).
    """

    def __init__(
        self,
        voice: str = EDGE_TTS_VOICE,
        rate: str = "+5%",
        pitch: str = "+0Hz",
    ) -> None:
        super().__init__()
        self._voice = voice
        self._rate  = rate
        self._pitch = pitch
        log.info(f"EdgeTTS ready (voice={voice})")

    async def _generate(self, text: str, filename: str) -> None:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text,
            voice=self._voice,
            rate=self._rate,
            pitch=self._pitch,
        )
        await communicate.save(filename)

    def speak(self, text: str) -> None:
        """Speak text using Edge TTS. Blocks until audio playback finishes."""
        if not text.strip():
            return

        clean = clean_text(text)
        log.info(f"TTS (Edge): {clean[:60]}...")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            filename = tmp.name

        try:
            asyncio.run(self._generate(clean, filename))
            self._play_file(filename)
        except Exception as exc:
            log.error(f"TTS failed: {exc}", exc_info=True)
            try:
                os.remove(filename)
            except Exception:
                pass
            
            # Fallback for when network fails
            log.info("Falling back to offline TTS...")
            if sys.platform == "darwin":
                os.system(f'say "{clean}"')
            else:
                os.system(f'espeak "{clean}"')


# ── Piper TTS (Offline) ───────────────────────────────────────────────────────

class PiperTTS(BaseTTS):
    """
    Piper local TTS — runs entirely offline on device.

    Requires the ``piper`` binary and an ONNX voice model.
    Download voices from: https://github.com/rhasspy/piper/releases

    Parameters
    ----------
    model_path:
        Path to the ``.onnx`` voice model file.
    """

    def __init__(self, model_path: str = PIPER_MODEL_PATH) -> None:
        super().__init__()
        self._model_path = model_path
        self._available = self._check_piper()
        if self._available:
            log.info(f"PiperTTS ready (model={model_path})")
        else:
            log.warning("Piper binary or model not found — falling back to EdgeTTS")

    def _check_piper(self) -> bool:
        """Check if the piper binary and model file exist."""
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True, timeout=3
            )
            model_exists = os.path.exists(self._model_path)
            return result.returncode == 0 and model_exists
        except Exception:
            return False

    def speak(self, text: str) -> None:
        """Speak text using Piper. Falls back to EdgeTTS if unavailable."""
        if not text.strip():
            return

        clean = clean_text(text)
        log.info(f"TTS (Piper): {clean[:60]}...")

        if not self._available:
            # Fallback
            EdgeTTS().speak(clean)
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            filename = tmp.name

        try:
            proc = subprocess.run(
                [
                    "piper",
                    "--model", self._model_path,
                    "--output_file", filename,
                ],
                input=clean.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Piper exit {proc.returncode}: {proc.stderr.decode()}")

            self._play_file(filename)

        except Exception as exc:
            log.error(f"PiperTTS error: {exc}", exc_info=True)
            # Fallback to EdgeTTS
            try:
                os.remove(filename)
            except Exception:
                pass
            EdgeTTS().speak(clean)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_tts(engine: Optional[str] = None) -> BaseTTS:
    """
    Create a TTS engine based on configuration.

    Parameters
    ----------
    engine:
        ``"edge"`` or ``"piper"``. Defaults to ``TTS_ENGINE`` from config.

    Returns
    -------
    BaseTTS
        Configured TTS engine instance.
    """
    selected = (engine or TTS_ENGINE).lower().strip()

    if selected == "piper":
        return PiperTTS()
    else:
        return EdgeTTS()


# ── Default Instance ──────────────────────────────────────────────────────────
# For backward compatibility: `from speech.tts import TTS`

class TTS(BaseTTS):
    """
    Backward-compatible TTS wrapper.

    Automatically selects EdgeTTS or PiperTTS based on config.
    """

    def __init__(self) -> None:
        super().__init__()
        self._engine = create_tts()

    def speak(self, text: str) -> None:
        self._engine.speak(text)

    def stop(self) -> None:
        self._engine.stop()

    def is_speaking(self) -> bool:
        return self._engine.is_speaking()

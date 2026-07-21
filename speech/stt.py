"""
GreetBot Speech-to-Text
========================
Whisper-based STT with language configuration and improved error handling.
Transcribes audio files captured by the Microphone module.
"""

import os
from typing import Optional

from config import STT_MODEL
from utils.logger import get_logger

log = get_logger(__name__)


class STT:
    """
    Whisper speech recognition.

    Loads the Whisper model once on init (can take a few seconds on RPi).
    Transcribe audio files recorded by the Microphone module.

    Parameters
    ----------
    model_size:
        Whisper model variant: ``"tiny"``, ``"base"``, ``"small"``,
        ``"medium"``, or ``"large"``.
        Larger models are more accurate but slower and use more RAM.
    language:
        BCP-47 language code (``"en"`` for English).
        Set to ``None`` for automatic language detection.
    """

    def __init__(
        self,
        model_size: str = STT_MODEL,
        language: str = "en",
    ) -> None:
        self._language = language

        log.info(f"Loading Whisper model: {model_size}...")
        try:
            import whisper
            self._model = whisper.load_model(model_size)
            log.info(f"Whisper {model_size!r} ready")
        except Exception as exc:
            log.error(f"Failed to load Whisper: {exc}", exc_info=True)
            raise

    def transcribe(self, filename: str) -> str:
        """
        Transcribe an audio file to text.

        Parameters
        ----------
        filename:
            Path to the audio file (WAV format).

        Returns
        -------
        str
            Transcribed text, stripped of leading/trailing whitespace.
            Empty string if transcription failed or produced no output.
        """
        if not os.path.exists(filename):
            log.warning(f"Audio file not found: {filename}")
            return ""

        if os.path.getsize(filename) < 1000:
            log.debug("Audio file too small — likely silence")
            return ""

        try:
            result = self._model.transcribe(
                filename,
                language=self._language,
                fp16=False,     # FP16 not available on CPU (RPi)
                verbose=False,
            )
            text = result.get("text", "").strip()
            log.info(f"STT: {text!r}")
            return text

        except Exception as exc:
            log.error(f"Whisper transcription error: {exc}", exc_info=True)
            return ""

    def set_language(self, language: Optional[str]) -> None:
        """
        Change the recognition language.

        Parameters
        ----------
        language:
            BCP-47 code (e.g. ``"en"``, ``"hi"``), or None for auto-detect.
        """
        self._language = language
        log.info(f"STT language set to: {language or 'auto'}")

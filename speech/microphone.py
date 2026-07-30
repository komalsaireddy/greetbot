import queue
import time
import os

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad

from config import (
    AUDIO_QUEUE_MAX_FRAMES,
    LISTEN_TIMEOUT_SECONDS,
    MAX_RECORDING_SECONDS,
)
from utils.logger import get_logger

log = get_logger(__name__)


class Microphone:

    def __init__(self):

        self.sample_rate = 16000
        self.channels = 1
        self.frame_duration = 30

        self.frame_size = int(
            self.sample_rate * self.frame_duration / 1000
        )

        self.vad = webrtcvad.Vad(2)

        # Initialize openwakeword model
        try:
            from openwakeword.model import Model
            # hey_jarvis is one of the built-in default models in openwakeword
            self.oww_model = Model(wakeword_models=["hey_jarvis"])
        except Exception as e:
            log.warning(f"Could not load openwakeword model: {e}")
            self.oww_model = None

        # Keep a finite amount of audio while STT/TTS is busy.  An unbounded
        # queue grows forever when the bot is speaking or the network is slow.
        self.queue: queue.Queue[np.ndarray | None] = queue.Queue(
            maxsize=AUDIO_QUEUE_MAX_FRAMES
        )

        self.running = False
        self.stream = None

    def _callback(self, indata, frames, t, status):
        if status:
            log.warning("Microphone status: %s", status)
        try:
            self.queue.put_nowait(indata.copy())
        except queue.Full:
            # Discard the oldest frame so newly spoken audio is always fresh.
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(indata.copy())
            except queue.Empty:
                pass

    def start(self):
        if self.running:
            return

        self.running = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.frame_size,
            callback=self._callback,
        )
        self.stream.start()

    def stop(self):
        self.running = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        # Wake a listening thread so shutdown does not wait for speech.
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            pass

    def flush(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    def wait_for_wakeword(self) -> bool:
        """
        Blocks until the wake word is detected in the audio stream.
        Returns True if detected, False if stopped.
        """
        if not self.oww_model:
            log.warning("Wake word model not loaded, skipping wake word detection.")
            return True

        log.info("Waiting for wake word: 'Hey Jarvis'...")
        while self.running:
            try:
                data = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if data is None:
                return False

            prediction = self.oww_model.predict(data.flatten())
            for mdl in self.oww_model.prediction_buffer.keys():
                if prediction[mdl] >= 0.5:
                    log.info(f"Wake word '{mdl}' detected!")
                    return True
        return False

    def listen(
        self,
        filename: str,
        listen_timeout: float = LISTEN_TIMEOUT_SECONDS,
        max_recording_seconds: float = MAX_RECORDING_SECONDS,
    ) -> str | None:
        """
        Listen for speech using VAD and save it to a file.
        Returns the filename if speech was captured, or None if timed out.
        """
        self.flush()

        frames = []
        speech_started = False
        silence_frames = 0

        started_at = time.monotonic()
        while self.running:
            elapsed = time.monotonic() - started_at
            if not speech_started and listen_timeout > 0 and elapsed >= listen_timeout:
                log.debug("Listening timed out without speech")
                return None
            if speech_started and max_recording_seconds > 0 and elapsed >= max_recording_seconds:
                log.warning("Recording reached maximum duration")
                break

            try:
                data = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if data is None:
                return None

            pcm = data.tobytes()
            speech = self.vad.is_speech(pcm, self.sample_rate)

            if speech:
                speech_started = True
                silence_frames = 0
                frames.append(data)
            elif speech_started:
                frames.append(data)
                silence_frames += 1

            if speech_started and silence_frames > 20:
                break

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)
        sf.write(filename, audio, self.sample_rate)
        print("✅ Recording Complete")
        return filename

    def record(self, filename="input.wav"):
        self.start()
        try:
            return self.listen(filename)
        finally:
            self.stop()

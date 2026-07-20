import queue

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad


class Microphone:

    def __init__(self):

        self.sample_rate = 16000
        self.channels = 1
        self.frame_duration = 30

        self.frame_size = int(
            self.sample_rate * self.frame_duration / 1000
        )

        self.vad = webrtcvad.Vad(2)

        self.queue = queue.Queue()

        self.running = False

        self.stream = None

    def _callback(self, indata, frames, t, status):

        self.queue.put(indata.copy())

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

    def flush(self):

        while not self.queue.empty():

            try:
                self.queue.get_nowait()

            except queue.Empty:
                break

    def listen(self, filename="input.wav"):

        self.flush()

        print("\n🎤 Listening...")

        frames = []

        speech_started = False

        silence_frames = 0

        while True:

            data = self.queue.get()

            pcm = data.tobytes()

            speech = self.vad.is_speech(
                pcm,
                self.sample_rate
            )

            if speech:

                speech_started = True

                silence_frames = 0

                frames.append(data)

            elif speech_started:

                frames.append(data)

                silence_frames += 1

            if speech_started and silence_frames > 20:
                break

        audio = np.concatenate(frames, axis=0)

        sf.write(
            filename,
            audio,
            self.sample_rate
        )

        print("✅ Recording Complete")

        return filename

    def record(self, filename="input.wav"):

        self.start()

        try:

            return self.listen(filename)

        finally:

            self.stop()

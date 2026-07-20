import asyncio
import edge_tts
import os
import subprocess
import tempfile
import threading


class TTS:

    def __init__(self):

        self.voice = "en-US-AndrewNeural"

        self.player = None

        self.lock = threading.Lock()

    async def _generate(self, text, filename):

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate="+5%",
            pitch="+0Hz",
        )

        await communicate.save(filename)

    def speak(self, text):

        print(f"\n🤖 GreetBot: {text}")

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3",
        ) as temp:

            filename = temp.name

        asyncio.run(self._generate(text, filename))

        with self.lock:

            self.player = subprocess.Popen(
                ["mpg123", "-q", filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        self.player.wait()

        with self.lock:

            self.player = None

        try:
            os.remove(filename)
        except Exception:
            pass

    def stop(self):

        with self.lock:

            if self.player is None:
                return

            if self.player.poll() is None:

                self.player.terminate()

                try:
                    self.player.wait(timeout=1)
                except Exception:
                    pass

            self.player = None

    def is_speaking(self):

        with self.lock:

            if self.player is None:
                return False

            return self.player.poll() is None

import whisper


class STT:

    def __init__(self):

        print("Loading Whisper model...")

        self.model = whisper.load_model("base")

    def transcribe(self, filename):

        result = self.model.transcribe(
            filename,
            language="en",
            fp16=False,
        )

        text = result["text"].strip()

        print(f"\n🗣 You: {text}")

        return text

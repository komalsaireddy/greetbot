from speech.microphone import Microphone
from speech.stt import STT

mic = Microphone()
stt = STT()

audio = mic.record()

text = stt.transcribe(audio)

print(text)

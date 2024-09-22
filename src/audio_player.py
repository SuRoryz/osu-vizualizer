import sounddevice as sd
import soundfile as sf
import threading
import glfw  # Import glfw
class AudioPlayer:
    def __init__(self, audio_file):
        print("Audio file:", audio_file)
        self.audio_file = audio_file
        self.duration = 0
        self.start_time = None
        self._thread = None

    def play(self):
        data, fs = sf.read(self.audio_file)
        print(data)
        self.duration = len(data) / fs * 1000  # Duration in milliseconds
        sd.play(data, fs, blocking=False)
        print("Audio file duration:", self.duration, "ms")
        self.start_time = glfw.get_time() * 1000  # Record start time in ms
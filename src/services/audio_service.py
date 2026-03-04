from dataclasses import dataclass
from typing import Optional
import os
import tempfile
from pathlib import Path

# Try importing audio libraries, but don't fail immediately if not installed
# (allows backend to still function without audio capability if misconfigured)
try:
    import sounddevice as sd
    import wavio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


@dataclass
class STTResult:
    """Standardized result from any Speech-to-Text provider."""
    text: str
    confidence: float
    language: Optional[str] = None
    duration: float = 0.0


class AudioRecorder:
    """Handles microphone capture and WAV file creation."""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self._temp_dir = Path(tempfile.gettempdir()) / "language_learning_audio"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._current_recording = None
        self._recording_thread = None

    def start_recording(self) -> None:
        """Start recording indefinitely until stop_recording is called. (Not blocking)"""
        # Note: True asynchronous recording with sounddevice requires an InputStream
        # and a queue or callback, which we'll need if we want start/stop mechanics.
        # For simplicity in many of our features, we might use fixed-duration or
        # specific input stream callbacks.
        if not AUDIO_AVAILABLE:
            raise RuntimeError("Audio libraries (sounddevice, wavio) are not installed.")
            
        import queue
        self.is_recording = True
        self.q = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                print(f"[Audio Error] {status}")
            self.q.put(indata.copy())

        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=callback)
        self.stream.start()

    def stop_recording(self) -> Optional[Path]:
        """Stop current recording and save to a temporary WAV file."""
        if not self.is_recording or not hasattr(self, 'stream'):
            return None

        self.stream.stop()
        self.stream.close()
        self.is_recording = False

        import numpy as np
        audio_data = []
        while not self.q.empty():
            audio_data.append(self.q.get())

        if not audio_data:
            return None

        audio_np = np.concatenate(audio_data, axis=0)
        
        file_path = self._temp_dir / f"recording_{len(list(self._temp_dir.glob('*.wav')))}.wav"
        import wavio
        wavio.write(str(file_path), audio_np, self.sample_rate, sampwidth=2)
        
        return file_path

    def record_for_duration(self, seconds: int) -> Path:
        """Record for a fixed duration (blocking)."""
        if not AUDIO_AVAILABLE:
            raise RuntimeError("Audio libraries (sounddevice, wavio) are not installed.")
            
        print(f"Recording for {seconds} seconds...")
        myrecording = sd.rec(int(seconds * self.sample_rate), samplerate=self.sample_rate, channels=self.channels)
        sd.wait()
        
        file_path = self._temp_dir / f"recording_{len(list(self._temp_dir.glob('*.wav')))}.wav"
        import wavio
        wavio.write(str(file_path), myrecording, self.sample_rate, sampwidth=2)
        
        return file_path

    def cleanup_temp_files(self):
        """Remove all temporary audio files created by this session."""
        for file in self._temp_dir.glob("*.wav"):
            try:
                os.remove(file)
            except Exception as e:
                print(f"[Cleanup Error] {e}")


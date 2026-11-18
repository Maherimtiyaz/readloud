"""The TTS engine layer.

Design note: everything else in the app talks to the small `TTSEngine`
protocol, never to Kokoro directly. That lets us
  * swap in other engines later (Piper for weak PCs, Chatterbox for cloning),
  * use a fast fake engine in unit tests, so tests run in milliseconds
    without downloading a 92 MB model.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .models import ModelPaths, default_paths
from .text import split_sentences

SPEED_MIN, SPEED_MAX = 0.5, 2.0  # Kokoro's sensible range; faster = later via time-stretch


class TTSEngine(Protocol):
    sample_rate: int

    def voices(self) -> list[str]: ...

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> np.ndarray:
        """Return mono float32 audio in [-1, 1] for a short piece of text."""
        ...


class ModelNotFoundError(RuntimeError):
    pass


class KokoroEngine:
    sample_rate = 24_000

    def __init__(self, paths: ModelPaths | None = None, lang: str = "en-us"):
        self.paths = paths or default_paths()
        self.lang = lang
        self._kokoro = None
        self._lock = threading.Lock()

    def _model(self):
        # Lazy-load: the app starts instantly; the model loads on first use.
        with self._lock:
            if self._kokoro is None:
                if not self.paths.exist():
                    raise ModelNotFoundError(
                        f"Model files not found in {self.paths.model.parent}. "
                        "Run `readloud download` first."
                    )
                from kokoro_onnx import Kokoro

                self._kokoro = Kokoro(str(self.paths.model), str(self.paths.voices))
            return self._kokoro

    def voices(self) -> list[str]:
        return sorted(self._model().get_voices())

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> np.ndarray:
        kokoro = self._model()
        if voice not in kokoro.get_voices():
            raise ValueError(f"unknown voice {voice!r}")
        audio, _ = kokoro.create(text, voice=voice, speed=speed, lang=self.lang)
        return np.asarray(audio, dtype=np.float32)


@dataclass
class Segment:
    """One spoken sentence and where it sits in the final audio."""

    index: int
    text: str
    audio: np.ndarray
    start: float  # seconds
    end: float


def speak(
    engine: TTSEngine,
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0,
    pause: float = 0.15,
) -> Iterator[Segment]:
    """Synthesize text sentence by sentence.

    It's a generator, so a caller can start playing sentence 1 while
    sentence 2 is still being generated. That's the key to low latency.
    """
    if not SPEED_MIN <= speed <= SPEED_MAX:
        raise ValueError(f"speed must be between {SPEED_MIN} and {SPEED_MAX}")
    silence = np.zeros(int(pause * engine.sample_rate), dtype=np.float32)
    clock = 0.0
    for i, sentence in enumerate(split_sentences(text)):
        audio = engine.synthesize(sentence, voice, speed)
        audio = np.concatenate([audio, silence])
        duration = len(audio) / engine.sample_rate
        yield Segment(i, sentence, audio, clock, clock + duration)
        clock += duration


def render(engine: TTSEngine, text: str, voice: str = "af_heart", speed: float = 1.0):
    """Synthesize everything; return (audio, segments)."""
    segments = list(speak(engine, text, voice, speed))
    if not segments:
        return np.zeros(0, dtype=np.float32), []
    return np.concatenate([s.audio for s in segments]), segments

import numpy as np
import pytest

from readloud.engine import KokoroEngine


class FakeEngine:
    """Stands in for Kokoro: 0.01 s of quiet tone per character, instantly."""

    sample_rate = 24_000

    def __init__(self):
        self.calls: list[tuple[str, str, float]] = []

    def voices(self):
        return ["af_heart", "am_adam"]

    def synthesize(self, text, voice, speed=1.0):
        if voice not in self.voices():
            raise ValueError(f"unknown voice {voice!r}")
        self.calls.append((text, voice, speed))
        n = int(len(text) * 0.01 * self.sample_rate / speed)
        return (0.1 * np.sin(np.arange(n) / 10)).astype(np.float32)


@pytest.fixture
def fake_engine():
    return FakeEngine()


@pytest.fixture(scope="session")
def real_engine():
    engine = KokoroEngine()
    if not engine.paths.exist():
        pytest.skip("model not downloaded; run `readloud download`")
    return engine

import io

import numpy as np
import pytest
import soundfile as sf

from readloud.audio import encode, format_for_path, to_int16
from readloud.engine import render, speak


def test_speak_yields_sentences_with_contiguous_timings(fake_engine):
    segments = list(speak(fake_engine, "One here. Two here. Three here."))
    assert [s.text for s in segments] == ["One here.", "Two here.", "Three here."]
    assert segments[0].start == 0
    for a, b in zip(segments, segments[1:]):
        assert b.start == pytest.approx(a.end)
    total = sum(len(s.audio) for s in segments) / fake_engine.sample_rate
    assert segments[-1].end == pytest.approx(total)


def test_speak_is_lazy(fake_engine):
    """Streaming: the first sentence is ready before later ones are generated."""
    gen = speak(fake_engine, "First. Second. Third.")
    next(gen)
    assert len(fake_engine.calls) == 1


def test_speed_and_voice_passed_through(fake_engine):
    render(fake_engine, "Hello.", voice="am_adam", speed=1.5)
    assert fake_engine.calls == [("Hello.", "am_adam", 1.5)]


@pytest.mark.parametrize("speed", [0.1, 5.0])
def test_speed_out_of_range_rejected(fake_engine, speed):
    with pytest.raises(ValueError):
        list(speak(fake_engine, "Hi.", speed=speed))


def test_render_empty_text(fake_engine):
    audio, segments = render(fake_engine, "   ")
    assert len(audio) == 0 and segments == []


def test_int16_clips_instead_of_wrapping():
    out = to_int16(np.array([2.0, -2.0, 0.5], dtype=np.float32))
    assert out.tolist() == [32767, -32767, 16383]


def test_wav_roundtrip():
    audio = np.linspace(-0.5, 0.5, 2400, dtype=np.float32)
    data, sr = sf.read(io.BytesIO(encode(audio, 24_000, "wav")))
    assert sr == 24_000 and len(data) == 2400


def test_mp3_has_valid_header():
    data = encode(np.zeros(24_000, dtype=np.float32), 24_000, "mp3")
    assert data[:3] == b"ID3" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0)


def test_format_for_path():
    assert format_for_path("out.MP3") == "mp3"
    with pytest.raises(ValueError):
        format_for_path("out.ogg")

"""Tests against the real Kokoro model. Skipped automatically if it isn't downloaded."""

import json

import numpy as np
import pytest

from readloud import cli
from readloud.engine import render

pytestmark = pytest.mark.integration


def test_real_voices(real_engine):
    voices = real_engine.voices()
    assert "af_heart" in voices and len(voices) > 20


def test_real_synthesis_is_audible_and_plausible_length(real_engine):
    audio, segments = render(real_engine, "Hello. This is a test of local speech.")
    seconds = len(audio) / real_engine.sample_rate
    assert len(segments) == 2
    assert 1.5 < seconds < 8  # ~7 words: a couple of seconds, not silence or garbage
    assert np.abs(audio).max() > 0.05  # not silent
    assert np.abs(audio).max() <= 1.0


def test_speed_makes_audio_shorter(real_engine):
    slow, _ = render(real_engine, "The quick brown fox jumps over the lazy dog.", speed=1.0)
    fast, _ = render(real_engine, "The quick brown fox jumps over the lazy dog.", speed=1.8)
    assert len(fast) < 0.75 * len(slow)


def test_cli_read_end_to_end(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("Chapter one.\n\nIt was a bright cold day. The clocks struck.", encoding="utf-8")
    out, timings = tmp_path / "doc.mp3", tmp_path / "doc.json"
    assert cli.main(["read", str(src), "-o", str(out), "--timings", str(timings)]) == 0
    assert out.stat().st_size > 5_000
    data = json.loads(timings.read_text(encoding="utf-8"))
    assert [d["text"] for d in data] == ["Chapter one.", "It was a bright cold day.", "The clocks struck."]

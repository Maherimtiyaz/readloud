"""Encode raw float audio into files people can play."""

from __future__ import annotations

import io

import lameenc
import numpy as np
import soundfile as sf

FORMATS = {"wav": "audio/wav", "mp3": "audio/mpeg"}


def to_int16(audio: np.ndarray) -> np.ndarray:
    # Clip first: a float sample of 1.2 would otherwise wrap around and click.
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def encode(audio: np.ndarray, sample_rate: int, fmt: str) -> bytes:
    if fmt == "wav":
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()
    if fmt == "mp3":
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(64)  # plenty for speech; ~0.5 MB per minute
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(1)
        encoder.set_quality(2)
        return bytes(encoder.encode(to_int16(audio).tobytes()) + encoder.flush())
    raise ValueError(f"unsupported format {fmt!r}; choose from {sorted(FORMATS)}")


def format_for_path(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext not in FORMATS:
        raise ValueError(f"output must end in .wav or .mp3, got {path!r}")
    return ext

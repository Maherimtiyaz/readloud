"""Local HTTP API.

`POST /v1/audio/speech` follows OpenAI's request shape, so any tool that
already speaks to OpenAI TTS can point at readloud instead and run free and
offline. The desktop UI and browser extension (later phases) will use this
same API.
"""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import __version__
from .audio import FORMATS, encode
from .engine import SPEED_MAX, SPEED_MIN, KokoroEngine, ModelNotFoundError, TTSEngine, render

MAX_INPUT_CHARS = 20_000  # one request = a few minutes of audio; books go through the CLI


class SpeechRequest(BaseModel):
    input: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    voice: str = "af_heart"
    speed: float = Field(1.0, ge=SPEED_MIN, le=SPEED_MAX)
    response_format: Literal["mp3", "wav"] = "mp3"
    model: str = "kokoro"  # accepted for OpenAI compatibility; ignored


def create_app(engine: TTSEngine | None = None) -> FastAPI:
    engine = engine or KokoroEngine()
    app = FastAPI(title="readloud", version=__version__)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/v1/voices")
    def voices():
        try:
            return {"voices": engine.voices()}
        except ModelNotFoundError as e:
            raise HTTPException(503, str(e)) from e

    @app.post("/v1/audio/speech")
    async def speech(req: SpeechRequest):
        try:
            # Synthesis is CPU-heavy; run it off the event loop so the
            # server stays responsive to other requests (like /health).
            audio, segments = await run_in_threadpool(
                render, engine, req.input, req.voice, req.speed
            )
        except ModelNotFoundError as e:
            raise HTTPException(503, str(e)) from e
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        if not segments:
            raise HTTPException(400, "input contains no speakable text")
        body = encode(audio, engine.sample_rate, req.response_format)
        return Response(
            body,
            media_type=FORMATS[req.response_format],
            headers={"X-Audio-Duration": f"{segments[-1].end:.3f}"},
        )

    return app

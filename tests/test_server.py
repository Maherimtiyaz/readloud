import io

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from readloud.server import MAX_INPUT_CHARS, create_app


@pytest.fixture
def client(fake_engine):
    return TestClient(create_app(fake_engine))


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_voices(client):
    assert client.get("/v1/voices").json() == {"voices": ["af_heart", "am_adam"]}


def test_speech_wav(client):
    r = client.post("/v1/audio/speech", json={"input": "Hello world.", "response_format": "wav"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    data, sr = sf.read(io.BytesIO(r.content))
    assert sr == 24_000 and len(data) > 0
    assert float(r.headers["x-audio-duration"]) > 0


def test_speech_defaults_to_mp3_openai_style(client):
    r = client.post("/v1/audio/speech", json={"model": "tts-1", "input": "Hi there.", "voice": "af_heart"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"


@pytest.mark.parametrize(
    "body",
    [
        {"input": ""},
        {"input": "x" * (MAX_INPUT_CHARS + 1)},
        {"input": "Hi.", "speed": 9},
        {"input": "Hi.", "response_format": "ogg"},
    ],
)
def test_speech_validation(client, body):
    assert client.post("/v1/audio/speech", json=body).status_code == 422


def test_unknown_voice_is_400(client):
    r = client.post("/v1/audio/speech", json={"input": "Hi.", "voice": "nope"})
    assert r.status_code == 400 and "unknown voice" in r.json()["detail"]


def test_unspeakable_input_is_400(client):
    assert client.post("/v1/audio/speech", json={"input": "   "}).status_code == 400

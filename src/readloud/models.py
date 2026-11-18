"""Where model files live, and how to fetch them."""

from __future__ import annotations

import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

# int8 quantized model: ~92 MB instead of ~310 MB, near-identical quality,
# and faster on CPU. The right default for a desktop app.
MODEL_FILE = "kokoro-v1.0.int8.onnx"
VOICES_FILE = "voices-v1.0.bin"


@dataclass(frozen=True)
class ModelPaths:
    model: Path
    voices: Path

    def exist(self) -> bool:
        return self.model.is_file() and self.voices.is_file()


def home_dir() -> Path:
    """Data directory. Override with the READLOUD_HOME environment variable."""
    return Path(os.environ.get("READLOUD_HOME", Path.home() / ".readloud"))


def default_paths() -> ModelPaths:
    models = home_dir() / "models"
    return ModelPaths(models / MODEL_FILE, models / VOICES_FILE)


def download(paths: ModelPaths | None = None, force: bool = False) -> ModelPaths:
    paths = paths or default_paths()
    for target in (paths.model, paths.voices):
        if target.is_file() and not force:
            print(f"already present: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        _fetch(f"{_RELEASE}/{target.name}", target)
    return paths


def _fetch(url: str, target: Path) -> None:
    # Download to a temp name first so an interrupted download never
    # leaves a half-written file that looks valid.
    partial = target.with_suffix(target.suffix + ".part")
    print(f"downloading {url}")
    with urllib.request.urlopen(url) as response, open(partial, "wb") as out:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                sys.stdout.write(f"\r  {done / total:6.1%} of {total / 1e6:.0f} MB")
                sys.stdout.flush()
    print()
    partial.replace(target)

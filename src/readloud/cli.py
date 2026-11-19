"""Command-line interface: `readloud <command>`."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__, models
from .audio import encode, format_for_path
from .documents import load_text
from .engine import KokoroEngine, ModelNotFoundError, render, speak


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="readloud", description="Free, offline text-to-speech.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("download", help="download the voice model (~120 MB, once)")
    sub.add_parser("voices", help="list available voices")

    p = sub.add_parser("say", help="speak some text (plays it, or saves with -o)")
    p.add_argument("text")
    _voice_args(p)
    p.add_argument("-o", "--output", help="save to .mp3 or .wav instead of playing")

    p = sub.add_parser("read", help="turn a .txt/.md/.pdf file into an audio file")
    p.add_argument("file")
    p.add_argument("-o", "--output", required=True, help="output .mp3 or .wav")
    p.add_argument("--timings", help="also write sentence timings as JSON (for highlighting)")
    _voice_args(p)

    p = sub.add_parser("serve", help="run the local HTTP API")
    p.add_argument("--host", default="127.0.0.1", help="default: localhost only (safe)")
    p.add_argument("--port", type=int, default=8765)

    p = sub.add_parser("bench", help="measure synthesis speed on this machine")
    _voice_args(p)

    args = parser.parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except ModelNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _voice_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--voice", default="af_heart")
    p.add_argument("--speed", type=float, default=1.0, help="0.5 to 2.0")


def cmd_download(args) -> int:
    paths = models.download()
    print(f"ready: {paths.model.parent}")
    return 0


def cmd_voices(args) -> int:
    for name in KokoroEngine().voices():
        print(name)
    return 0


def cmd_say(args) -> int:
    engine = KokoroEngine()
    if args.output:
        audio, _ = render(engine, args.text, args.voice, args.speed)
        _save(audio, engine.sample_rate, args.output)
        return 0
    try:
        import sounddevice as sd
    except (ImportError, OSError):
        print("error: playback needs `pip install readloud[play]` (or use -o file.mp3)", file=sys.stderr)
        return 1
    # Play each sentence as soon as it's ready: speech starts after the
    # first sentence, not after the whole text.
    for seg in speak(engine, args.text, args.voice, args.speed):
        print(seg.text)
        sd.play(seg.audio, engine.sample_rate)
        sd.wait()
    return 0


def cmd_read(args) -> int:
    format_for_path(args.output)  # fail fast, before minutes of synthesis
    text = load_text(args.file)
    engine = KokoroEngine()
    start = time.perf_counter()
    segments = []
    for seg in speak(engine, text, args.voice, args.speed):
        segments.append(seg)
        print(f"\r  sentence {seg.index + 1}, {seg.end / 60:.1f} min of audio", end="", flush=True)
    print()
    if not segments:
        print("error: no speakable text in file", file=sys.stderr)
        return 1
    import numpy as np

    audio = np.concatenate([s.audio for s in segments])
    _save(audio, engine.sample_rate, args.output)
    if args.timings:
        data = [{"i": s.index, "text": s.text, "start": round(s.start, 3), "end": round(s.end, 3)} for s in segments]
        Path(args.timings).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    took = time.perf_counter() - start
    print(f"done in {took:.1f}s ({segments[-1].end / took:.1f}x faster than real time)")
    return 0


def cmd_serve(args) -> int:
    import uvicorn

    from .server import create_app

    if args.host not in ("127.0.0.1", "localhost"):
        print("warning: the API has no authentication; anyone on your network can use it")
    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def cmd_bench(args) -> int:
    engine = KokoroEngine()
    sample = (
        "Reading should be accessible to everyone. This benchmark measures how quickly "
        "your computer turns text into natural speech, using only the CPU. "
        "A real-time factor below one means audio is generated faster than it plays."
    )
    t = time.perf_counter()
    engine.synthesize("Warm up.", args.voice)
    print(f"model load + warm-up: {time.perf_counter() - t:.2f}s")
    t = time.perf_counter()
    next(speak(engine, sample, args.voice, args.speed))
    print(f"time to first sentence: {time.perf_counter() - t:.2f}s")
    t = time.perf_counter()
    audio, _ = render(engine, sample, args.voice, args.speed)
    took = time.perf_counter() - t
    seconds = len(audio) / engine.sample_rate
    print(f"{seconds:.1f}s of audio in {took:.2f}s  ->  real-time factor {took / seconds:.2f}")
    return 0


def _save(audio, sample_rate: int, output: str) -> None:
    data = encode(audio, sample_rate, format_for_path(output))
    Path(output).write_bytes(data)
    print(f"saved {output} ({len(audio) / sample_rate:.1f}s, {len(data) / 1e6:.2f} MB)")


COMMANDS = {
    "download": cmd_download,
    "voices": cmd_voices,
    "say": cmd_say,
    "read": cmd_read,
    "serve": cmd_serve,
    "bench": cmd_bench,
}

if __name__ == "__main__":
    raise SystemExit(main())

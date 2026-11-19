# readloud

**Free, offline, open-source text-to-speech.** Your documents, read aloud by natural voices that run on your own computer. No account, no subscription, no cloud.

> Status: **Phase 0 (engine spike).** This is a command-line tool and local API. The Windows desktop app comes in a later phase.

## What works today

- 54 natural voices (Kokoro-82M, Apache-2.0), running on a normal CPU, no GPU needed
- Read `.txt`, `.md` and `.pdf` files into `.mp3` or `.wav`
- Sentence timings as JSON, the basis for highlighting text as it's read
- Streaming: speech starts after the first sentence, not after the whole document
- A local HTTP API compatible with OpenAI's `/v1/audio/speech`

Measured on a 4-core cloud CPU: speech starts after **~0.8 s**, and audio is generated **~3x faster than real time**.

## Install (Windows)

1. Install [uv](https://docs.astral.sh/uv/) (it installs Python for you). In PowerShell:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. Get the code and install:
   ```powershell
   git clone <your-repo-url> readloud
   cd readloud
   uv sync --extra play
   ```
3. Download the voice model (~120 MB, once):
   ```powershell
   uv run readloud download
   ```

## Use it

```powershell
uv run readloud say "Hello! I am running entirely on your computer."
uv run readloud read paper.pdf -o paper.mp3 --timings paper.json
uv run readloud voices
uv run readloud say "Faster please." --voice am_adam --speed 1.4
uv run readloud bench
uv run readloud serve        # API on http://127.0.0.1:8765
```

API example:

```powershell
curl.exe http://127.0.0.1:8765/v1/audio/speech -H "content-type: application/json" `
  -d '{\"input\": \"Hello from the API.\", \"voice\": \"af_heart\"}' -o hello.mp3
```

## Develop

```powershell
uv run pytest            # all tests; real-model tests skip if the model isn't downloaded
uv run pytest -m "not integration"   # fast unit tests only
```

## How it's built

```
documents.py  file -> raw text (txt, md, pdf)
text.py       raw text -> clean sentences (fixes PDF line-wraps, hyphenation, abbreviations)
engine.py     sentences -> audio, one at a time (TTSEngine interface; Kokoro behind it)
audio.py      audio -> wav / mp3 bytes
cli.py        the `readloud` command
server.py     the local HTTP API (FastAPI)
```

`engine.py` defines a tiny `TTSEngine` interface. Everything else depends on that interface, not on Kokoro, so engines can be swapped (Piper for slow PCs, Chatterbox for voice cloning) and unit tests can use a fake engine.

## Roadmap

- **Phase 0, engine:** CLI, local API, PDF/text to audio, tests, Windows CI. (done)
- **Phase 1, reader:** EPUB/DOCX/web pages, headings and footnote handling, word-level highlighting, speeds above 2x, chapters in MP3 export
- **Phase 2, desktop app (Windows first):** select text anywhere, press a hotkey and it's read aloud; tray app; OCR for scanned PDFs and screenshots
- **Phase 3, browser extension** talking to the local API
- **Phase 4, more voices and languages,** optional voice cloning, pronunciation dictionary
- **Phase 5,** mobile, plus accessibility testing with real dyslexic and low-vision users

## License

Apache-2.0. The Kokoro model is Apache-2.0 too.

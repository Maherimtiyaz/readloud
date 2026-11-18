"""Turn messy real-world text into clean, speakable sentences.

Why this module matters: TTS quality depends as much on the text you feed
the model as on the model itself. PDFs in particular are full of broken
line-wraps and hyphenated words that sound awful if read verbatim.
"""

from __future__ import annotations

import re

# Words ending in "." that do NOT end a sentence.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
    "e.g", "i.e", "fig", "no", "vol", "approx", "inc", "ltd", "co",
}

# A sentence ends at . ! or ? (optionally followed by quotes/brackets),
# then whitespace, then something that looks like a new sentence.
_SENTENCE_END = re.compile(r"""([.!?]+["')\]]*)\s+(?=["'(\[]?[A-Z0-9])""")

# Soft limit so one sentence never becomes a giant synthesis job.
MAX_CHUNK_CHARS = 400


def normalize(text: str) -> str:
    """Repair common extraction artefacts and collapse whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # "exam-\nple" -> "example" (word hyphenated across a line break)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Blank line = paragraph break; keep it as a sentence boundary marker.
    text = re.sub(r"\n\s*\n+", "   ", text)
    # Single newlines inside a paragraph are just wrapping.
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, each at most MAX_CHUNK_CHARS long."""
    text = normalize(text)
    if not text:
        return []

    sentences: list[str] = []
    for paragraph in text.split(" "):
        sentences.extend(_split_paragraph(paragraph.strip()))

    chunks: list[str] = []
    for sentence in sentences:
        chunks.extend(_split_long(sentence))
    return [c for c in chunks if c]


def _split_paragraph(paragraph: str) -> list[str]:
    if not paragraph:
        return []
    parts: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(paragraph):
        candidate = paragraph[start : match.end(1)]
        last_word = candidate.rstrip(".!?\"')]").rsplit(" ", 1)[-1].lower()
        if match.group(1).startswith(".") and last_word in _ABBREVIATIONS:
            continue  # "Dr. Smith" is not two sentences
        parts.append(candidate.strip())
        start = match.end()
    tail = paragraph[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _split_long(sentence: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    """Break an over-long sentence at the most natural pause we can find."""
    if len(sentence) <= limit:
        return [sentence]
    chunks: list[str] = []
    rest = sentence
    while len(rest) > limit:
        window = rest[:limit]
        cut = max(window.rfind(sep) for sep in (", ", "; ", ": ", " - ", " — "))
        if cut < limit // 3:  # no good punctuation: fall back to a space
            cut = window.rfind(" ")
        if cut <= 0:  # one enormous "word" (a URL, say): hard cut
            cut = limit - 1
        chunks.append(rest[: cut + 1].strip())
        rest = rest[cut + 1 :].strip()
    if rest:
        chunks.append(rest)
    return chunks

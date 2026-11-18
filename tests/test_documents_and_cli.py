import pytest

from readloud import cli
from readloud.documents import load_text


def _make_pdf(path, text: str) -> None:
    """Write a minimal one-page PDF containing `text` (no extra dependency)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


def test_load_txt(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("Hello file.", encoding="utf-8")
    assert load_text(f) == "Hello file."


def test_load_pdf(tmp_path):
    f = tmp_path / "a.pdf"
    _make_pdf(f, "Hello from a PDF.")
    assert "Hello from a PDF." in load_text(f)


def test_corrupt_pdf_is_a_friendly_error(tmp_path, capsys):
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"<html>not a pdf</html>")
    assert cli.main(["read", str(f), "-o", str(tmp_path / "x.mp3")]) == 1
    assert "not a readable PDF" in capsys.readouterr().err


def test_unsupported_type(tmp_path):
    f = tmp_path / "a.docx"
    f.write_bytes(b"")
    with pytest.raises(ValueError):
        load_text(f)


def test_cli_missing_model_gives_friendly_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("READLOUD_HOME", str(tmp_path))
    assert cli.main(["voices"]) == 2
    assert "readloud download" in capsys.readouterr().err


def test_cli_rejects_bad_output_before_working(tmp_path, capsys):
    f = tmp_path / "a.txt"
    f.write_text("Hi.", encoding="utf-8")
    assert cli.main(["read", str(f), "-o", str(tmp_path / "out.ogg")]) == 1
    assert ".wav or .mp3" in capsys.readouterr().err

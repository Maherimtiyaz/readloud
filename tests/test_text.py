from readloud.text import MAX_CHUNK_CHARS, normalize, split_sentences


def test_basic_split():
    assert split_sentences("Hello there. How are you? Great!") == [
        "Hello there.",
        "How are you?",
        "Great!",
    ]


def test_abbreviations_do_not_split():
    assert split_sentences("Dr. Smith met Mr. Jones. They talked.") == [
        "Dr. Smith met Mr. Jones.",
        "They talked.",
    ]


def test_decimals_do_not_split():
    assert split_sentences("Pi is 3.14 roughly. Yes.") == ["Pi is 3.14 roughly.", "Yes."]


def test_pdf_hyphenation_and_wrapping_repaired():
    assert normalize("an exam-\nple of wrapped\ntext") == "an example of wrapped text"


def test_paragraph_break_is_a_boundary_even_without_punctuation():
    assert split_sentences("Chapter One\n\nIt was dark.") == ["Chapter One", "It was dark."]


def test_quotes_after_period():
    assert split_sentences('He said "stop." Then left.') == ['He said "stop."', "Then left."]


def test_long_sentence_is_chunked_at_commas():
    sentence = ", ".join(["a fairly long clause of words"] * 40) + "."
    chunks = split_sentences(sentence)
    assert len(chunks) > 1
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)
    assert " ".join(chunks).replace("  ", " ") == sentence


def test_giant_word_is_hard_cut():
    chunks = split_sentences("x" * 1000)
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)
    assert "".join(chunks) == "x" * 1000


def test_empty_and_whitespace():
    assert split_sentences("") == []
    assert split_sentences("   \n\n  ") == []


def test_windows_line_endings():
    assert split_sentences("One.\r\nTwo.") == ["One.", "Two."]

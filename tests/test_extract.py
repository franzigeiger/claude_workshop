from paperclaw.ingest.extract import _is_usable


def test_empty_string_is_not_usable() -> None:
    assert not _is_usable("")


def test_short_text_is_not_usable() -> None:
    assert not _is_usable("too short")


def test_just_below_threshold_is_not_usable() -> None:
    assert not _is_usable("a" * 99)


def test_at_threshold_is_usable() -> None:
    assert _is_usable("a" * 100)


def test_normal_text_is_usable() -> None:
    text = "This is a perfectly normal document sentence. " * 5
    assert _is_usable(text)


def test_mostly_null_bytes_is_not_usable() -> None:
    garbage = "\x00\x01\x02\x03" * 50
    assert not _is_usable(garbage)


def test_mixed_printable_below_ratio_is_not_usable() -> None:
    # 20% printable, 80% non-printable — below the 0.8 threshold
    text = "a" * 20 + "\x00" * 80
    assert not _is_usable(text)


def test_mixed_printable_at_ratio_is_usable() -> None:
    # exactly 80% printable (100 chars minimum met)
    text = "a" * 80 + "\x00" * 20
    assert _is_usable(text)

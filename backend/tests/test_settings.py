"""Configuration tests."""

from pydantic import ValidationError

from app.core.config import Settings


def test_settings_exposes_upload_size_in_bytes() -> None:
    settings = Settings(max_upload_size_mb=10)

    assert settings.max_upload_size_bytes == 10 * 1024 * 1024


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    try:
        Settings(chunk_size=500, chunk_overlap=500)
    except ValidationError as exc:
        assert "CHUNK_OVERLAP must be smaller than CHUNK_SIZE" in str(exc)
    else:
        raise AssertionError("Expected settings validation to fail")

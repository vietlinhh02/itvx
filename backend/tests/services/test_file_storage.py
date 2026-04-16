"""File storage service tests."""

from pathlib import Path

from src.services.file_storage import StoredFile, store_upload_file


def test_store_upload_file_writes_bytes(tmp_path: Path) -> None:
    """Stored uploads should preserve the original file bytes."""
    stored = store_upload_file(
        upload_dir=tmp_path,
        file_name="jd.pdf",
        file_bytes=b"pdf-content",
    )

    assert isinstance(stored, StoredFile)
    assert stored.file_name == "jd.pdf"
    assert Path(stored.storage_path).read_bytes() == b"pdf-content"


def test_store_upload_file_sanitizes_spaces(tmp_path: Path) -> None:
    """Stored upload paths should normalize spaces in file names."""
    stored = store_upload_file(
        upload_dir=tmp_path,
        file_name="Senior Backend JD.pdf",
        file_bytes=b"content",
    )

    assert " " not in Path(stored.storage_path).name


def test_store_upload_file_sanitizes_unsafe_filename_characters(tmp_path: Path) -> None:
    """Stored upload paths should deterministically strip unsafe filename content."""
    stored = store_upload_file(
        upload_dir=tmp_path,
        file_name=" ../Senior:Backend/JD?.pdf ",
        file_bytes=b"content",
    )

    stored_name = Path(stored.storage_path).name

    assert ".." not in stored_name
    assert "/" not in stored_name
    assert ":" not in stored_name
    assert "?" not in stored_name

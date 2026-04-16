"""File storage helpers for uploaded JD documents."""

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredFile:
    """Metadata for a stored file."""

    file_name: str
    storage_path: str


_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_file_name(file_name: str) -> str:
    """Return a deterministic basename safe to use on local storage."""
    base_name = Path(file_name.strip() or "uploaded.jd").name
    normalized = _UNSAFE_FILENAME_CHARS.sub("_", base_name)
    collapsed = normalized.strip("._")
    return collapsed or "uploaded.jd"


def store_upload_file(upload_dir: Path, file_name: str, file_bytes: bytes) -> StoredFile:
    """Store uploaded bytes on disk and return metadata."""
    safe_name = sanitize_file_name(file_name)
    upload_dir.mkdir(parents=True, exist_ok=True)

    destination_path = upload_dir / f"{uuid4()}_{safe_name}"
    _ = destination_path.write_bytes(file_bytes)

    return StoredFile(file_name=file_name, storage_path=str(destination_path))

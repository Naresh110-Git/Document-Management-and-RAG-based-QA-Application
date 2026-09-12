"""Storage helpers for uploaded files."""

import io
import asyncio
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
from typing import Tuple

from fastapi import UploadFile

from app.core.config import Settings


class StorageError(Exception):
    pass


class StorageService:
    """Responsible for saving and deleting uploaded files on disk."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_dir = settings.upload_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, owner_id: str, upload: UploadFile) -> Tuple[str, Path, int, str]:
        """Save an UploadFile to disk and return (stored_filename, path, size, sha256_hex)."""
        data = await upload.read()

        # validate size
        if len(data) > self.settings.max_upload_size_bytes:
            raise StorageError("Uploaded file exceeds maximum allowed size")

        ext = Path(upload.filename).suffix or ""
        stored_filename = f"{uuid4().hex}{ext}"
        owner_dir = self.base_dir / str(owner_id)
        owner_dir.mkdir(parents=True, exist_ok=True)
        path = owner_dir / stored_filename

        # write file in a thread to avoid blocking
        await asyncio.to_thread(path.write_bytes, data)

        checksum = sha256(data).hexdigest()
        size = path.stat().st_size

        return stored_filename, path, size, checksum

    async def delete_file(self, stored_path: Path) -> None:
        try:
            await asyncio.to_thread(stored_path.unlink)
        except FileNotFoundError:
            return

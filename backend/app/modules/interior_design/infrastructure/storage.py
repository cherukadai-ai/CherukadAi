"""Private, organisation-namespaced asset storage for the design studio."""
from __future__ import annotations

import os
from pathlib import Path
import uuid

from fastapi import UploadFile

from app.core.config import get_settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024


class PrivateAssetStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(os.getenv("CHERUKADAI_STORAGE_ROOT", ".storage"))

    def _path(self, organisation_id: uuid.UUID, project_id: uuid.UUID, key: str) -> Path:
        path = self.root / str(organisation_id) / str(project_id) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def save_upload(self, upload: UploadFile, organisation_id: uuid.UUID, project_id: uuid.UUID) -> tuple[str, int]:
        if upload.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Only JPEG, PNG, and WebP images are supported.")
        key = f"originals/{uuid.uuid4().hex}"
        path = self._path(organisation_id, project_id, key)
        size = 0
        try:
            with path.open("xb") as target:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        raise ValueError("Image exceeds the 25 MB limit.")
                    target.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return key, size

    def save_generated(self, data: bytes, organisation_id: uuid.UUID, project_id: uuid.UUID) -> tuple[str, int]:
        key = f"generated/{uuid.uuid4().hex}.png"
        path = self._path(organisation_id, project_id, key)
        with path.open("xb") as target:
            target.write(data)
        return key, len(data)

    def read(self, organisation_id: uuid.UUID, project_id: uuid.UUID, key: str) -> bytes:
        safe_key = Path(key)
        if safe_key.is_absolute() or ".." in safe_key.parts:
            raise ValueError("Invalid asset key.")
        return self._path(organisation_id, project_id, key).read_bytes()

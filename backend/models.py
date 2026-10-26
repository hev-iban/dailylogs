"""Data shapes and constants for the logs API."""
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, StringConstraints

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UPLOADS_DIR = PROJECT_ROOT / "uploads"
# Prefix of the photo paths stored in the DB and returned to clients.
UPLOADS_URL_PREFIX = "uploads"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

MIN_PHOTOS = 1
MAX_PHOTOS = 5
MAX_PHOTO_BYTES = 5 * 1024 * 1024
# Counted in characters (code points) after trimming; the minimum is 1 (non-blank).
MAX_DESCRIPTION_CHARS = 200
# GET /api/logs page size: used when no limit is given; larger limits are clamped.
DEFAULT_LIST_LIMIT = 5
MAX_LIST_LIMIT = 20
# GET /api/logs offset: >= 0 and at most the PostgreSQL bigint maximum (larger is 422).
MAX_LIST_OFFSET = 2**63 - 1
# 5 photos x 5 MiB plus 1 MiB for multipart framing and the description.
MAX_REQUEST_BYTES = MAX_PHOTOS * MAX_PHOTO_BYTES + 1024 * 1024

ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
# Pillow format name -> extension used for the stored file.
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


class LogOut(BaseModel):
    id: int
    description: str
    photos: list[str]
    created_at: str
    updated_at: str


class DescriptionIn(BaseModel):
    """Description rules: a real string, trimmed first, then 1..MAX_DESCRIPTION_CHARS code points."""
    description: Annotated[str, StringConstraints(
        strict=True, strip_whitespace=True,
        min_length=1, max_length=MAX_DESCRIPTION_CHARS)]

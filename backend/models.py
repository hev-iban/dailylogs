"""Data shapes and constants for the logs API."""
from pathlib import Path

from pydantic import BaseModel

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

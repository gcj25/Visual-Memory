"""Upload validation and decoding. Original bytes are never modified; ids are content-derived."""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from config import Settings

_MAGIC = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"BM", "bmp"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
)
_EXT = {"jpeg": "jpg", "png": "png", "bmp": "bmp", "tiff": "tiff", "webp": "webp"}


class ImageValidationError(ValueError):
    """Raised for unusable uploads. ``status_code`` maps to the HTTP response."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class LoadedImage:
    image_id: str
    filename: str
    bgr: np.ndarray
    width: int
    height: int
    sha256: str
    fmt: str
    size_bytes: int
    raw: bytes

    @property
    def extension(self) -> str:
        return _EXT[self.fmt]

    def meta(self) -> dict:
        return {"image_id": self.image_id, "filename": self.filename, "width": self.width,
                "height": self.height, "sha256": self.sha256, "format": self.fmt, "size_bytes": self.size_bytes}


def _sniff(data: bytes) -> str | None:
    for magic, name in _MAGIC:
        if data.startswith(magic):
            return name
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def decode_upload(data: bytes, filename: str, settings: Settings) -> LoadedImage:
    label = (filename or "upload")[:80]
    if not data:
        raise ImageValidationError(f"'{label}' is empty")
    if len(data) > settings.max_upload_bytes:
        raise ImageValidationError(
            f"'{label}' exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB upload limit", 413)
    fmt = _sniff(data)
    if fmt is None:
        raise ImageValidationError(f"'{label}' is not a supported image type (JPEG, PNG, BMP, TIFF, WEBP)", 415)
    # Header-only size check first, to refuse decompression bombs before decoding pixels.
    try:
        with Image.open(io.BytesIO(data)) as im:
            w0, h0 = im.size
    except Exception as e:  # noqa: BLE001
        raise ImageValidationError(f"'{label}' is corrupted or unreadable ({type(e).__name__})") from e
    if w0 * h0 > settings.max_pixels:
        raise ImageValidationError(f"'{label}' has too many pixels ({w0}x{h0})", 413)
    arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)  # applies EXIF orientation
    if arr is None or arr.size == 0:
        raise ImageValidationError(f"'{label}' could not be decoded (corrupted image data)")
    h, w = arr.shape[:2]
    if min(w, h) < settings.min_dimension or max(w, h) > settings.max_dimension:
        raise ImageValidationError(
            f"'{label}' is {w}x{h}; sides must be between {settings.min_dimension} and {settings.max_dimension} px")
    sha = hashlib.sha256(data).hexdigest()
    return LoadedImage(image_id=f"img_{sha[:12]}", filename=label, bgr=arr, width=w, height=h,
                       sha256=sha, fmt=fmt, size_bytes=len(data), raw=data)

"""Download map images via the IIIF Image API."""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from unimap.config import DOWNLOAD_TIMEOUT, IMAGES_DIR, MAX_IMAGE_WIDTH
from unimap.harvest.models import MapRecord

logger = logging.getLogger(__name__)


def _image_download_url(record: MapRecord, max_width: int = MAX_IMAGE_WIDTH) -> str:
    base = record.iiif_image_service_url.rstrip("/")
    if record.source == "rumsey":
        return f"{base}/full/!{max_width},{max_width}/0/default.jpg"
    else:
        return f"{base}/full/{max_width},/0/default.jpg"


def download_image(record: MapRecord, max_width: int = MAX_IMAGE_WIDTH) -> Path:
    """Download a map image via IIIF. Returns path to the saved JPEG. Skips if exists."""
    out_dir = IMAGES_DIR / record.source
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{record.slug}.jpg"

    if out_path.exists():
        logger.info("Already downloaded: %s", out_path)
        return out_path

    url = _image_download_url(record, max_width)
    logger.info("Downloading %s -> %s", url, out_path)

    with httpx.Client(follow_redirects=True) as client:
        with client.stream("GET", url, timeout=DOWNLOAD_TIMEOUT) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    logger.info("Downloaded %s (%d bytes)", out_path, out_path.stat().st_size)
    return out_path


def download_all(
    records: list[MapRecord], max_width: int = MAX_IMAGE_WIDTH
) -> dict[str, Path]:
    """Download images for all records. Returns {slug: image_path}."""
    results: dict[str, Path] = {}
    for record in records:
        try:
            path = download_image(record, max_width)
            results[record.slug] = path
        except httpx.HTTPError as exc:
            logger.error("Failed to download %s: %s", record.slug, exc)
    return results

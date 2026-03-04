"""Shared IIIF manifest parsing utilities."""
from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)


def parse_iiif_manifest(client: httpx.Client, manifest_url: str) -> dict | None:
    """Fetch and parse an IIIF manifest (v2 or v3) to extract canvas + image info.

    Returns dict with keys: canvas_id, canvas_width, canvas_height, image_service_url, title
    or None on failure.
    """
    try:
        resp = client.get(manifest_url, timeout=30)
        resp.raise_for_status()
        manifest = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None

    title = _extract_title(manifest)

    # IIIF v3
    if "items" in manifest:
        result = _parse_v3(manifest)
        if result:
            result["title"] = title
        return result

    # IIIF v2
    if "sequences" in manifest:
        result = _parse_v2(manifest)
        if result:
            result["title"] = title
        return result

    return None


def _extract_title(manifest: dict) -> str:
    label = manifest.get("label")
    # v3: label is {"en": ["Some title"]}
    if isinstance(label, dict):
        for lang_vals in label.values():
            if isinstance(lang_vals, list) and lang_vals:
                return lang_vals[0]
    # v2: label is a string
    if isinstance(label, str):
        return label
    return "Untitled"


def _parse_v3(manifest: dict) -> dict | None:
    try:
        canvas = manifest["items"][0]
        anno_page = canvas["items"][0]
        anno = anno_page["items"][0]
        body = anno["body"]
        service = body.get("service", [{}])
        if isinstance(service, list):
            service = service[0]
        return {
            "canvas_id": canvas["id"],
            "canvas_width": canvas["width"],
            "canvas_height": canvas["height"],
            "image_service_url": service.get("id") or service.get("@id", ""),
        }
    except (KeyError, IndexError):
        return None


def _parse_v2(manifest: dict) -> dict | None:
    try:
        canvas = manifest["sequences"][0]["canvases"][0]
        image = canvas["images"][0]
        service = image["resource"].get("service", {})
        return {
            "canvas_id": canvas["@id"],
            "canvas_width": canvas["width"],
            "canvas_height": canvas["height"],
            "image_service_url": service.get("@id", ""),
        }
    except (KeyError, IndexError):
        return None

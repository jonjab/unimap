"""David Rumsey Map Collection harvester."""
from __future__ import annotations

import json
import logging
import time

import httpx

from unimap.config import RUMSEY_SEARCH_URL
from unimap.harvest.models import MapRecord

logger = logging.getLogger(__name__)


def _search_luna(
    client: httpx.Client, query: str = "map", offset: int = 0, batch_size: int = 10
) -> list[dict]:
    params = {
        "q": query,
        "lc": "RUMSEY~8~1",
        "os": str(offset),
        "bs": str(batch_size),
    }
    resp = client.get(RUMSEY_SEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def _parse_iiif_manifest(client: httpx.Client, manifest_url: str) -> dict | None:
    try:
        resp = client.get(manifest_url, timeout=30)
        resp.raise_for_status()
        manifest = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None

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


def _extract_field(result: dict, field_name: str) -> str:
    for fv in result.get("fieldValues", []):
        if isinstance(fv, dict):
            if field_name in fv:
                val = fv[field_name]
                if isinstance(val, list):
                    return val[0] if val else ""
                return str(val)
    return ""


def harvest(limit: int = 20) -> list[MapRecord]:
    """Harvest up to `limit` map records from the David Rumsey Map Collection."""
    records: list[MapRecord] = []

    with httpx.Client() as client:
        offset = 0
        batch_size = 10

        while len(records) < limit:
            results = _search_luna(client, query="map", offset=offset, batch_size=batch_size)
            if not results:
                break

            for result in results:
                if len(records) >= limit:
                    break

                if result.get("mediaType") != "Image":
                    continue

                manifest_url = result.get("iiifManifest")
                if not manifest_url:
                    continue

                time.sleep(0.3)  # Rate-limit courtesy for Luna API
                iiif_info = _parse_iiif_manifest(client, manifest_url)
                if iiif_info is None:
                    continue

                luna_id = result.get("id", "")
                title = result.get("displayName", "Untitled")

                record = MapRecord(
                    id=luna_id,
                    source="rumsey",
                    title=title,
                    iiif_manifest_url=manifest_url,
                    iiif_image_service_url=iiif_info["image_service_url"],
                    canvas_id=iiif_info["canvas_id"],
                    canvas_width=iiif_info["canvas_width"],
                    canvas_height=iiif_info["canvas_height"],
                    metadata={
                        "creator": _extract_field(result, "Author"),
                        "date": _extract_field(result, "Date"),
                    },
                )
                records.append(record)
                logger.info("Harvested Rumsey map %d/%d: %s", len(records), limit, title)

            offset += batch_size

    return records

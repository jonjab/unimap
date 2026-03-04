"""Stanford Earthworks (OpenGeoMetadata) harvester."""
from __future__ import annotations

import json
import logging

import httpx

from unimap.config import STANFORD_IIIF_REF_KEY, STANFORD_LAYERS_URL, STANFORD_METADATA_BASE
from unimap.harvest.models import MapRecord

logger = logging.getLogger(__name__)


def _druid_to_path(druid: str) -> str:
    """Convert a bare druid like 'bb014tx0752' into 'bb/014/tx/0752'."""
    d = druid.removeprefix("druid:")
    return f"{d[0:2]}/{d[2:5]}/{d[5:7]}/{d[7:11]}"


def _fetch_layers_index(client: httpx.Client) -> dict[str, str]:
    resp = client.get(STANFORD_LAYERS_URL, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _fetch_geoblacklight(client: httpx.Client, metadata_path: str) -> dict | None:
    url = f"{STANFORD_METADATA_BASE}/{metadata_path}/geoblacklight.json"
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
        return None


def _is_map_with_iiif(record: dict) -> bool:
    resource_classes = record.get("gbl_resourceClass_sm", [])
    if "Maps" not in resource_classes:
        return False
    refs_raw = record.get("dct_references_s", "{}")
    if isinstance(refs_raw, str):
        try:
            refs = json.loads(refs_raw)
        except json.JSONDecodeError:
            return False
    else:
        refs = refs_raw
    return STANFORD_IIIF_REF_KEY in refs


def _parse_iiif_manifest(client: httpx.Client, manifest_url: str) -> dict | None:
    """Fetch and parse an IIIF manifest (v2 or v3) to extract canvas + image info."""
    try:
        resp = client.get(manifest_url, timeout=30)
        resp.raise_for_status()
        manifest = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None

    # IIIF v3
    if "items" in manifest:
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

    # IIIF v2
    if "sequences" in manifest:
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

    return None


def harvest(limit: int = 20) -> list[MapRecord]:
    """Harvest up to `limit` map records from Stanford Earthworks."""
    records: list[MapRecord] = []

    with httpx.Client() as client:
        layers = _fetch_layers_index(client)
        logger.info("Loaded %d layer entries from Stanford", len(layers))

        for druid_key, metadata_path in layers.items():
            if len(records) >= limit:
                break

            gb = _fetch_geoblacklight(client, metadata_path)
            if gb is None:
                continue

            if not _is_map_with_iiif(gb):
                continue

            refs_raw = gb.get("dct_references_s", "{}")
            refs = json.loads(refs_raw) if isinstance(refs_raw, str) else refs_raw
            manifest_url = refs[STANFORD_IIIF_REF_KEY]

            iiif_info = _parse_iiif_manifest(client, manifest_url)
            if iiif_info is None:
                logger.debug("Could not parse IIIF manifest for %s", druid_key)
                continue

            druid = druid_key.removeprefix("druid:")
            title = gb.get("dct_title_s", "Untitled")

            creators = gb.get("dct_creator_sm", ["Unknown"])
            descriptions = gb.get("dct_description_sm", [""])

            record = MapRecord(
                id=druid,
                source="stanford",
                title=title,
                iiif_manifest_url=manifest_url,
                iiif_image_service_url=iiif_info["image_service_url"],
                canvas_id=iiif_info["canvas_id"],
                canvas_width=iiif_info["canvas_width"],
                canvas_height=iiif_info["canvas_height"],
                metadata={
                    "creator": creators[0] if creators else "Unknown",
                    "date": gb.get("dct_issued_s", ""),
                    "description": descriptions[0] if descriptions else "",
                },
            )
            records.append(record)
            logger.info("Harvested Stanford map %d/%d: %s", len(records), limit, title)

    return records

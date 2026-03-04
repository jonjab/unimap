"""GeoJSON output for OCR results."""
from __future__ import annotations

import json
from pathlib import Path

from unimap.config import GEOJSON_DIR
from unimap.harvest.models import MapRecord
from unimap.ocr.models import MapOCRResult


def ocr_result_to_geojson(record: MapRecord, result: MapOCRResult) -> dict:
    """Convert OCR results to a GeoJSON FeatureCollection in IIIF canvas pixel coords."""
    features = []

    for det in result.detections:
        canvas_bbox = result.to_canvas_coords(det)
        ring = canvas_bbox + [canvas_bbox[0]]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
            "properties": {
                "text": det.text,
                "confidence": round(det.confidence, 4),
                "map_id": record.id,
                "map_source": record.source,
                "map_title": record.title,
            },
        })

    return {
        "type": "FeatureCollection",
        "properties": {
            "coordinate_system": "iiif_canvas_pixels",
            "canvas_id": record.canvas_id,
            "canvas_width": record.canvas_width,
            "canvas_height": record.canvas_height,
            "iiif_manifest": record.iiif_manifest_url,
            "map_id": record.id,
            "map_source": record.source,
            "map_title": record.title,
            "total_detections": len(result.detections),
            "metadata": record.metadata,
        },
        "features": features,
    }


def write_geojson(record: MapRecord, result: MapOCRResult) -> Path:
    GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GEOJSON_DIR / f"{result.map_slug}.geojson"

    geojson = ocr_result_to_geojson(record, result)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)

    return out_path

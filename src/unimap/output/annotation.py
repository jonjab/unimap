"""W3C Web Annotation JSON-LD output for IIIF canvases."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from unimap.config import ANNOTATIONS_DIR
from unimap.harvest.models import MapRecord
from unimap.ocr.models import MapOCRResult, TextDetection


def _detection_to_annotation(
    record: MapRecord,
    result: MapOCRResult,
    det: TextDetection,
) -> dict:
    """Convert a TextDetection to a W3C Web Annotation on a IIIF canvas."""
    canvas_bbox = result.to_canvas_coords(det)

    xs = [pt[0] for pt in canvas_bbox]
    ys = [pt[1] for pt in canvas_bbox]
    x = int(min(xs))
    y = int(min(ys))
    w = int(max(xs) - min(xs))
    h = int(max(ys) - min(ys))

    return {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": "Annotation",
        "motivation": "tagging",
        "body": {
            "type": "TextualBody",
            "value": det.text,
            "format": "text/plain",
            "purpose": "tagging",
        },
        "target": {
            "source": record.canvas_id,
            "selector": {
                "type": "FragmentSelector",
                "conformsTo": "http://www.w3.org/TR/media-frags/",
                "value": f"xywh={x},{y},{w},{h}",
            },
        },
        "confidence": round(det.confidence, 4),
    }


def ocr_result_to_annotation_page(record: MapRecord, result: MapOCRResult) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    annotations = []
    for det in result.detections:
        anno = _detection_to_annotation(record, result, det)
        anno["created"] = now
        annotations.append(anno)

    return {
        "@context": [
            "http://www.w3.org/ns/anno.jsonld",
            "http://iiif.io/api/presentation/3/context.json",
        ],
        "id": f"urn:uuid:{uuid.uuid4()}",
        "type": "AnnotationPage",
        "target": record.canvas_id,
        "items": annotations,
        "metadata": {
            "map_id": record.id,
            "map_source": record.source,
            "map_title": record.title,
            "iiif_manifest": record.iiif_manifest_url,
            "total_annotations": len(annotations),
            "generated": now,
            "generator": "unimap",
        },
    }


def write_annotations(record: MapRecord, result: MapOCRResult) -> Path:
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANNOTATIONS_DIR / f"{result.map_slug}.annotations.json"

    page = ocr_result_to_annotation_page(record, result)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(page, f, indent=2, ensure_ascii=False)

    return out_path

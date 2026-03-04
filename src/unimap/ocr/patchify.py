"""Image patching and coordinate stitching for large map images."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

from unimap.config import PATCH_OVERLAP, PATCH_SIZE
from unimap.harvest.models import MapRecord
from unimap.ocr.base import TextSpotter
from unimap.ocr.models import MapOCRResult, TextDetection

logger = logging.getLogger(__name__)


def _generate_patch_coords(
    img_width: int, img_height: int, patch_size: int, overlap: int
) -> list[tuple[int, int, int, int]]:
    """Generate (x_start, y_start, x_end, y_end) for overlapping patches."""
    step = patch_size - overlap
    patches = []
    y = 0
    while y < img_height:
        x = 0
        while x < img_width:
            x_end = min(x + patch_size, img_width)
            y_end = min(y + patch_size, img_height)
            patches.append((x, y, x_end, y_end))
            if x_end == img_width:
                break
            x += step
        if y_end == img_height:
            break
        y += step
    return patches


def _deduplicate_detections(
    detections: list[TextDetection], iou_threshold: float = 0.5
) -> list[TextDetection]:
    """Remove duplicate detections from overlapping patches using IoU + text match."""
    if not detections:
        return []

    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
    keep: list[TextDetection] = []

    for det in sorted_dets:
        is_duplicate = False
        for kept in keep:
            x_overlap = max(0, min(det.x_max, kept.x_max) - max(det.x_min, kept.x_min))
            y_overlap = max(0, min(det.y_max, kept.y_max) - max(det.y_min, kept.y_min))
            intersection = x_overlap * y_overlap

            det_area = (det.x_max - det.x_min) * (det.y_max - det.y_min)
            kept_area = (kept.x_max - kept.x_min) * (kept.y_max - kept.y_min)
            union = det_area + kept_area - intersection

            if union > 0 and (intersection / union) > iou_threshold:
                if det.text.strip().lower() == kept.text.strip().lower():
                    is_duplicate = True
                    break

        if not is_duplicate:
            keep.append(det)

    return keep


def run_ocr_on_map(
    record: MapRecord,
    image_path: Path,
    spotter: TextSpotter,
    patch_size: int = PATCH_SIZE,
    overlap: int = PATCH_OVERLAP,
) -> MapOCRResult:
    """Run the full OCR pipeline on a single map image."""
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)
    img_height, img_width = img_array.shape[:2]

    patch_coords = _generate_patch_coords(img_width, img_height, patch_size, overlap)
    logger.info(
        "Map %s: %dx%d, %d patches (size=%d, overlap=%d)",
        record.slug, img_width, img_height, len(patch_coords), patch_size, overlap,
    )

    all_detections: list[TextDetection] = []

    for x_start, y_start, x_end, y_end in tqdm(
        patch_coords, desc=f"OCR {record.slug}", unit="patch"
    ):
        patch = img_array[y_start:y_end, x_start:x_end]
        patch_bgr = patch[:, :, ::-1].copy()

        patch_detections = spotter.detect(patch_bgr)

        for det in patch_detections:
            translated_bbox = [[pt[0] + x_start, pt[1] + y_start] for pt in det.bbox]
            all_detections.append(
                TextDetection(
                    text=det.text,
                    confidence=det.confidence,
                    bbox=translated_bbox,
                )
            )

    unique_detections = _deduplicate_detections(all_detections)
    logger.info(
        "Map %s: %d raw detections -> %d after dedup",
        record.slug, len(all_detections), len(unique_detections),
    )

    return MapOCRResult(
        map_slug=record.slug,
        image_width=img_width,
        image_height=img_height,
        canvas_width=record.canvas_width,
        canvas_height=record.canvas_height,
        detections=unique_detections,
    )

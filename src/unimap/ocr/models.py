"""Data models for OCR results."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextDetection:
    """A single detected text region in map-level pixel coordinates."""

    text: str
    confidence: float
    bbox: list[list[float]]  # 4 corner points: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    @property
    def x_min(self) -> float:
        return min(pt[0] for pt in self.bbox)

    @property
    def y_min(self) -> float:
        return min(pt[1] for pt in self.bbox)

    @property
    def x_max(self) -> float:
        return max(pt[0] for pt in self.bbox)

    @property
    def y_max(self) -> float:
        return max(pt[1] for pt in self.bbox)


@dataclass
class MapOCRResult:
    """All text detections for a single map."""

    map_slug: str
    image_width: int
    image_height: int
    canvas_width: int
    canvas_height: int
    detections: list[TextDetection]

    def to_canvas_coords(self, det: TextDetection) -> list[list[float]]:
        """Scale a detection's bbox from image coordinates to IIIF canvas coordinates."""
        x_scale = self.canvas_width / self.image_width
        y_scale = self.canvas_height / self.image_height
        return [[pt[0] * x_scale, pt[1] * y_scale] for pt in det.bbox]

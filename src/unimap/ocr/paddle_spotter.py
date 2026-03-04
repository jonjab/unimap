"""PaddleOCR-based text spotter implementation."""
from __future__ import annotations

import logging

import numpy as np

from unimap.config import CONFIDENCE_THRESHOLD, PADDLE_LANG, PADDLE_USE_GPU
from unimap.ocr.models import TextDetection

logger = logging.getLogger(__name__)


class PaddleSpotter:
    """TextSpotter implementation using PaddleOCR (v2.x API)."""

    def __init__(
        self,
        lang: str = PADDLE_LANG,
        use_gpu: bool = PADDLE_USE_GPU,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        from paddleocr import PaddleOCR

        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=use_gpu,
            show_log=False,
        )
        logger.info("PaddleOCR initialized (lang=%s, gpu=%s)", lang, use_gpu)

    def warmup(self) -> None:
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        self._ocr.ocr(dummy, cls=True)
        logger.info("PaddleOCR warmup complete")

    def detect(self, patch: np.ndarray) -> list[TextDetection]:
        results = self._ocr.ocr(patch, cls=True)
        detections: list[TextDetection] = []

        if results is None or len(results) == 0:
            return detections

        for line in results[0] or []:
            bbox_points = line[0]
            text = line[1][0]
            confidence = float(line[1][1])

            if confidence < self.confidence_threshold:
                continue

            detections.append(
                TextDetection(text=text, confidence=confidence, bbox=bbox_points)
            )

        return detections

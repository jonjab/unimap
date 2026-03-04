"""Abstract text spotter protocol."""
from __future__ import annotations

from typing import Protocol

import numpy as np

from unimap.ocr.models import TextDetection


class TextSpotter(Protocol):
    """
    Protocol for text detection and recognition on image patches.

    Implementations:
    - PaddleSpotter: Uses PaddleOCR (CPU-only, current default)
    - SpotterV2:     Uses MapKurator's spotter-v2 (GPU, future)
    """

    def detect(self, patch: np.ndarray) -> list[TextDetection]:
        """Run text detection + recognition on a BGR image patch (H, W, 3)."""
        ...

    def warmup(self) -> None:
        """Optional warmup call to pre-load models."""
        ...

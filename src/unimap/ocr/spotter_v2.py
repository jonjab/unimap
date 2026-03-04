"""MapKurator spotter-v2 implementation stub (requires GPU)."""
from __future__ import annotations

import numpy as np

from unimap.ocr.models import TextDetection


class SpotterV2:
    """
    TextSpotter placeholder for MapKurator's spotter-v2.

    To implement:
    1. Install mapkurator dependencies (requires CUDA GPU).
    2. Load the spotter-v2 model weights in __init__.
    3. Implement detect() to run inference on a patch.

    See: https://github.com/knowledge-computing/mapkurator-spotter
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "SpotterV2 requires GPU and mapkurator dependencies. "
            "See https://github.com/knowledge-computing/mapkurator-system"
        )

    def warmup(self) -> None:
        pass

    def detect(self, patch: np.ndarray) -> list[TextDetection]:
        raise NotImplementedError

"""Data models for harvested map records."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MapRecord:
    """A single harvested map, source-agnostic."""

    id: str
    source: str  # "stanford" or "rumsey"
    title: str
    iiif_manifest_url: str
    iiif_image_service_url: str
    canvas_id: str
    canvas_width: int
    canvas_height: int
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Filesystem-safe identifier: source--id."""
        safe_id = self.id.replace(":", "_").replace("/", "_").replace("~", "_")
        return f"{self.source}--{safe_id}"

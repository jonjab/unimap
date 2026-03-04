"""Abstract harvester protocol."""
from __future__ import annotations

from typing import Protocol

from unimap.harvest.models import MapRecord


class Harvester(Protocol):
    def harvest(self, limit: int = 20) -> list[MapRecord]: ...

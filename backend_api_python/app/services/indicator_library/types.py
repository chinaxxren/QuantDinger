"""Types for the built-in QuantDinger indicator library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class IndicatorSpec:
    """Metadata for one built-in chart indicator."""

    identifier: str
    name: str
    description: str
    category: str
    tags: Tuple[str, ...]
    version: str = "1.0.0"

    @property
    def module_file(self) -> str:
        """Return the canonical one-file implementation name."""
        return f"{self.identifier}.py"

"""Types for the built-in QuantDinger indicator library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class IndicatorSpec:
    """Metadata plus source filename for one built-in chart indicator."""

    identifier: str
    name: str
    description: str
    category: str
    tags: Tuple[str, ...]
    source_file: str
    version: str = "1.0.0"

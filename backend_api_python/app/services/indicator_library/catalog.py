"""Canonical loader for the one-file-per-indicator library.

Every built-in indicator is represented by one module in ``indicators``.
The module may expose a trusted ``compute`` callable, chart source code in
``SOURCE_CODE``, or both.  This is an implementation detail of that module;
callers only ask the catalog for the capability they need.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from pathlib import PurePosixPath
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd


_PACKAGE = "app.services.indicator_library.indicators"


def _validate_identifier(identifier: str) -> str:
    value = str(identifier or "").strip()
    if not value or PurePosixPath(value).name != value or not value.replace("_", "").isalnum():
        raise ValueError("invalid indicator identifier")
    return value


@lru_cache(maxsize=None)
def get_indicator_module(identifier: str) -> Any:
    """Load the canonical module for an indicator ID."""
    return import_module(f"{_PACKAGE}.{_validate_identifier(identifier)}")


@lru_cache(maxsize=None)
def get_indicator_source_code(identifier: str) -> str | None:
    """Return optional chart source code stored in the indicator module."""
    source = getattr(get_indicator_module(identifier), "SOURCE_CODE", None)
    return source if isinstance(source, str) and source.strip() else None


@lru_cache(maxsize=None)
def _compiled_source(identifier: str) -> Any:
    source = get_indicator_source_code(identifier)
    if not source:
        raise ValueError(f"missing source for indicator: {identifier}")
    return compile(source, f"indicator:{identifier}", "exec")


def _execute_source(identifier: str, frame: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    """Execute trusted source kept in an indicator's canonical module."""
    namespace: dict[str, Any] = {
        "df": frame.copy(),
        "params": dict(params),
        "pd": pd,
        "np": np,
        "output": None,
    }
    exec(_compiled_source(identifier), namespace)
    result = namespace.get("output")
    if not isinstance(result, dict):
        raise ValueError("indicator source returned invalid output")
    return result


@lru_cache(maxsize=None)
def get_indicator_compute(identifier: str) -> Callable[..., Any] | None:
    """Return the single calculation entry point for an indicator module.

    Native indicators export ``compute``. Source-backed indicators use the
    same public entry point through the internal source adapter. The caller
    therefore never needs to maintain a second source/calculation registry.
    """
    compute = getattr(get_indicator_module(identifier), "compute", None)
    if callable(compute):
        return compute
    if get_indicator_source_code(identifier) is not None:
        return lambda frame, params: _execute_source(identifier, frame, params)
    return None


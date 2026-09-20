#!/usr/bin/env python3
"""Small, shared runtime configuration parsers for ShortAutoPro.

Environment values are user-editable on Termux. These helpers keep malformed
values from crashing production while enforcing explicit operational bounds.
"""

from __future__ import annotations

import math
import os


def env_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError, OverflowError):
        value = default
    return max(low, min(high, value))


def env_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError, OverflowError):
        value = default
    if not math.isfinite(value):
        value = default
    return max(low, min(high, value))

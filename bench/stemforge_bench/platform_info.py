"""Platform-specific details, kept in one place (DR-0003: isolate platform logic)."""
from __future__ import annotations

import resource
import sys


def maxrss_to_mb(maxrss: int) -> float:
    """`ru_maxrss` is bytes on macOS and KiB on Linux."""
    return maxrss / 1e6 if sys.platform == "darwin" else maxrss / 1e3


def peak_rss_mb() -> float:
    return maxrss_to_mb(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

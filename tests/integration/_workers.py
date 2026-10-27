"""Multiprocessing worker entry points for the concurrency integration test.

Defined at module level, not nested inside the test function, because the
default ``multiprocessing`` start method on macOS and Windows is
``"spawn"``: the child process re-imports the target function by its
dotted path, which only works for a real, importable module-level
function.
"""

from __future__ import annotations

import logging
from pathlib import Path


def log_many(log_path: str, app_name: str, count: int, run_id: str | None) -> None:
    """Configure applog in this (child) process and emit ``count`` records."""
    import applog  # imported here so the child process initializes its own state

    applog.configure(app_name, log_path=Path(log_path), run_id=run_id)
    logger = logging.getLogger(__name__)
    for seq in range(count):
        logger.info("worker message", extra={"seq": seq})

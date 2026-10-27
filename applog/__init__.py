"""applog: a reusable, structured JSON Lines logging module for Python apps.

Call :func:`configure` once at application startup. Every module in the
application (and any libraries it uses) can then log with the standard
``logging.getLogger(__name__)`` pattern, and every event will be written as
a structured JSON Lines record — tagged with the application name and a
correlation run ID — to one centrally configured file that an existing log
forwarder already watches.

Minimal usage::

    import logging
    import applog

    applog.configure("my-app")
    logger = logging.getLogger(__name__)
    logger.info("started", extra={"status": "ok"})

See the package README for configuration options, the multi-module
application pattern, and the concurrency/rotation design.
"""

from __future__ import annotations

import logging

from applog.config import LogConfig, configure, get_config, reset
from applog.context import get_run_id, new_run_id, run_id_context

__all__ = [
    "LogConfig",
    "configure",
    "get_config",
    "get_logger",
    "get_run_id",
    "new_run_id",
    "reset",
    "run_id_context",
]

__version__ = "0.1.0"


def get_logger(name: str | None = None) -> logging.Logger:
    """Return ``logging.getLogger(name)``.

    Pure sugar so a caller can do ``applog.get_logger(__name__)`` right
    after ``import applog`` without a second import — the plain stdlib
    call works identically and is always safe to use instead.
    """
    return logging.getLogger(name)

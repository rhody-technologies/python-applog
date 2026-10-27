"""Logging filter that stamps identity and correlation data onto records."""

from __future__ import annotations

import logging

from applog.context import get_run_id


class ContextFilter(logging.Filter):
    """Attach ``app`` and ``run_id`` attributes to every record it sees.

    Installed on each handler by :func:`applog.configure`, not on loggers,
    so it runs exactly once per emitted record regardless of how many
    loggers in the propagation chain the record passed through.
    """

    def __init__(self, app_name: str) -> None:
        super().__init__()
        self._app_name = app_name

    def filter(self, record: logging.LogRecord) -> bool:
        """Add ``app`` and ``run_id`` to ``record`` and always allow it through."""
        record.app = self._app_name
        record.run_id = get_run_id()
        return True

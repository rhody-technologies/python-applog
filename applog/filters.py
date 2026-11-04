"""Logging filter that stamps identity and correlation data onto records."""

from __future__ import annotations

import logging
import uuid

from applog.context import get_run_id

# Private marker so a caller-supplied ``extra={"log_id": ...}`` can never
# masquerade as the library-generated unique ID.
LOG_ID_STAMP_ATTR = "_applog_log_id"


class ContextFilter(logging.Filter):
    """Attach ``app``, ``run_id`` and ``log_id`` attributes to every record.

    Installed on each handler by :func:`applog.configure`, not on loggers,
    so it runs exactly once per emitted record regardless of how many
    loggers in the propagation chain the record passed through.

    ``log_id`` is a UUID4 hex string unique to each record. Because the same
    filter instance is shared by every handler, a record fanned out to both
    the file and the console is stamped once and carries the same ``log_id``
    in both outputs, which lets the two copies be correlated.
    """

    def __init__(self, app_name: str) -> None:
        super().__init__()
        self._app_name = app_name

    def filter(self, record: logging.LogRecord) -> bool:
        """Add ``app``, ``run_id`` and ``log_id``; always allow the record through."""
        record.app = self._app_name
        record.run_id = get_run_id()
        if not hasattr(record, LOG_ID_STAMP_ATTR):
            setattr(record, LOG_ID_STAMP_ATTR, uuid.uuid4().hex)
        return True

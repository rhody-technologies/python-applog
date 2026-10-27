"""JSON Lines formatter: one structured JSON object per log record."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

# Standard attributes every logging.LogRecord carries, plus the handful of
# pseudo-attributes we compute ourselves. Anything else found on a record
# came from a caller's `extra={...}` and is arbitrary application metadata
# (status, record counts, file names, durations, ...) that belongs in the
# output under "extra" rather than being silently dropped.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "app", "run_id"}


class JsonFormatter(logging.Formatter):
    """Render a :class:`logging.LogRecord` as a single-line JSON object.

    Each call to :meth:`format` returns exactly one line with no embedded
    raw newlines (tracebacks are escaped by ``json.dumps`` like any other
    string), which is what makes the output valid JSON Lines: one
    self-contained JSON value per line, safe to append to and to tail.
    """

    def __init__(self, *, utc: bool = True) -> None:
        super().__init__()
        self._utc = utc

    def format(self, record: logging.LogRecord) -> str:
        """Return ``record`` rendered as a single-line JSON string."""
        payload: dict[str, Any] = {
            "timestamp": self._timestamp(record),
            "level": record.levelname,
            "app": getattr(record, "app", None),
            "run_id": getattr(record, "run_id", None),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "pid": record.process,
            "thread": record.threadName,
        }

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_ATTRS
        }
        if extra:
            payload["extra"] = extra

        if record.exc_info:
            payload["exception"] = self._format_exception(record.exc_info)
        elif record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, ensure_ascii=False)

    def _timestamp(self, record: logging.LogRecord) -> str:
        tz = timezone.utc if self._utc else None
        return datetime.fromtimestamp(record.created, tz=tz).isoformat(timespec="milliseconds")

    @staticmethod
    def _format_exception(exc_info: Any) -> dict[str, Any]:
        exc_type, exc_value, exc_tb = exc_info
        return {
            "type": exc_type.__name__ if exc_type else None,
            "message": str(exc_value) if exc_value is not None else None,
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        }

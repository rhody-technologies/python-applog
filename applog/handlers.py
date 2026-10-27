"""Construction of the shared, concurrency-safe log file handler.

Multiple independent Python processes may log to the same physical file at
once: one centrally configured location per application, watched by an
existing log-shipping forwarder. Two stdlib-only mechanisms make that safe
without adding a dependency:

1. Every record is written with a single ``write()`` followed by an
   immediate ``flush()`` (this is what :class:`logging.StreamHandler.emit`
   already does). The file is opened in append mode, and POSIX guarantees
   that an ``O_APPEND`` write is atomic as long as it fits in one
   ``write(2)`` syscall — in practice, up to ``PIPE_BUF`` (commonly 4096
   bytes on Linux). Concurrent processes therefore cannot interleave
   partial lines; keep individual structured log lines well under that
   size if you expect many concurrent writers.
2. :class:`logging.handlers.WatchedFileHandler` watches the file's inode
   and transparently reopens it if an external tool (``logrotate``, the
   forwarder, an operator) renames or truncates the file out from under
   it. This module deliberately does **not** rotate the file itself —
   having every process in a fleet independently decide "it's time to
   rotate" is exactly the multi-process rotation hazard this design
   avoids. Rotation is infrastructure's job; this module only ever
   appends.
"""

from __future__ import annotations

import logging.handlers
from pathlib import Path


def build_file_handler(path: Path) -> logging.handlers.WatchedFileHandler:
    """Build the shared JSON Lines file handler for ``path``.

    Creates parent directories if they do not already exist and opens the
    target file for append.

    :param path: Physical log file location.
    :return: A configured, unformatted ``WatchedFileHandler`` (callers set
        the formatter and filters).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return logging.handlers.WatchedFileHandler(path, mode="a", encoding="utf-8")

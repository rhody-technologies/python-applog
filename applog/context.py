"""Run-correlation primitives.

A "run ID" ties every log event emitted during one execution of an
application together, even across threads, async tasks, and separate OS
processes that are cooperating on the same unit of work. The default run ID
is generated once at :func:`applog.configure` time and stored as a
process-wide fallback; :func:`run_id_context` lets a thread or async task
temporarily adopt a different run ID (e.g. a worker handling one item of a
batch) without disturbing the parent execution's correlation.
"""

from __future__ import annotations

import contextlib
import contextvars
import uuid
from collections.abc import Iterator

_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("applog_run_id")
_default_run_id: str | None = None


def new_run_id() -> str:
    """Generate a new, effectively-unique run ID (a 32-character hex UUID4)."""
    return uuid.uuid4().hex


def set_default_run_id(run_id: str) -> None:
    """Set the process-wide fallback run ID.

    Called once by :func:`applog.configure`. ``get_run_id`` falls back to
    this value in any thread/task that has not entered a
    :func:`run_id_context` override, which is what makes a single
    ``configure()`` call at startup sufficient for the whole process.
    """
    global _default_run_id
    _default_run_id = run_id


def _clear_default_run_id() -> None:
    """Clear the process-wide fallback run ID.

    Used by :func:`applog.reset`. Not part of the public API — resetting
    correlation state mid-run is a test/REPL concern, not something
    application code should ever need to do.
    """
    global _default_run_id
    _default_run_id = None


def get_run_id() -> str | None:
    """Return the run ID for the current execution context.

    Resolves to the nearest enclosing :func:`run_id_context` override if
    one is active, otherwise to the process-wide default set by
    :func:`applog.configure`, otherwise ``None`` if logging has not been
    configured yet.
    """
    return _run_id_var.get(_default_run_id)


@contextlib.contextmanager
def run_id_context(run_id: str | None = None) -> Iterator[str]:
    """Temporarily override the run ID for the current thread/async context.

    Use this for sub-units of work (a batch item, a sub-task) that should
    be correlated under their own run ID while the surrounding execution
    keeps its own. Nested calls stack and unwind correctly.

    :param run_id: The run ID to adopt. A new one is generated if omitted.
    :return: A context manager yielding the resolved run ID.
    """
    resolved = run_id or new_run_id()
    token = _run_id_var.set(resolved)
    try:
        yield resolved
    finally:
        _run_id_var.reset(token)

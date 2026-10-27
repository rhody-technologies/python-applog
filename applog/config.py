"""Process-wide logging configuration.

:func:`configure` is the single entry point applications call, once, at
startup. Everything else in this module exists to resolve *what* it should
configure (paths, level, console echo) without requiring host applications
to edit this module's source: every setting has a library default, can be
overridden by an ``APPLOG_*`` environment variable, and can be overridden
again by an explicit keyword argument to ``configure()``.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from os import environ
from pathlib import Path

from applog.context import _clear_default_run_id, new_run_id, set_default_run_id
from applog.filters import ContextFilter
from applog.formatter import JsonFormatter
from applog.handlers import build_file_handler

_ENV_PREFIX = "APPLOG_"
_CONFIGURED_ATTR = "_applog_configured"
_CONFIG_ATTR = "_applog_config"

_LEVEL_NAMES: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _env_level(name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    level = _LEVEL_NAMES.get(raw.strip().upper())
    if level is None:
        valid = ", ".join(sorted(_LEVEL_NAMES))
        raise ValueError(f"Invalid {name}={raw!r}; expected one of: {valid}")
    return level


@dataclass(frozen=True)
class LogConfig:
    """Resolved configuration for one process's logging setup."""

    app_name: str
    log_path: Path
    level: int = logging.INFO
    console: bool = False
    utc_timestamps: bool = True
    run_id: str = field(default_factory=new_run_id)

    @classmethod
    def from_env(
        cls,
        app_name: str,
        *,
        log_path: Path | None = None,
        level: int | None = None,
        console: bool | None = None,
        utc_timestamps: bool | None = None,
        run_id: str | None = None,
    ) -> LogConfig:
        """Resolve a :class:`LogConfig`, applying env vars as the fallback tier.

        Precedence (lowest to highest): library default, ``APPLOG_*``
        environment variable, the explicit keyword argument passed here.

        Recognized environment variables: ``APPLOG_LOG_PATH``,
        ``APPLOG_LEVEL`` (``DEBUG``/``INFO``/``WARNING``/``ERROR``/
        ``CRITICAL``), ``APPLOG_CONSOLE`` (``true``/``false``),
        ``APPLOG_UTC`` (``true``/``false``), ``APPLOG_RUN_ID`` (useful for
        propagating one run ID from a parent process to subprocesses it
        launches).

        :raises ValueError: if ``APPLOG_LEVEL`` is set to an unrecognized
            name.
        """
        resolved_log_path = log_path or Path(
            environ.get(f"{_ENV_PREFIX}LOG_PATH", f"/var/log/apps/{app_name}/{app_name}.jsonl")
        )
        resolved_level = (
            level if level is not None else _env_level(f"{_ENV_PREFIX}LEVEL", logging.INFO)
        )
        resolved_console = (
            console if console is not None else _env_bool(f"{_ENV_PREFIX}CONSOLE", False)
        )
        resolved_utc = (
            utc_timestamps if utc_timestamps is not None else _env_bool(f"{_ENV_PREFIX}UTC", True)
        )
        resolved_run_id = run_id or environ.get(f"{_ENV_PREFIX}RUN_ID") or new_run_id()

        return cls(
            app_name=app_name,
            log_path=resolved_log_path,
            level=resolved_level,
            console=resolved_console,
            utc_timestamps=resolved_utc,
            run_id=resolved_run_id,
        )


def configure(
    app_name: str,
    *,
    log_path: Path | None = None,
    level: int | None = None,
    console: bool | None = None,
    utc_timestamps: bool | None = None,
    run_id: str | None = None,
    force: bool = False,
) -> LogConfig:
    """Configure process-wide logging. Safe to call more than once.

    Attaches handlers to the root logger exactly once per process. A
    second (or hundredth) call — e.g. because both a library and the
    application importing it call ``configure()`` — is a no-op that
    returns the existing configuration, so repeated imports or
    initialization never produce duplicate handlers or duplicate log
    lines. Pass ``force=True`` to tear down and rebuild configuration
    deliberately (intended for tests and REPL sessions, not normal
    application startup).

    After this call, any module may log with the plain stdlib pattern
    ``logging.getLogger(__name__)`` and its records will flow through the
    handlers configured here.

    :param app_name: Identifies the application in every log event and
        (by default) names its log file.
    :param log_path: Physical log file location. Defaults to
        ``APPLOG_LOG_PATH`` or ``/var/log/apps/<app_name>/<app_name>.jsonl``.
    :param level: Root logger level. Defaults to ``APPLOG_LEVEL`` or INFO.
    :param console: Also echo formatted records to stderr. Defaults to
        ``APPLOG_CONSOLE`` or False.
    :param utc_timestamps: Render timestamps in UTC rather than local
        time. Defaults to ``APPLOG_UTC`` or True.
    :param run_id: Correlation ID for this execution. Defaults to
        ``APPLOG_RUN_ID`` (propagated from a parent process) or a freshly
        generated one.
    :param force: Rebuild configuration even if already configured.
    :return: The resolved :class:`LogConfig` in effect for this process.
    """
    root = logging.getLogger()

    if getattr(root, _CONFIGURED_ATTR, False) and not force:
        return getattr(root, _CONFIG_ATTR)  # type: ignore[no-any-return]

    cfg = LogConfig.from_env(
        app_name,
        log_path=log_path,
        level=level,
        console=console,
        utc_timestamps=utc_timestamps,
        run_id=run_id,
    )

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    formatter = JsonFormatter(utc=cfg.utc_timestamps)
    context_filter = ContextFilter(cfg.app_name)

    file_handler = build_file_handler(cfg.log_path)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    root.addHandler(file_handler)

    if cfg.console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        root.addHandler(console_handler)

    root.setLevel(cfg.level)
    set_default_run_id(cfg.run_id)

    setattr(root, _CONFIGURED_ATTR, True)
    setattr(root, _CONFIG_ATTR, cfg)
    return cfg


def get_config() -> LogConfig | None:
    """Return the active :class:`LogConfig`, or ``None`` if not yet configured."""
    return getattr(logging.getLogger(), _CONFIG_ATTR, None)


def reset() -> None:
    """Remove applog's handlers and clear configuration state.

    Intended for tests that need a clean slate between cases, and for
    REPL sessions. Application code should not normally need this.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    for attr in (_CONFIGURED_ATTR, _CONFIG_ATTR):
        if hasattr(root, attr):
            delattr(root, attr)
    _clear_default_run_id()

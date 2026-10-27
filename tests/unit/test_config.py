"""Tests for configuration precedence and idempotent configure()."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

import applog
from applog.config import LogConfig


def test_default_log_path_uses_app_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPLOG_LOG_PATH", raising=False)
    cfg = LogConfig.from_env("billing-sync")
    assert cfg.log_path == Path("/var/log/apps/billing-sync/billing-sync.jsonl")


def test_explicit_kwarg_beats_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPLOG_LEVEL", "DEBUG")
    cfg = LogConfig.from_env("svc", log_path=tmp_path / "svc.jsonl", level=logging.ERROR)
    assert cfg.level == logging.ERROR


def test_env_var_beats_default_when_no_kwarg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPLOG_LEVEL", "WARNING")
    cfg = LogConfig.from_env("svc", log_path=tmp_path / "svc.jsonl")
    assert cfg.level == logging.WARNING


def test_invalid_level_env_var_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPLOG_LEVEL", "NOT_A_LEVEL")
    with pytest.raises(ValueError, match="APPLOG_LEVEL"):
        LogConfig.from_env("svc", log_path=tmp_path / "svc.jsonl")


def test_console_and_utc_env_bools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPLOG_CONSOLE", "true")
    monkeypatch.setenv("APPLOG_UTC", "false")
    cfg = LogConfig.from_env("svc", log_path=tmp_path / "svc.jsonl")
    assert cfg.console is True
    assert cfg.utc_timestamps is False


def test_run_id_propagated_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPLOG_RUN_ID", "parent-run-123")
    cfg = LogConfig.from_env("svc", log_path=tmp_path / "svc.jsonl")
    assert cfg.run_id == "parent-run-123"


def test_run_id_defaults_to_fresh_uuid(tmp_path: Path) -> None:
    cfg_a = LogConfig.from_env("svc", log_path=tmp_path / "a.jsonl")
    cfg_b = LogConfig.from_env("svc", log_path=tmp_path / "b.jsonl")
    assert cfg_a.run_id != cfg_b.run_id


def test_configure_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir" / "app.jsonl"
    applog.configure("svc", log_path=target)
    assert target.parent.is_dir()


def test_configure_attaches_file_handler_only_by_default(tmp_path: Path) -> None:
    applog.configure("svc", log_path=tmp_path / "svc.jsonl")
    root = logging.getLogger()
    assert len(root.handlers) == 1


def test_configure_attaches_console_handler_when_requested(tmp_path: Path) -> None:
    applog.configure("svc", log_path=tmp_path / "svc.jsonl", console=True)
    root = logging.getLogger()
    assert len(root.handlers) == 2


def test_repeated_configure_is_noop_and_keeps_first_config(tmp_path: Path) -> None:
    first = applog.configure("svc", log_path=tmp_path / "svc.jsonl", level=logging.DEBUG)
    second = applog.configure("other-app", log_path=tmp_path / "other.jsonl", level=logging.ERROR)

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert second is first
    assert applog.get_config() == first


def test_force_rebuilds_configuration(tmp_path: Path) -> None:
    applog.configure("svc", log_path=tmp_path / "svc.jsonl", level=logging.DEBUG)
    rebuilt = applog.configure(
        "svc", log_path=tmp_path / "svc2.jsonl", level=logging.ERROR, force=True
    )

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert rebuilt.level == logging.ERROR
    assert rebuilt.log_path == tmp_path / "svc2.jsonl"


def test_reset_clears_configuration(tmp_path: Path) -> None:
    applog.configure("svc", log_path=tmp_path / "svc.jsonl")
    applog.reset()
    assert applog.get_config() is None
    assert logging.getLogger().handlers == []


def test_get_config_none_before_configure() -> None:
    assert applog.get_config() is None

"""Tests for run-id generation and context propagation."""

from __future__ import annotations

from applog.context import get_run_id, new_run_id, run_id_context, set_default_run_id


def test_new_run_id_is_unique_and_hex() -> None:
    a, b = new_run_id(), new_run_id()
    assert a != b
    assert len(a) == 32
    int(a, 16)  # does not raise


def test_default_run_id_is_fallback() -> None:
    assert get_run_id() is None
    set_default_run_id("process-default")
    assert get_run_id() == "process-default"


def test_run_id_context_overrides_and_restores() -> None:
    set_default_run_id("process-default")
    assert get_run_id() == "process-default"

    with run_id_context("task-run-id") as resolved:
        assert resolved == "task-run-id"
        assert get_run_id() == "task-run-id"

    assert get_run_id() == "process-default"


def test_run_id_context_generates_id_when_omitted() -> None:
    with run_id_context() as resolved:
        assert resolved
        assert get_run_id() == resolved


def test_nested_run_id_context_stacks_and_unwinds() -> None:
    set_default_run_id("root")
    with run_id_context("outer"):
        assert get_run_id() == "outer"
        with run_id_context("inner"):
            assert get_run_id() == "inner"
        assert get_run_id() == "outer"
    assert get_run_id() == "root"

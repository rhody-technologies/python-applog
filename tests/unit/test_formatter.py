"""Tests for JsonFormatter output shape and exception handling."""

from __future__ import annotations

import json
import logging
import re
import uuid

from applog.filters import ContextFilter
from applog.formatter import JsonFormatter


def _make_record(
    *,
    msg: str = "hello %s",
    args: tuple[object, ...] = ("world",),
    exc_info: tuple[object, ...] | None = None,
    extra: dict[str, object] | None = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="my.module",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg=msg,
        args=args,
        exc_info=exc_info,  # type: ignore[arg-type]
        func="some_function",
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_format_produces_single_line_valid_json() -> None:
    record = _make_record()
    ContextFilter("my-app").filter(record)
    line = JsonFormatter().format(record)

    assert "\n" not in line
    payload = json.loads(line)
    assert payload["message"] == "hello world"
    assert payload["app"] == "my-app"
    assert payload["logger"] == "my.module"
    assert payload["function"] == "some_function"
    assert payload["line"] == 42
    assert payload["level"] == "INFO"
    assert "timestamp" in payload
    assert "run_id" in payload


def test_run_id_present_after_filter() -> None:
    record = _make_record()
    ContextFilter("my-app").filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["run_id"] is None  # no configure() -> no default run id in this test


def test_extra_metadata_is_namespaced_under_extra_key() -> None:
    record = _make_record(extra={"status": "ok", "record_count": 42})
    ContextFilter("my-app").filter(record)
    payload = json.loads(JsonFormatter().format(record))

    assert payload["extra"] == {"status": "ok", "record_count": 42}
    assert "status" not in payload
    assert "record_count" not in payload


def test_no_extra_key_when_no_extra_metadata() -> None:
    record = _make_record()
    ContextFilter("my-app").filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert "extra" not in payload


def test_exception_info_is_structured() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = _make_record(msg="failed", args=(), exc_info=exc_info)
    ContextFilter("my-app").filter(record)
    line = JsonFormatter().format(record)

    assert "\n" not in line
    payload = json.loads(line)
    assert payload["exception"]["type"] == "ValueError"
    assert payload["exception"]["message"] == "boom"
    assert "Traceback (most recent call last)" in payload["exception"]["traceback"]
    assert "ValueError: boom" in payload["exception"]["traceback"]


def test_stack_info_is_included_when_present_without_exception() -> None:
    record = _make_record(msg="checkpoint", args=())
    record.stack_info = "Stack (most recent call last):\n  File ..."
    ContextFilter("my-app").filter(record)
    payload = json.loads(JsonFormatter().format(record))

    assert "exception" not in payload
    assert payload["stack"] == "Stack (most recent call last):\n  File ..."


def test_utc_vs_local_timestamp_formatting_runs_without_error() -> None:
    record = _make_record()
    ContextFilter("my-app").filter(record)
    utc_line = JsonFormatter(utc=True).format(record)
    local_line = JsonFormatter(utc=False).format(record)
    assert json.loads(utc_line)["timestamp"]
    assert json.loads(local_line)["timestamp"]


def test_log_id_is_present_and_a_uuid4_hex() -> None:
    record = _make_record()
    ContextFilter("my-app").filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert re.fullmatch(r"[0-9a-f]{32}", payload["log_id"])
    assert uuid.UUID(payload["log_id"]).version == 4


def test_log_id_is_unique_per_record() -> None:
    log_filter = ContextFilter("my-app")
    formatter = JsonFormatter()
    ids = set()
    for _ in range(1000):
        record = _make_record()
        log_filter.filter(record)
        ids.add(json.loads(formatter.format(record))["log_id"])
    assert len(ids) == 1000


def test_log_id_is_stable_when_one_record_passes_through_the_filter_twice() -> None:
    # configure() shares one filter across the file and console handlers, so a
    # single record is filtered once per handler; both outputs must agree.
    record = _make_record()
    log_filter = ContextFilter("my-app")
    log_filter.filter(record)
    first = json.loads(JsonFormatter().format(record))["log_id"]
    log_filter.filter(record)
    second = json.loads(JsonFormatter().format(record))["log_id"]
    assert first == second


def test_log_id_is_generated_even_without_the_filter() -> None:
    payload = json.loads(JsonFormatter().format(_make_record()))
    assert re.fullmatch(r"[0-9a-f]{32}", payload["log_id"])


def test_caller_supplied_log_id_extra_cannot_override_the_generated_id() -> None:
    record = _make_record(extra={"log_id": "spoofed"})
    ContextFilter("my-app").filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["log_id"] != "spoofed"
    assert payload["extra"] == {"log_id": "spoofed"}

"""End-to-end: configure() + logging.getLogger(__name__) writing real JSON Lines."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import applog


def test_getlogger_pattern_writes_structured_json_line(tmp_path: Path) -> None:
    log_path = tmp_path / "app.jsonl"
    applog.configure("checkout-service", log_path=log_path)

    logger = logging.getLogger("checkout_service.orders")
    logger.info("order placed", extra={"order_id": "A1", "total_cents": 1999})

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["app"] == "checkout-service"
    assert payload["logger"] == "checkout_service.orders"
    assert payload["message"] == "order placed"
    assert payload["extra"] == {"order_id": "A1", "total_cents": 1999}
    assert payload["run_id"] == applog.get_config().run_id  # type: ignore[union-attr]


def test_repeated_configure_does_not_duplicate_log_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "app.jsonl"
    applog.configure("svc", log_path=log_path)
    applog.configure("svc", log_path=log_path)  # second call: no-op
    applog.configure("svc", log_path=log_path)  # third call: no-op

    logging.getLogger(__name__).info("only once")

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1


def test_level_filtering_respects_configured_level(tmp_path: Path) -> None:
    log_path = tmp_path / "app.jsonl"
    applog.configure("svc", log_path=log_path, level=logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("should be filtered out")
    logger.warning("should be kept")

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["message"] == "should be kept"


def test_exception_logged_via_logger_exception(tmp_path: Path) -> None:
    log_path = tmp_path / "app.jsonl"
    applog.configure("svc", log_path=log_path)
    logger = logging.getLogger(__name__)

    try:
        raise RuntimeError("disk full")
    except RuntimeError:
        logger.exception("failed to write output")

    payload = json.loads(log_path.read_text().splitlines()[0])
    assert payload["exception"]["type"] == "RuntimeError"
    assert payload["exception"]["message"] == "disk full"


def test_get_logger_is_equivalent_to_stdlib_getlogger() -> None:
    assert applog.get_logger("my.module") is logging.getLogger("my.module")
    assert applog.get_logger() is logging.getLogger()


def test_run_id_context_tags_sub_task_events(tmp_path: Path) -> None:
    log_path = tmp_path / "app.jsonl"
    applog.configure("svc", log_path=log_path)
    root_run_id = applog.get_config().run_id  # type: ignore[union-attr]
    logger = logging.getLogger(__name__)

    logger.info("before sub-task")
    with applog.run_id_context("sub-task-1"):
        logger.info("inside sub-task")
    logger.info("after sub-task")

    payloads = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [p["run_id"] for p in payloads] == [root_run_id, "sub-task-1", root_run_id]

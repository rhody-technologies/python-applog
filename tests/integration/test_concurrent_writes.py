"""Integration test: multiple real OS processes logging to one shared file.

This exercises the specific hazard the module is designed around: several
independent Python processes (not threads — separate interpreters, no
shared memory) appending structured JSON Lines to the same physical log
file at once. A naive implementation (e.g. handlers that do their own
size-based rotation) can interleave partial writes or race each other
during rotation, corrupting the file. applog avoids both by relying on
atomic O_APPEND writes and never rotating in-process (see
``applog/handlers.py``); this test proves that design holds under real
concurrent load rather than just asserting it in a docstring.
"""

from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

from tests.integration._workers import log_many

_PROCESS_COUNT = 8
_MESSAGES_PER_PROCESS = 250


def _run_workers(log_path: Path, run_id: str | None) -> None:
    ctx = mp.get_context("spawn")
    procs = [
        ctx.Process(
            target=log_many,
            args=(str(log_path), "concurrency-test-app", _MESSAGES_PER_PROCESS, run_id),
        )
        for _ in range(_PROCESS_COUNT)
    ]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(timeout=60)
        assert proc.exitcode == 0, f"worker process failed with exit code {proc.exitcode}"


def test_concurrent_multiprocess_writes_produce_no_corruption(tmp_path: Path) -> None:
    log_path = tmp_path / "shared.jsonl"
    _run_workers(log_path, run_id=None)

    lines = log_path.read_text().splitlines()
    assert len(lines) == _PROCESS_COUNT * _MESSAGES_PER_PROCESS

    # Every single line must parse as one complete JSON object: if two
    # processes' writes had interleaved, at least one line would be
    # truncated or merged with another and json.loads would fail here.
    parsed = [json.loads(line) for line in lines]
    assert all(entry["message"] == "worker message" for entry in parsed)
    assert all(entry["app"] == "concurrency-test-app" for entry in parsed)

    # Each process independently emits seq 0..N-1; across all processes we
    # must see each seq value exactly _PROCESS_COUNT times, confirming no
    # message was dropped or duplicated by the concurrent-write path.
    seqs_seen = sorted(entry["extra"]["seq"] for entry in parsed)
    expected = sorted(list(range(_MESSAGES_PER_PROCESS)) * _PROCESS_COUNT)
    assert seqs_seen == expected


def test_concurrent_processes_share_a_propagated_run_id(tmp_path: Path) -> None:
    log_path = tmp_path / "shared.jsonl"
    shared_run_id = "integration-shared-run-id"
    _run_workers(log_path, run_id=shared_run_id)

    lines = log_path.read_text().splitlines()
    parsed = [json.loads(line) for line in lines]
    assert all(entry["run_id"] == shared_run_id for entry in parsed)

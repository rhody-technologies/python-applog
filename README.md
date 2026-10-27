# applog

A reusable, structured logging module for Python applications. Call
`applog.configure()` once at startup; every module in the application (and
every library it uses) keeps using the standard
`logging.getLogger(__name__)` pattern, and every event comes out as a
structured [JSON Lines](https://jsonlines.org/) record in one centrally
configured file that an existing log forwarder already watches.

## Why

Every Python application in the fleet ends up solving the same problem —
"where do logs go, what format are they in, how do I tell which app and
which run an event belongs to" — slightly differently. `applog` standardizes
that once, on top of the standard library's own `logging` module, so:

- Applications don't gain a new dependency's worth of coupling — just
  stdlib `logging` underneath.
- Output is machine-parseable JSON Lines, one object per line, ready for
  the forwarder to ship to the centralized logging platform.
- Every event is tagged with the originating application, module,
  function, and a run ID correlating every event from one execution.
- Changing *where* logs go, or how they're forwarded, is a one-line config
  change in each application — not a rewrite of its logging calls.

## Install

From this repository:

```bash
pip install git+https://github.com/rhody-technologies/python-applog.git
```

Or, for local development against a checkout:

```bash
pip install -e ".[dev]"
```

## Quick start

```python
import logging
import applog

applog.configure("my-app")          # once, at startup
logger = logging.getLogger(__name__)  # everywhere else, as usual

logger.info("started", extra={"status": "ok"})
```

That's the entire integration surface. See [`examples/standalone_script`](examples/standalone_script)
for a complete single-file script, and [`examples/multi_module_app`](examples/multi_module_app)
for an application where `configure()` is called once in `main.py` while
`services/` and `models/` modules never import `applog` at all.

## What a log line looks like

```json
{"timestamp": "2026-10-27T14:30:52.294+00:00", "level": "INFO", "app": "order-batch-app", "run_id": "9881fbb8efee432f8d4454dd5bb03d39", "logger": "examples.multi_module_app.services.worker", "module": "worker", "function": "process_batch", "line": 32, "message": "processed order", "pid": 99807, "thread": "MainThread", "extra": {"order_id": "A1", "total_cents": 1999}}
```

- `app`, `run_id`, `logger`/`module`/`function`/`line`, `pid`, `thread` —
  identify exactly where and under which execution the event happened.
- `message` — the formatted log message, same as stdlib `logging`.
- `extra` — anything passed via `logger.info(msg, extra={...})`. This is
  where application-specific structured metadata (status, record counts,
  file names, durations, ...) lives; arbitrary and optional.
- `exception` — present only when the record carries exception info
  (`logger.exception(...)` or `exc_info=True`), with `type`, `message`,
  and a single-string `traceback`.

## Configuration

`configure()` resolves every setting through the same precedence, lowest to
highest: **library default → `APPLOG_*` environment variable → explicit
keyword argument.** This is what lets an application change logging
behavior (where the file lives, what level is active, whether to also echo
to the console) without ever touching this module's source.

| Setting | Keyword arg | Environment variable | Default |
|---|---|---|---|
| Application name | `app_name` (positional, required) | — | — |
| Log file path | `log_path: Path` | `APPLOG_LOG_PATH` | `/var/log/apps/<app_name>/<app_name>.jsonl` |
| Log level | `level: int` (e.g. `logging.DEBUG`) | `APPLOG_LEVEL` (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`) | `INFO` |
| Echo to stderr | `console: bool` | `APPLOG_CONSOLE` (`true`/`false`) | `False` |
| UTC timestamps | `utc_timestamps: bool` | `APPLOG_UTC` (`true`/`false`) | `True` |
| Run ID | `run_id: str` | `APPLOG_RUN_ID` | freshly generated UUID4 |

```python
import logging
from pathlib import Path
import applog

applog.configure(
    "my-app",
    log_path=Path("/var/log/apps/my-app/my-app.jsonl"),
    level=logging.DEBUG,
    console=False,
)
```

Setting `APPLOG_RUN_ID` is how a parent process propagates one run ID down
to subprocesses it launches, so every process involved in one logical
execution is correlated under the same ID.

## Correlating a run

Every event emitted after `configure()` carries the same `run_id` by
default — grep the log file for one `run_id` to see the full timeline of
one execution, across every module and (if propagated via `APPLOG_RUN_ID`)
every process involved.

For a sub-unit of work that deserves its own correlation ID — one item of
a batch, a sub-task — without disturbing the parent's `run_id`, use
`run_id_context`:

```python
with applog.run_id_context():          # generates a fresh sub-run ID
    handle_one_batch_item(item)
# back to the process's default run_id here
```

## Avoiding duplicate handlers and log lines

`configure()` is idempotent: it attaches handlers to the root logger
exactly once per process. A second, third, or Nth call — because a library
and the application that imports it both call `configure()`, or because a
module gets imported twice — returns the existing configuration unchanged
and does **not** add another handler. That's what the test suite in
`tests/unit/test_end_to_end_logging.py::test_repeated_configure_does_not_duplicate_log_lines`
verifies directly: logging once after three `configure()` calls produces
exactly one line in the output file.

Pass `force=True` only when you deliberately want to rebuild configuration
(tests, a REPL session) — not during normal application startup.

## Concurrency and rotation design

Multiple independent Python processes (different applications, or several
workers of the same application) may write to the same shared log file at
once. Two stdlib-only properties make that safe:

1. Each record is written with a single `write()` + `flush()`, to a file
   opened in append mode. POSIX guarantees an `O_APPEND` write is atomic as
   long as it fits in one `write(2)` syscall (in practice, up to
   `PIPE_BUF` — commonly 4096 bytes on Linux). Concurrent processes
   therefore cannot interleave partial lines. Keep individual log lines
   reasonably small if you expect many concurrent writers; log a reference
   to large payloads (a file path, an object-store key) rather than
   embedding them.
2. The file handler is a `logging.handlers.WatchedFileHandler`, which
   detects if an external tool (`logrotate`, the forwarder) has renamed or
   truncated the file and transparently reopens it. **This module never
   rotates the file itself** — several processes each independently
   deciding "it's time to rotate" is exactly the hazard this design avoids.
   Rotation is infrastructure's job (e.g. `logrotate` with `copytruncate`
   or `create`); applog only ever appends.

`tests/integration/test_concurrent_writes.py` proves this holds under real
load: eight separate OS processes (via `multiprocessing`, `spawn` start
method — genuinely separate interpreters, no shared memory) each write 250
records concurrently to one file, and the test asserts every single line
parses as valid, uncorrupted JSON with no dropped or duplicated messages.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                 # full suite (unit + multiprocess integration)
black .
ruff check .
mypy .
```

See [`CHANGELOG.md`](CHANGELOG.md) for release history.

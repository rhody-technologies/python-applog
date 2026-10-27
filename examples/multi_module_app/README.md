# Multi-module application example

Shows the pattern the task requires: configure applog exactly once, at the
application's entry point, and let every other module use the plain
standard-library `logging.getLogger(__name__)` pattern.

```text
main.py                  <- the only module that imports applog
services/worker.py       <- plain `logging.getLogger(__name__)`, no applog import
models/record.py         <- plain `logging.getLogger(__name__)`, no applog import
```

## Run it

```bash
pip install -e .            # from the repo root, installs applog
python -m examples.multi_module_app.main
```

## What to look at

- `main.py` is the only file with `import applog` in it. `services/worker.py`
  and `models/record.py` only ever import `logging`.
- Because `applog.configure()` attaches handlers to the **root** logger,
  every child logger (`examples.multi_module_app.services.worker`,
  `examples.multi_module_app.models.record`, ...) propagates up to it and
  comes out in the same structured format automatically — nothing to wire
  up per module.
- `services/worker.py` attaches arbitrary structured metadata
  (`record_count`, `processed_count`, `duration_ms`) via `extra={...}`,
  showing how application-specific fields flow through untouched.
- `models/record.py`'s `logger.warning(...)` call for the invalid record
  shows up tagged with its own module's logger name
  (`examples.multi_module_app.models.record`) even though that module never
  configured anything.
- All events from one run share the same `run_id`, letting you grep the
  log file for one execution across every module that logged during it.

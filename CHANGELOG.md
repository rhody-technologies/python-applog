# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `applog` package: a reusable, structured JSON Lines logging module.
  Call `applog.configure(app_name)` once at startup; every module keeps
  using `logging.getLogger(__name__)`. Provides a `JsonFormatter`,
  run-ID correlation (`run_id_context`, `APPLOG_RUN_ID` propagation), a
  concurrency-safe `WatchedFileHandler`-based file handler designed for
  multiple processes appending to one shared log file, standardized
  exception/traceback formatting, and `APPLOG_*` environment variable
  configuration. Idempotent `configure()` — repeated calls never
  duplicate handlers or log lines.
- Unit tests (`tests/unit`) covering configuration precedence, idempotent
  setup, JSON formatter output, exception formatting, and run-ID context
  propagation.
- Integration test (`tests/integration/test_concurrent_writes.py`)
  exercising real multi-process concurrent writes to a shared log file.
- Usage examples: a single-file standalone script
  (`examples/standalone_script`) and a multi-module application
  (`examples/multi_module_app`) demonstrating configure-once,
  `getLogger(__name__)`-everywhere.

### Changed

- CI workflows and the pull request template, which were inherited from
  a Go project template, now run Python checks (`ruff`, `black --check`,
  `mypy`, `pytest`) instead of Go tooling.

### Added (template)

- Initial project template: source layout, test scaffolding, CI/CD
  workflows, and contributor documentation.

## [0.1.0] - 2026-09-02

### Added

- Initial release of the template repository.

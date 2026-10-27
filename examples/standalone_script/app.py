"""Standalone-script example: minimal applog setup.

Run with:

    python examples/standalone_script/app.py

Writes structured JSON Lines to ./standalone-example.jsonl in the current
directory and echoes them to stderr (console=True is handy for scripts you
run interactively; a long-running service typically leaves it off and lets
the log forwarder be the only consumer of the file).
"""

from __future__ import annotations

import logging
from pathlib import Path

import applog

logger = logging.getLogger(__name__)


def risky_division(numerator: int, denominator: int) -> float:
    """Divide two numbers, logging the inputs and outcome."""
    logger.info("computing division", extra={"numerator": numerator, "denominator": denominator})
    return numerator / denominator


def main() -> None:
    """Configure logging once, then run the script's work."""
    applog.configure(
        "standalone-example",
        log_path=Path(__file__).parent / "standalone-example.jsonl",
        console=True,
    )

    logger.info("script started", extra={"run_kind": "manual"})

    logger.info("result: %s", risky_division(10, 2))

    try:
        risky_division(1, 0)
    except ZeroDivisionError:
        logger.exception("division failed")

    logger.info("script finished", extra={"status": "ok"})


if __name__ == "__main__":
    main()

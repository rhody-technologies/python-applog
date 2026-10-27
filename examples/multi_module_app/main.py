"""Multi-module application example: configure once, log everywhere.

Run with (from the repo root):

    python -m examples.multi_module_app.main

Only this entry-point module ever imports or calls into applog. The
``services`` and ``models`` modules it calls into use plain
``logging.getLogger(__name__)`` and know nothing about applog — yet their
events come out in the same structured JSON Lines format, tagged with the
same app name and run ID, because logging configuration lives on the root
logger and every logger propagates up to it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import applog
from examples.multi_module_app.models.record import OrderRecord
from examples.multi_module_app.services.worker import process_batch

logger = logging.getLogger(__name__)


def main() -> None:
    """Configure logging once, then run the application."""
    applog.configure(
        "order-batch-app",
        log_path=Path(__file__).parent / "order-batch-app.jsonl",
        console=True,
    )

    logger.info("application starting", extra={"run_id": applog.get_run_id()})

    batch = [
        OrderRecord(order_id="A1", total_cents=1999),
        OrderRecord(order_id="A2", total_cents=499),
        OrderRecord(order_id="A3", total_cents=-100),  # invalid: rejected by models/record.py
    ]
    processed = process_batch(batch)

    logger.info("application finished", extra={"status": "ok", "processed_count": processed})


if __name__ == "__main__":
    main()

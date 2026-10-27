"""A small processing service used by the multi-module example.

Like ``models/record.py``, this module only ever touches the standard
library ``logging`` module. It has no idea applog exists, which is exactly
what lets it be reused in a different application with different logging
configuration without any changes.
"""

from __future__ import annotations

import logging
import time

from examples.multi_module_app.models.record import OrderRecord, validate

logger = logging.getLogger(__name__)


def process_batch(records: list[OrderRecord]) -> int:
    """Validate and "process" each record, returning the count processed.

    Logs one structured event per record and a summary event at the end,
    including a duration — an example of the arbitrary application
    metadata the task calls out (status, record counts, durations).
    """
    started = time.monotonic()
    processed = 0

    for record in records:
        if not validate(record):
            continue
        logger.info(
            "processed order",
            extra={"order_id": record.order_id, "total_cents": record.total_cents},
        )
        processed += 1

    duration_ms = round((time.monotonic() - started) * 1000, 2)
    logger.info(
        "batch complete",
        extra={
            "status": "ok",
            "record_count": len(records),
            "processed_count": processed,
            "duration_ms": duration_ms,
        },
    )
    return processed

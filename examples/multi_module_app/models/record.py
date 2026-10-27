"""A small domain model used by the multi-module example.

Note this module never imports or configures applog — it just uses the
standard library pattern. That's the point: logging setup is the
application's concern, not every module's.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderRecord:
    """One row of input data for the batch example."""

    order_id: str
    total_cents: int


def validate(record: OrderRecord) -> bool:
    """Return whether ``record`` is valid, logging a warning if not."""
    if record.total_cents < 0:
        logger.warning(
            "rejecting record with negative total",
            extra={"order_id": record.order_id, "total_cents": record.total_cents},
        )
        return False
    return True

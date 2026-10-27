"""Shared fixtures for applog unit tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import applog


@pytest.fixture(autouse=True)
def _applog_clean_state() -> Iterator[None]:
    """Ensure every test starts and ends with no applog configuration."""
    applog.reset()
    yield
    applog.reset()

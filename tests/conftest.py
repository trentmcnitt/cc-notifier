"""Shared pytest fixtures for cc-notifier tests."""

from unittest.mock import patch

import pytest

import cc_notifier


@pytest.fixture(autouse=True)
def isolated_log_file(tmp_path):
    """Keep tests from writing to the developer's real ~/.cc-notifier log."""
    with patch.object(cc_notifier, "LOG_FILE", tmp_path / "cc-notifier.log"):
        yield

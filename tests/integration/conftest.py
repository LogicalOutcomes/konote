"""Pytest configuration for integration tests."""
import pytest


def pytest_collection_modifyitems(items):
    """Mark all tests in this directory with the 'integration' marker."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

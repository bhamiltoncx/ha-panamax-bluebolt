"""pytest configuration for the BlueBolt / Panamax test suite."""
from __future__ import annotations
from pathlib import Path
import pytest


def pytest_configure(config: object) -> None:
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def hass_config_dir() -> str:
    return str(Path(__file__).parent.parent)

"""Shared test fixtures."""

import importlib.util
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests must never download anything: fail loudly on any connection attempt."""

    def guard(*args, **kwargs):
        raise RuntimeError("Tests must not use the network; use the sample files in data/")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


def load_script(name):
    """Import ``scripts/<name>.py`` as a module (scripts are not a package)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # needed by dataclasses inside the script
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def download_module():
    """``scripts/download_data.py``, imported without network access."""
    return load_script("download_data")

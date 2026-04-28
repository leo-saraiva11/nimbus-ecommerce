"""Shared pytest fixtures for the Nimbus test suite."""
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    return project_root / "data"


@pytest.fixture
def corpus_dir(project_root: Path) -> Path:
    return project_root / "corpus"

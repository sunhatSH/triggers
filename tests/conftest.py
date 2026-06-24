"""Shared test fixtures."""
from pathlib import Path

import pytest

from triggerctl import library as lib


def _resolve_fixture_library() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (
        here / "fixtures" / "trigger-library",
        here.parent.parent / "trigger-library",
    ):
        if candidate.is_dir() and (
            (candidate / "manifest.yaml").is_file() or any(candidate.rglob("*.md"))
        ):
            return candidate
    raise FileNotFoundError(
        "trigger-library fixture not found "
        "(expected tests/fixtures/trigger-library or sibling trigger-library repo)"
    )


FIXTURE_LIB = _resolve_fixture_library()


@pytest.fixture
def synced_library(tmp_path, monkeypatch):
    dest = tmp_path / "library"
    monkeypatch.setattr("triggerctl.paths.local_library_dir", lambda: dest)
    monkeypatch.setattr("triggerctl.library.local_library_dir", lambda: dest)
    lib.sync_library(str(FIXTURE_LIB))
    return dest

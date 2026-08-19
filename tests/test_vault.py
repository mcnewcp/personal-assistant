"""Tests for Vault path construction."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from personal_assistant.vault import note_path

VAULT = Path("/vault")


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        # Single-digit month and day both zero-pad, in the directory names and
        # in the filename.
        (date(2026, 3, 7), "Notes/2026/03/2026-03-07.md"),
        # The edges of the year, where a naive month directory would collapse.
        (date(2026, 1, 1), "Notes/2026/01/2026-01-01.md"),
        (date(2026, 12, 31), "Notes/2026/12/2026-12-31.md"),
    ],
)
def test_note_path_files_the_day_by_year_and_month(day: date, expected: str) -> None:
    assert note_path(VAULT, day) == VAULT / expected


def test_note_path_stays_under_the_vault_root() -> None:
    result = note_path(VAULT, date(2026, 3, 7))

    assert result.is_relative_to(VAULT)
    assert result.relative_to(VAULT) == Path("Notes/2026/03/2026-03-07.md")


def test_note_path_does_not_touch_the_filesystem(tmp_path: Path) -> None:
    """It computes a path and nothing more — no mkdir, no existence check."""
    result = note_path(tmp_path, date(2026, 3, 7))

    assert not result.exists()
    assert list(tmp_path.iterdir()) == []

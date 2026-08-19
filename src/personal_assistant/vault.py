"""Where things live in the Vault.

The Vault is the Obsidian vault outside this repo; every path the application
reads or writes is derived here rather than spelled out at the call site.
Layout decisions are settled in the v0.1 map (#2) and #7.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path


def note_path(vault_root: Path, day: date) -> Path:
    """Return the path the given day's Note lives at, under `vault_root`.

    Notes are filed as `Notes/YYYY/MM/YYYY-MM-DD.md`, zero-padded. This is a
    pure computation: it never creates directories and never checks whether
    the Note already exists.
    """
    return (
        vault_root
        / "Notes"
        / f"{day.year:04d}"
        / f"{day.month:02d}"
        / f"{day.isoformat()}.md"
    )

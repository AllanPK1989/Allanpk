"""Nightly copy of the SQLite database (safe while the app is running), keeping the last 14."""
import sqlite3
from pathlib import Path

from .config import get_config
from .timeutil import utcnow


def backup_dir() -> Path:
    path = get_config().data_dir / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path | None:
    url = get_config().db_url
    if not url.startswith("sqlite:///"):
        return None
    return Path(url.removeprefix("sqlite:///"))


def run_backup() -> Path | None:
    src_path = db_path()
    if src_path is None or not src_path.exists():
        return None
    target = backup_dir() / f"nudge-{utcnow().strftime('%Y-%m-%d-%H%M%S')}.sqlite"
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    prune()
    return target


def prune() -> None:
    keep = get_config().backup_keep
    files = sorted(backup_dir().glob("nudge-*.sqlite"))
    for old in files[: max(0, len(files) - keep)]:
        old.unlink(missing_ok=True)


def list_backups() -> list[dict]:
    files = sorted(backup_dir().glob("nudge-*.sqlite"), reverse=True)
    return [{"name": f.name, "size": f.stat().st_size} for f in files]


def backup_file(name: str) -> Path | None:
    if "/" in name or "\\" in name or not name.startswith("nudge-") or not name.endswith(".sqlite"):
        return None
    path = backup_dir() / name
    return path if path.exists() else None

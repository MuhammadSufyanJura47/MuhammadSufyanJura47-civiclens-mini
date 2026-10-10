"""
JSON-file storage for CivicLens Mini.

No database. Complaints live in a single JSON file (`data/complaints.json`).
Writes are atomic (write temp file, then replace) so an interrupted write never
corrupts the store. Windows-safe paths via pathlib.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
STORE_PATH = DATA_DIR / "complaints.json"

STATUSES = ["New", "In Review", "Assigned", "Resolved", "Closed"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_store() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        _atomic_write([])


def _atomic_write(items: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        os.replace(tmp, STORE_PATH)  # atomic on Windows + POSIX
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_all() -> list[dict[str, Any]]:
    _ensure_store()
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable -> start clean rather than crash the dashboard.
        return []


def save_complaint(
    text: str,
    analysis: dict[str, Any],
    *,
    is_sample: bool = False,
    duplicates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items = load_all()
    record = {
        "id": uuid.uuid4().hex[:8],
        "created_at": _now_iso(),
        "text": text.strip(),
        "analysis": analysis,
        "status": "New",
        "is_sample": is_sample,
        "duplicates": duplicates or [],
    }
    items.insert(0, record)  # newest first
    _atomic_write(items)
    return record


def update_status(complaint_id: str, status: str) -> bool:
    if status not in STATUSES:
        return False
    items = load_all()
    changed = False
    for item in items:
        if item.get("id") == complaint_id:
            item["status"] = status
            changed = True
            break
    if changed:
        _atomic_write(items)
    return changed


def delete_complaint(complaint_id: str) -> bool:
    items = load_all()
    new_items = [i for i in items if i.get("id") != complaint_id]
    if len(new_items) == len(items):
        return False
    _atomic_write(new_items)
    return True


def clear_all() -> None:
    _atomic_write([])


def stats() -> dict[str, Any]:
    items = load_all()
    by_category: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    open_count = 0
    for item in items:
        a = item.get("analysis") or {}
        by_category[a.get("category", "Other")] = by_category.get(a.get("category", "Other"), 0) + 1
        by_priority[a.get("suggested_priority", "Medium")] = (
            by_priority.get(a.get("suggested_priority", "Medium"), 0) + 1
        )
        if item.get("status") not in {"Resolved", "Closed"}:
            open_count += 1
    return {
        "total": len(items),
        "open": open_count,
        "by_category": by_category,
        "by_priority": by_priority,
    }

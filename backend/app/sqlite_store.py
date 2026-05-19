"""SQLite-backed task store. Drop-in replacement for app/dataverse.py while you
finish setting up Dataverse. Same async function signatures so the rest of the
backend doesn't need to change.

Switch from Dataverse to SQLite by editing app/main.py to import from
`.sqlite_store` instead of `.dataverse`. To switch back later, undo that import.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "tasks.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Not Started',
            priority TEXT DEFAULT 'Medium',
            assignee_email TEXT,
            due_date TEXT,
            created_on TEXT NOT NULL,
            modified_on TEXT NOT NULL
        )
        """
    )
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


async def list_tasks() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM tasks ORDER BY created_on DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_task(task_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_dict(row) if row else None


async def create_task(payload: dict) -> dict:
    now = datetime.utcnow().isoformat()
    task_id = str(uuid.uuid4())
    record = {
        "id": task_id,
        "title": payload.get("title"),
        "description": payload.get("description"),
        "status": payload.get("status") or "Not Started",
        "priority": payload.get("priority") or "Medium",
        "assignee_email": payload.get("assignee_email"),
        "due_date": payload.get("due_date").isoformat() if hasattr(payload.get("due_date"), "isoformat") else payload.get("due_date"),
        "created_on": now,
        "modified_on": now,
    }
    with _conn() as c:
        c.execute(
            "INSERT INTO tasks (id, title, description, status, priority, assignee_email, due_date, created_on, modified_on) VALUES (:id, :title, :description, :status, :priority, :assignee_email, :due_date, :created_on, :modified_on)",
            record,
        )
        c.commit()
    return record


async def update_task(task_id: str, payload: dict) -> dict:
    existing = await get_task(task_id)
    if not existing:
        raise ValueError(f"Task {task_id} not found")
    merged = {**existing, **{k: v for k, v in payload.items() if v is not None}}
    if "due_date" in merged and hasattr(merged["due_date"], "isoformat"):
        merged["due_date"] = merged["due_date"].isoformat()
    merged["modified_on"] = datetime.utcnow().isoformat()
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET title=:title, description=:description, status=:status, priority=:priority, assignee_email=:assignee_email, due_date=:due_date, modified_on=:modified_on WHERE id=:id",
            merged,
        )
        c.commit()
    return merged


async def delete_task(task_id: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        c.commit()

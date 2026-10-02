"""SQLite persistence: one row per workflow run, state stored as JSON."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .models import WorkflowState


def _db_path() -> Path:
    return Path(config.get("FORGEFLOW_DB", str(config.DATA_DIR / "forgeflow.db")))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, updated TEXT NOT NULL, state TEXT NOT NULL)")
    return conn


def save(state: WorkflowState) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO runs (id, updated, state) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET updated = excluded.updated, state = excluded.state",
            (state.id, now, state.model_dump_json()),
        )


def load(run_id: str) -> WorkflowState | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
    return WorkflowState.model_validate_json(row[0]) if row else None


def list_runs() -> list[str]:
    with closing(_connect()) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM runs ORDER BY updated DESC")]

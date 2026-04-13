from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import ApplicationRecord, ApplicationStatus, JobCard


class ApplicationTracker:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    linkedin_job_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    applied_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    linkedin_job_id TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    FOREIGN KEY (linkedin_job_id) REFERENCES applications(linkedin_job_id)
                );
                """
            )

    def upsert_discovered(self, job: JobCard, note: str = "Discovered in search") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM applications WHERE linkedin_job_id = ?", (job.linkedin_job_id,)
            ).fetchone()

            if row is None:
                conn.execute(
                    """
                    INSERT INTO applications (linkedin_job_id, title, company, location, status, note, applied_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.linkedin_job_id,
                        job.title,
                        job.company,
                        job.location,
                        ApplicationStatus.DISCOVERED.value,
                        note,
                        None,
                        now,
                    ),
                )
                self._add_history(conn, job.linkedin_job_id, None, ApplicationStatus.DISCOVERED.value, note)

    def update_status(self, linkedin_job_id: str, new_status: ApplicationStatus, note: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            current = conn.execute(
                "SELECT status, applied_at FROM applications WHERE linkedin_job_id = ?", (linkedin_job_id,)
            ).fetchone()
            if current is None:
                raise ValueError(f"Unknown application id: {linkedin_job_id}")

            applied_at = current["applied_at"]
            if new_status == ApplicationStatus.APPLIED and not applied_at:
                applied_at = now

            conn.execute(
                """
                UPDATE applications
                SET status = ?, note = ?, applied_at = ?, updated_at = ?
                WHERE linkedin_job_id = ?
                """,
                (new_status.value, note, applied_at, now, linkedin_job_id),
            )
            self._add_history(conn, linkedin_job_id, current["status"], new_status.value, note)

    def _add_history(self, conn: sqlite3.Connection, job_id: str, old_status: str | None, new_status: str, note: str) -> None:
        conn.execute(
            """
            INSERT INTO status_history (linkedin_job_id, old_status, new_status, note, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, old_status, new_status, note, datetime.now(timezone.utc).isoformat()),
        )

    def exists(self, linkedin_job_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM applications WHERE linkedin_job_id = ?", (linkedin_job_id,)
            ).fetchone()
        return row is not None

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT status, COUNT(*) AS count FROM applications GROUP BY status").fetchall()
        return {r["status"]: r["count"] for r in rows}

    def recent(self, limit: int = 20) -> list[ApplicationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT linkedin_job_id, title, company, location, status, note, applied_at, updated_at
                FROM applications
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        def parse_dt(value: str | None):
            return datetime.fromisoformat(value) if value else None

        return [
            ApplicationRecord(
                linkedin_job_id=r["linkedin_job_id"],
                title=r["title"],
                company=r["company"],
                location=r["location"],
                status=ApplicationStatus(r["status"]),
                note=r["note"],
                applied_at=parse_dt(r["applied_at"]),
                updated_at=parse_dt(r["updated_at"]),
            )
            for r in rows
        ]

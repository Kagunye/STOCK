import json
import sqlite3
from pathlib import Path
from typing import Optional

from .models import Job, JobScore, Proposal

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

# Job lifecycle: new -> filtered | scored -> drafted -> submitted | skipped
STATUSES = ("new", "filtered", "scored", "drafted", "submitted", "skipped", "hired")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    filter_reason TEXT,
    score INTEGER,
    score_data TEXT,
    proposal_data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class Store:
    def __init__(self, path: Path = DEFAULT_DB):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def add_job(self, job: Job) -> bool:
        """Insert a job; returns False if it was already stored."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO jobs (id, data) VALUES (?, ?)", (job.id, job.model_dump_json())
        )
        self.conn.commit()
        return cur.rowcount == 1

    def get(self, job_id: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def by_status(self, status: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC, created_at DESC", (status,)
        ).fetchall()

    def all(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()

    def mark_filtered(self, job_id: str, reason: str) -> None:
        self._update(job_id, status="filtered", filter_reason=reason)

    def save_score(self, job_id: str, score: JobScore) -> None:
        self._update(job_id, status="scored", score=score.score, score_data=score.model_dump_json())

    def save_proposal(self, job_id: str, proposal: Proposal) -> None:
        self._update(job_id, status="drafted", proposal_data=proposal.model_dump_json())

    def set_status(self, job_id: str, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}; expected one of {STATUSES}")
        self._update(job_id, status=status)

    def _update(self, job_id: str, **fields) -> None:
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))
        self.conn.commit()


def row_job(row: sqlite3.Row) -> Job:
    return Job.model_validate_json(row["data"])


def row_score(row: sqlite3.Row) -> Optional[JobScore]:
    return JobScore.model_validate_json(row["score_data"]) if row["score_data"] else None


def row_proposal(row: sqlite3.Row) -> Optional[Proposal]:
    return Proposal.model_validate_json(row["proposal_data"]) if row["proposal_data"] else None


def row_dict(row: sqlite3.Row) -> dict:
    return {
        "job": json.loads(row["data"]),
        "status": row["status"],
        "filter_reason": row["filter_reason"],
        "score": json.loads(row["score_data"]) if row["score_data"] else None,
        "proposal": json.loads(row["proposal_data"]) if row["proposal_data"] else None,
    }

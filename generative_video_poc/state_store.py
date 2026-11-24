"""Durable local project queue and clip checkpoints for the Termux controller."""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from generative_video_poc.contracts import ProjectSpec


class StoreError(RuntimeError):
    """A state transition would violate the local queue contract."""


class ProjectConflict(StoreError):
    """A project ID already exists with a different immutable spec."""


class LeaseError(StoreError):
    """A worker no longer owns a clip lease."""


_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_ERROR_CODE = re.compile(r"^[A-Z0-9_.:-]{1,100}$")


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _spec_payload(spec: ProjectSpec) -> dict[str, Any]:
    return {
        "kind": spec.kind,
        "target_duration_seconds": spec.target_duration_seconds,
        "aspect_ratio": spec.aspect_ratio,
        "width": spec.width,
        "height": spec.height,
        "clip_seconds": spec.clip_seconds,
        "prompt_template": spec.prompt_template,
        "clip_prompts": list(spec.clip_prompts),
    }


class ProjectStore:
    """SQLite-backed local project registry and resumable clip queue."""

    def __init__(self, root: Path | str | None = None):
        default_root = Path(os.environ.get("HOME", str(Path.home()))) / ".shortautopro"
        self.root = Path(root or default_root).expanduser().resolve()
        self.state_dir = self.root / "state"
        self.projects_dir = self.root / "projects"
        self.database = self.state_dir / "queue.sqlite3"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.database), timeout=15.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 15000")
        db.execute("PRAGMA synchronous = FULL")
        return db

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        try:
            yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._connection() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    spec_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clips (
                    project_id TEXT NOT NULL,
                    clip_index INTEGER NOT NULL,
                    start_seconds INTEGER NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    lease_owner TEXT,
                    lease_token TEXT,
                    lease_expires_at REAL,
                    output_path TEXT,
                    metadata_json TEXT,
                    error_code TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (project_id, clip_index),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_clips_queue ON clips(status, project_id, clip_index);
                CREATE INDEX IF NOT EXISTS idx_clips_lease ON clips(status, lease_expires_at);
                """
            )
            # Safe additive migration for a database created by an earlier POC revision.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(clips)").fetchall()}
            if "max_attempts" not in columns:
                db.execute("ALTER TABLE clips ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3")

    @staticmethod
    def validate_project_id(project_id: str) -> str:
        value = str(project_id or "").strip()
        if not _PROJECT_ID.fullmatch(value):
            raise ValueError("project_id must be 1-64 letters, numbers, '_' or '-'")
        return value

    def project_dir(self, project_id: str) -> Path:
        value = self.validate_project_id(project_id)
        root = self.projects_dir.resolve()
        target = (root / value).resolve()
        if not target.is_relative_to(root):
            raise ValueError("project path escapes the workspace")
        return target

    def create_project(
        self, project_id: str, spec: ProjectSpec | dict[str, Any], *, max_attempts: int = 3,
    ) -> dict[str, Any]:
        project_id = self.validate_project_id(project_id)
        if isinstance(spec, dict):
            spec = ProjectSpec.from_dict(spec)
        if not isinstance(spec, ProjectSpec):
            raise TypeError("spec must be a ProjectSpec or validated dictionary")
        if not 1 <= int(max_attempts) <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        encoded = _canonical_json(_spec_payload(spec))
        now = time.time()
        self.project_dir(project_id).mkdir(parents=True, exist_ok=True)

        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT spec_json FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            if existing:
                try:
                    previous_spec = json.loads(existing["spec_json"])
                except (TypeError, json.JSONDecodeError):
                    previous_spec = None
                if isinstance(previous_spec, dict):
                    # Backward compatibility for queue projects created before prompt_template existed.
                    previous_spec.setdefault("prompt_template", "")
                    previous_spec.setdefault("clip_prompts", [])
                if previous_spec != json.loads(encoded):
                    db.rollback()
                    raise ProjectConflict("project ID already exists with a different spec")
                db.commit()
                return self.get_project(project_id)

            db.execute(
                "INSERT INTO projects(project_id, spec_json, status, created_at, updated_at) "
                "VALUES (?, ?, 'QUEUED', ?, ?)",
                (project_id, encoded, now, now),
            )
            db.executemany(
                "INSERT INTO clips(project_id, clip_index, start_seconds, duration_seconds, "
                "status, max_attempts, updated_at) VALUES (?, ?, ?, ?, 'PENDING', ?, ?)",
                [
                    (project_id, clip.index, clip.start_seconds, clip.duration_seconds, int(max_attempts), now)
                    for clip in spec.clip_schedule()
                ],
            )
            db.commit()
        return self.get_project(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT p.project_id, p.status, p.created_at, p.updated_at, "
                "COUNT(c.clip_index) AS total_clips, "
                "SUM(CASE WHEN c.status='READY' THEN 1 ELSE 0 END) AS ready_clips, "
                "SUM(CASE WHEN c.status='FAILED' THEN 1 ELSE 0 END) AS failed_clips "
                "FROM projects p LEFT JOIN clips c ON c.project_id=p.project_id "
                "GROUP BY p.project_id ORDER BY p.created_at, p.project_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        project_id = self.validate_project_id(project_id)
        with self._connection() as db:
            project = db.execute(
                "SELECT * FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
            if not project:
                raise KeyError(f"project not found: {project_id}")
            clips = db.execute(
                "SELECT clip_index,start_seconds,duration_seconds,status,attempts,max_attempts,"
                "output_path,metadata_json,error_code,updated_at "
                "FROM clips WHERE project_id=? ORDER BY clip_index",
                (project_id,),
            ).fetchall()
        result = dict(project)
        result["spec"] = json.loads(result.pop("spec_json"))
        result["clips"] = []
        for row in clips:
            item = dict(row)
            metadata = item.pop("metadata_json")
            item["metadata"] = json.loads(metadata) if metadata else None
            result["clips"].append(item)
        statuses = [clip["status"] for clip in result["clips"]]
        result["progress"] = {
            "total": len(statuses), "ready": statuses.count("READY"),
            "running": statuses.count("RUNNING"), "pending": statuses.count("PENDING"),
            "failed": statuses.count("FAILED"),
        }
        return result

    @staticmethod
    def _refresh_project_status(db: sqlite3.Connection, project_id: str, now: float) -> None:
        rows = db.execute(
            "SELECT status,COUNT(*) AS n FROM clips WHERE project_id=? GROUP BY status",
            (project_id,),
        ).fetchall()
        counts = {row["status"]: row["n"] for row in rows}
        total = sum(counts.values())
        if total and counts.get("READY", 0) == total:
            status = "COMPLETE"
        elif counts.get("RUNNING", 0):
            status = "RUNNING"
        elif counts.get("PENDING", 0):
            status = "QUEUED"
        elif counts.get("FAILED", 0) and counts.get("READY", 0):
            status = "PARTIAL_FAILED"
        elif counts.get("FAILED", 0):
            status = "FAILED"
        else:
            status = "QUEUED"
        db.execute(
            "UPDATE projects SET status=?,updated_at=? WHERE project_id=?",
            (status, now, project_id),
        )

    def claim_next_clip(
        self, worker_id: str, *, project_id: str | None = None,
        lease_seconds: int = 900, now: float | None = None,
    ) -> dict[str, Any] | None:
        worker_id = str(worker_id or "").strip()
        if not worker_id or len(worker_id) > 100:
            raise ValueError("worker_id must contain 1-100 characters")
        if not 5 <= int(lease_seconds) <= 86400:
            raise ValueError("lease_seconds must be between 5 and 86400")
        if project_id is not None:
            project_id = self.validate_project_id(project_id)
        now = float(time.time() if now is None else now)
        token = secrets.token_urlsafe(24)

        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            expired = db.execute(
                "SELECT DISTINCT project_id FROM clips WHERE status='RUNNING' AND lease_expires_at<=?",
                (now,),
            ).fetchall()
            db.execute(
                "UPDATE clips SET status=CASE WHEN attempts>=max_attempts THEN 'FAILED' ELSE 'PENDING' END, "
                "lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,error_code='LEASE_EXPIRED',updated_at=? "
                "WHERE status='RUNNING' AND lease_expires_at<=?",
                (now, now),
            )
            for row in expired:
                self._refresh_project_status(db, row["project_id"], now)

            query = (
                "SELECT c.project_id,c.clip_index,c.start_seconds,c.duration_seconds,"
                "c.attempts,c.max_attempts "
                "FROM clips c JOIN projects p ON p.project_id=c.project_id "
                "WHERE c.status='PENDING' AND c.attempts<c.max_attempts"
            )
            params: list[Any] = []
            if project_id is not None:
                query += " AND c.project_id=?"
                params.append(project_id)
            query += " ORDER BY p.created_at,c.project_id,c.clip_index LIMIT 1"
            selected = db.execute(query, params).fetchone()
            if not selected:
                db.commit()
                return None

            expires = now + int(lease_seconds)
            updated = db.execute(
                "UPDATE clips SET status='RUNNING',attempts=attempts+1,lease_owner=?,lease_token=?,"
                "lease_expires_at=?,error_code=NULL,updated_at=? "
                "WHERE project_id=? AND clip_index=? AND status='PENDING'",
                (worker_id, token, expires, now, selected["project_id"], selected["clip_index"]),
            )
            if updated.rowcount != 1:
                db.rollback()
                raise StoreError("clip claim lost its transaction lock unexpectedly")
            self._refresh_project_status(db, selected["project_id"], now)
            db.commit()

        claim = dict(selected)
        attempt = int(selected["attempts"]) + 1
        output_dir = self.project_dir(selected["project_id"]) / "clips"
        claim.update({
            "status": "RUNNING", "attempts": attempt,
            "worker_id": worker_id, "lease_token": token, "lease_expires_at": expires,
            "output_dir": str(output_dir),
            "output_path": str(output_dir / f"clip_{int(selected['clip_index']):05d}_attempt_{attempt:02d}.mp4"),
        })
        return claim

    def renew_lease(
        self, project_id: str, clip_index: int, worker_id: str, lease_token: str,
        *, lease_seconds: int = 900, now: float | None = None,
    ) -> float:
        project_id = self.validate_project_id(project_id)
        if not 5 <= int(lease_seconds) <= 86400:
            raise ValueError("lease_seconds must be between 5 and 86400")
        now = float(time.time() if now is None else now)
        expires = now + int(lease_seconds)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            updated = db.execute(
                "UPDATE clips SET lease_expires_at=?,updated_at=? "
                "WHERE project_id=? AND clip_index=? AND status='RUNNING' "
                "AND lease_owner=? AND lease_token=? AND lease_expires_at>?",
                (expires, now, project_id, int(clip_index), worker_id, lease_token, now),
            )
            if updated.rowcount != 1:
                db.rollback()
                raise LeaseError("worker lease is expired or no longer owned")
            db.commit()
        return expires

    def complete_clip(
        self, project_id: str, clip_index: int, worker_id: str, lease_token: str,
        output_path: Path | str, validation: dict[str, Any], *, now: float | None = None,
    ) -> dict[str, Any]:
        project_id = self.validate_project_id(project_id)
        now = float(time.time() if now is None else now)
        output = Path(output_path).expanduser().resolve()
        project_root = self.project_dir(project_id).resolve()
        if not output.is_relative_to(project_root):
            raise ValueError("clip output must remain inside its project workspace")
        if not output.is_file() or output.stat().st_size <= 0:
            raise ValueError("clip output must be a non-empty file")
        if not isinstance(validation, dict):
            raise TypeError("validation metadata must be an object")
        if validation.get("status") != "GENERATED_AND_PROBED":
            raise ValueError("only an FFprobe-validated generated clip can be committed")
        if not validation.get("video_codec") or float(validation.get("duration_seconds") or 0) <= 0:
            raise ValueError("FFprobe validation must include a video codec and positive duration")
        encoded = _canonical_json(validation)

        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            updated = db.execute(
                "UPDATE clips SET status='READY',output_path=?,metadata_json=?,lease_owner=NULL,"
                "lease_token=NULL,lease_expires_at=NULL,error_code=NULL,updated_at=? "
                "WHERE project_id=? AND clip_index=? AND status='RUNNING' "
                "AND lease_owner=? AND lease_token=? AND lease_expires_at>?",
                (str(output), encoded, now, project_id, int(clip_index), worker_id, lease_token, now),
            )
            if updated.rowcount != 1:
                db.rollback()
                raise LeaseError("cannot complete clip: worker lease is expired or no longer owned")
            self._refresh_project_status(db, project_id, now)
            db.commit()
        return self.get_project(project_id)

    def fail_clip(
        self, project_id: str, clip_index: int, worker_id: str, lease_token: str,
        error_code: str, *, retryable: bool = True, now: float | None = None,
    ) -> str:
        project_id = self.validate_project_id(project_id)
        error_code = str(error_code or "").upper()
        if not _ERROR_CODE.fullmatch(error_code):
            raise ValueError("error_code must be a short, sanitized code")
        now = float(time.time() if now is None else now)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT attempts,max_attempts FROM clips WHERE project_id=? AND clip_index=? "
                "AND status='RUNNING' AND lease_owner=? AND lease_token=? AND lease_expires_at>?",
                (project_id, int(clip_index), worker_id, lease_token, now),
            ).fetchone()
            if not row:
                db.rollback()
                raise LeaseError("cannot fail clip: worker lease is expired or no longer owned")
            status = "PENDING" if retryable and int(row["attempts"]) < int(row["max_attempts"]) else "FAILED"
            db.execute(
                "UPDATE clips SET status=?,error_code=?,lease_owner=NULL,lease_token=NULL,"
                "lease_expires_at=NULL,updated_at=? WHERE project_id=? AND clip_index=?",
                (status, error_code, now, project_id, int(clip_index)),
            )
            self._refresh_project_status(db, project_id, now)
            db.commit()
        return status

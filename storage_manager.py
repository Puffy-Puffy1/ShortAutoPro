#!/usr/bin/env python3
"""Project-aware, lock-safe storage management for ShortAutoPro."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
OUT = BASE / "reports" / "evolution" / f"storage_{SID}.json"
LOCK_FILE = BASE / ".locks" / "production.lock"
PROVENANCE_DIR = BASE / "manifests" / "source_provenance_live"


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def env_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        value = default
    return max(low, min(high, value))


def env_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        value = default
    return max(low, min(high, value))


def path_size(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    except OSError:
        return 0


def project_paths() -> dict[str, list[Path]]:
    """Group all removable runtime directories by Short ID."""
    projects: dict[str, list[Path]] = {}
    images = BASE / "imagens"
    if images.is_dir():
        for path in images.glob("short_*"):
            if path.is_dir() and len(path.name) > len("short_"):
                projects.setdefault(path.name[len("short_"):], []).append(path)

    temp = BASE / "temp"
    if temp.is_dir():
        for path in temp.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                projects.setdefault(path.name, []).append(path)
    return projects


def project_mtime(paths: list[Path]) -> float:
    values: list[float] = []
    for path in paths:
        try:
            values.append(path.stat().st_mtime)
        except OSError:
            pass
    return max(values, default=0.0)


def lock_owner_sid() -> str:
    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        return str(data.get("short_id", "") or "").strip() if isinstance(data, dict) else ""
    except Exception:
        return ""


@contextmanager
def maintenance_lock(execute: bool) -> Iterator[tuple[bool, str]]:
    """Block external destructive cleanup while production/deploy is active.

    Internal post-production cleanup inherits SAP_PRODUCTION_LOCK_HELD=1 from
    main.py and therefore reuses the parent's already-held lock instead of
    attempting to lock the same file a second time.
    """
    if not execute or os.getenv("SAP_PRODUCTION_LOCK_HELD", "0") == "1":
        yield True, "inherited" if execute else "not_required"
        return

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_FILE.open("a+")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False, "production_or_deploy_active"
            return
        yield True, "acquired"
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()


def cleanup_stale_provenance(execute: bool) -> tuple[list[str], list[str]]:
    stale: list[str] = []
    failures: list[str] = []
    if not PROVENANCE_DIR.is_dir():
        return stale, failures
    for record in PROVENANCE_DIR.glob("source_*.json"):
        try:
            data = json.loads(record.read_text(encoding="utf-8"))
            local = Path(str(data.get("local_path", "") or "")).expanduser()
        except Exception:
            local = Path("")
        if local and local.is_file():
            continue
        stale.append(str(record.relative_to(BASE)))
        if execute:
            try:
                record.unlink(missing_ok=True)
            except OSError as exc:
                failures.append(f"{record.relative_to(BASE)}:{exc}")
    return stale, failures


def cleanup(execute: bool) -> dict[str, Any]:
    keep = env_int("SHORT_STORAGE_KEEP_PROJECTS", 3, 1, 20)
    days = env_int("SHORT_STORAGE_KEEP_DAYS", 7, 1, 90)
    cutoff = time.time() - days * 86400
    projects = project_paths()
    protected_ids = {item for item in (SID, lock_owner_sid()) if item}

    ordered = sorted(
        projects.items(),
        key=lambda item: project_mtime(item[1]),
        reverse=True,
    )
    completed = [(sid, paths) for sid, paths in ordered if sid not in protected_ids]
    selected: list[tuple[str, list[Path], str]] = []
    for index, (sid, paths) in enumerate(completed):
        old = project_mtime(paths) < cutoff
        if index >= keep or old:
            selected.append((sid, paths, "age" if old else "retention"))

    freed = sum(path_size(path) for _, paths, _ in selected for path in paths)
    removed: list[dict[str, Any]] = []
    failures: list[str] = []
    if execute:
        for sid, paths, reason in selected:
            removed_paths: list[str] = []
            for path in paths:
                rel = str(path.relative_to(BASE))
                try:
                    shutil.rmtree(path)
                    removed_paths.append(rel)
                except OSError as exc:
                    failures.append(f"{rel}:{exc}")
            removed.append({"short_id": sid, "paths": removed_paths, "reason": reason})

        for path in BASE.rglob("__pycache__"):
            if path.is_dir():
                try:
                    shutil.rmtree(path)
                except OSError as exc:
                    failures.append(f"{path.relative_to(BASE)}:{exc}")
    else:
        removed = [
            {
                "short_id": sid,
                "paths": [str(path.relative_to(BASE)) for path in paths],
                "reason": reason,
            }
            for sid, paths, reason in selected
        ]

    stale_provenance, provenance_failures = cleanup_stale_provenance(execute)
    failures.extend(provenance_failures)
    return {
        "execute": execute,
        "keep_projects": keep,
        "keep_days": days,
        "protected_short_ids": sorted(protected_ids),
        "project_count": len(projects),
        "selected_projects": len(selected),
        "removed": removed,
        "stale_provenance": stale_provenance,
        "estimated_freed_bytes": freed,
        "failures": failures,
        "status": "PASS" if not failures else "WARN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["preflight", "cleanup", "status"], nargs="?", default="status")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    usage = shutil.disk_usage(BASE)
    min_free_gb = env_float("SAP_MIN_FREE_GB", 1.2, 0.25, 64.0)
    min_free = int(min_free_gb * 1024**3)
    payload: dict[str, Any] = {
        "short_id": SID,
        "version": "2.0",
        "disk": {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "free_gb": round(usage.free / 1024**3, 2),
            "min_free_gb": round(min_free / 1024**3, 2),
        },
    }

    if args.command == "preflight":
        payload["status"] = "PASS" if usage.free >= min_free else "BLOCK"
        atomic(OUT, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["status"] == "PASS" else 1

    if args.command == "cleanup":
        with maintenance_lock(args.execute) as (lock_ok, lock_mode):
            payload["maintenance_lock"] = lock_mode
            if not lock_ok:
                payload["status"] = "BLOCK"
                payload["reason"] = "production_or_deploy_active"
                atomic(OUT, payload)
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 1
            payload["cleanup"] = cleanup(args.execute)
            payload["status"] = payload["cleanup"]["status"]
    else:
        payload["projects"] = len(project_paths())
        payload["status"] = "PASS"

    atomic(OUT, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

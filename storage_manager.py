#!/usr/bin/env python3
"""Concurrency-safe storage preflight and cleanup for ShortAutoPro 3.1."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
OUT = BASE / "reports" / "evolution" / f"storage_{SID}.json"
PRODUCTION_LOCK = BASE / ".locks" / "production.lock"


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if value != value or value in {float("inf"), float("-inf")}:
        value = default
    return max(minimum, min(maximum, value))


def size(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    except OSError:
        return 0


def candidates() -> list[Path]:
    found: list[Path] = []
    for root, pattern in ((BASE / "imagens", "short_*"), (BASE / "temp", "*")):
        if root.is_dir():
            found.extend(item for item in root.glob(pattern) if item.is_dir())
    return found


def protected(path: Path) -> bool:
    if not SID:
        return False
    return path.name in {SID, f"short_{SID}"}


class CleanupGuard:
    """Prevent external cleanup while the canonical production lock is held."""

    def __init__(self):
        self.handle = None
        self.inherited = os.getenv("SAP_PRODUCTION_LOCK_HELD", "").strip() == SID and bool(SID)

    def __enter__(self):
        if self.inherited:
            return self
        PRODUCTION_LOCK.parent.mkdir(parents=True, exist_ok=True)
        self.handle = PRODUCTION_LOCK.open("a+")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            self.handle = None
            raise RuntimeError("cleanup bloqueado: produção/atualização ativa") from exc
        return self

    def __exit__(self, *_):
        if self.handle:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.handle.close()
            self.handle = None


def cleanup(execute: bool) -> dict[str, Any]:
    keep = env_int("SHORT_STORAGE_KEEP_PROJECTS", 3, 1, 20)
    days = env_int("SHORT_STORAGE_KEEP_DAYS", 7, 1, 90)
    cutoff = time.time() - days * 86400

    items = sorted(
        candidates(),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    removable_pool = [path for path in items if not protected(path)]
    remove: list[Path] = []
    for index, path in enumerate(removable_pool):
        try:
            old = path.stat().st_mtime < cutoff
        except OSError:
            old = False
        if index >= keep or old:
            remove.append(path)

    estimated = sum(size(path) for path in remove)
    removed: list[str] = []
    errors: list[str] = []

    if execute:
        with CleanupGuard():
            for path in remove:
                try:
                    shutil.rmtree(path)
                    removed.append(str(path.relative_to(BASE)))
                except OSError as exc:
                    errors.append(f"remove:{path.relative_to(BASE)}:{type(exc).__name__}")
            for path in BASE.rglob("__pycache__"):
                if path.is_dir():
                    try:
                        shutil.rmtree(path)
                    except OSError as exc:
                        errors.append(f"pycache:{path.relative_to(BASE)}:{type(exc).__name__}")

    return {
        "execute": execute,
        "keep_projects": keep,
        "keep_days": days,
        "candidates_for_removal": [str(path.relative_to(BASE)) for path in remove],
        "removed": removed if execute else [],
        "estimated_freed_bytes": estimated,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["preflight", "cleanup", "status"], nargs="?", default="status")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    usage = shutil.disk_usage(BASE)
    min_free_gb = env_float("SAP_MIN_FREE_GB", 1.2, 0.25, 50.0)
    min_free = int(min_free_gb * 1024**3)
    payload: dict[str, Any] = {
        "short_id": SID,
        "version": "STORAGE_3_1",
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
        try:
            result = cleanup(args.execute)
            payload["cleanup"] = result
            payload["status"] = "WARN" if result["errors"] else "PASS"
            # Cleanup happens after a validated export and is an optimization.
            # Individual deletion failures are reported but never invalidate the
            # already approved production.
            code = 0
        except RuntimeError as exc:
            payload["cleanup"] = {"execute": args.execute, "errors": [str(exc)]}
            payload["status"] = "BLOCK"
            code = 2
    else:
        payload["status"] = "PASS"
        code = 0

    atomic(OUT, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

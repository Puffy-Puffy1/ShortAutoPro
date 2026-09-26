#!/usr/bin/env python3
"""Canonical sequential batch runtime for ShortAutoPro.

One source of truth for batch identity, per-item state, fresh-vs-resume,
retries, failure classification, locking, reports and exact release checks.
The runtime intentionally executes complete Shorts sequentially on mobile.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro"))))
QUEUE = BASE / "queue"
STATE_FILE = QUEUE / "batch_state.json"
LOCK_FILE = QUEUE / ".batch_runtime.lock"
REPORT_DIR = BASE / "reports" / "batch"
LOG_DIR = BASE / "logs" / "lotes"
VERSION = "BATCH_STATE_3.0_PER_ITEM"
ITEM_STATES = {
    "queued", "running", "retry_pending", "recovering", "completed",
    "failed_permanent", "blocked_global", "cancelled",
}
TRANSIENT_ENV = {
    "SHORT_ID", "SAP_REUSE_SHORT_ID", "SHORT_TOPIC_EXACT", "SHORT_ALLOW_REPEAT_TOPIC",
    "SAP_MEDIA_RECOVERY", "SAP_STAGE6_RECOVERY", "SAP_RESUME", "SAP_RESUME_MODE",
    "SAP_VISUAL_OVERRIDE", "SAP_MEDIA_OVERRIDE", "SAP_RECOVERY_SHORT_ID",
}
GLOBAL_CODES = {"STORAGE_LOW", "CONFIG_INVALID"}
PERMANENT_CODES = {"MEDIA_SEMANTIC_FAILURE", "AI_CONTENT_BLOCK"}
MAX_TOTAL = 10


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def item_short_id(batch_id: str, index: int) -> str:
    return f"{batch_id}_{index:02d}"


def artifact_paths(short_id: str) -> tuple[Path, ...]:
    return (
        BASE / ".sap_state" / f"pipeline_{short_id}.json",
        BASE / "roteiros" / f"scene_map_{short_id}.json",
        BASE / "roteiros" / f"short_{short_id}.txt",
        BASE / "imagens" / f"short_{short_id}",
        BASE / "audios" / f"short_{short_id}.mp3",
        BASE / "videos" / f"short_v6_{short_id}.mp4",
        BASE / "manifests" / f"{short_id}_release.json",
    )


def artifacts_exist(short_id: str) -> bool:
    return any(path.exists() for path in artifact_paths(short_id))


def last_stage(short_id: str) -> str:
    candidates = [
        BASE / ".sap_state" / f"pipeline_{short_id}.json",
        BASE / ".sap_state" / f"{short_id}.json",
    ]
    for path in candidates:
        data = read_json(path)
        value = data.get("current_stage") or data.get("last_stage") or data.get("stage")
        if value:
            return str(value)
    return ""


def release_ok(short_id: str) -> bool:
    guard = BASE / "release_artifact_guard.py"
    if not guard.is_file():
        return False
    proc = subprocess.run(
        [sys.executable, str(guard), "--short-id", short_id],
        cwd=BASE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def output_path(short_id: str) -> str:
    path = BASE / "videos" / f"short_v6_{short_id}.mp4"
    return str(path) if path.is_file() else ""


def _tail_text(path: Path, limit: int = 65536) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def run_logged(
    cmd: list[str],
    *,
    env: dict[str, str],
    log_path: Path,
    timeout: int,
) -> tuple[int, str, bool]:
    """Run one Short without retaining its complete output in RAM.

    A dedicated process group lets batch interruption/timeout terminate the
    launched main/resume process and its descendants instead of leaving an
    orphaned FFmpeg/Piper/Whisper tree.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timed_out = False
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{now()}] BATCH_SUBPROCESS_START cmd={' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=BASE,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                returncode = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                returncode = proc.wait()
        except BaseException:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                proc.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            raise
        finally:
            log.write(f"[{now()}] BATCH_SUBPROCESS_END timeout={timed_out}\n")
            log.flush()
    return returncode, _tail_text(log_path), timed_out


def clean_env(short_id: str) -> dict[str, str]:
    env = os.environ.copy()
    for key in TRANSIENT_ENV:
        env.pop(key, None)
    env["SHORTAUTOPRO_BASE"] = str(BASE)
    env["SHORT_ID"] = short_id
    env["SAP_BATCH_MODE"] = "1"
    return env


@dataclass(frozen=True)
class Failure:
    code: str
    kind: str
    message: str


def classify_failure(text: str, returncode: int) -> Failure:
    upper = (text or "").upper()
    rules = [
        ("STORAGE_LOW", "GLOBAL_BLOCKER", ("STORAGE_LOW", "ESPAÇO INSUFICIENTE", "NO SPACE LEFT")),
        ("CONFIG_INVALID", "GLOBAL_BLOCKER", ("CONFIG.SH", "CONFIG_INVALID", "FFMPEG AUSENTE", "PYTHON AUSENTE")),
        ("MEDIA_RATE_LIMIT", "RECOVERABLE", ("429", "RATE_LIMIT", "RETRY-AFTER")),
        ("MEDIA_PROVIDER_TIMEOUT", "RECOVERABLE", ("PROVIDER_TIMEOUT", "REQUEST TIMEOUT", "TIMEOUT")),
        ("MEDIA_INCOMPLETE", "RECOVERABLE", ("MEDIA_INCOMPLETE", "MEDIA_STAGE_RUNTIME=EXHAUSTED", "MÍDIA INCOMPLETA")),
        ("RENDER_TIMEOUT", "RECOVERABLE", ("RENDER_TIMEOUT", "FFMPEG", "EXCEDEU TIMEOUT")),
        ("RENDER_INVALID", "RECOVERABLE", ("RENDER_INVALID", "RENDERER TERMINOU SEM", "FFPROBE")),
        ("QA_BLOCK", "RECOVERABLE", ("QA_BLOCK", "VISUAL QA", "QUALITY GATE")),
        ("RELEASE_BLOCK", "RECOVERABLE", ("RELEASE GATE", "RELEASE_BLOCK")),
        ("AI_TIMEOUT", "RECOVERABLE", ("GEMINI", "503", "AI_TIMEOUT")),
        ("AI_CONTENT_BLOCK", "PERMANENT_ITEM", ("PROHIBITED_CONTENT", "PROMPT BLOCKED", "AI_CONTENT_BLOCK")),
        ("MEDIA_SEMANTIC_FAILURE", "PERMANENT_ITEM", ("SEMANTIC", "EXPLICIT MUST", "MUST FAILED")),
        ("LOCK_ACTIVE", "RECOVERABLE", ("JÁ ESTÁ EM ANDAMENTO", "LOCK_ACTIVE")),
        ("STATE_CORRUPT", "RECOVERABLE", ("STATE_CORRUPT", "JSON INVÁLIDO", "ESTADO INVÁLIDO")),
    ]
    for code, kind, needles in rules:
        if any(n in upper for n in needles):
            return Failure(code, kind, (text or "")[-500:])
    return Failure("UNKNOWN_EXCEPTION", "RECOVERABLE", (text or f"exit={returncode}")[-500:])


class BatchLock:
    def __init__(self) -> None:
        self.handle = None

    def __enter__(self):
        QUEUE.mkdir(parents=True, exist_ok=True)
        self.handle = LOCK_FILE.open("a+")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            self.handle = None
            raise RuntimeError("BATCH_LOCK_ACTIVE") from exc
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(json.dumps({"pid": os.getpid(), "started_at": now()}))
        self.handle.flush()
        return self

    def __exit__(self, *_):
        if self.handle:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            finally:
                self.handle.close()
                self.handle = None
        # Keep inode stable; flock ownership is tied to the open descriptor.


def make_state(total: int) -> dict[str, Any]:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    batch_id = f"{stamp}_{os.getpid()}"
    return {
        "version": VERSION,
        "batch_id": batch_id,
        "total": total,
        "status": "running",
        "created_at": now(),
        "updated_at": now(),
        "items": [
            {
                "index": i,
                "short_id": item_short_id(batch_id, i),
                "status": "queued",
                "attempts": 0,
                "recovery_count": 0,
                "created_at": now(),
                "updated_at": now(),
                "last_stage": "",
                "last_error": "",
                "error_class": "",
                "last_exit_code": None,
                "topic": "",
                "release": "UNKNOWN",
                "output_path": "",
                "log_path": "",
            }
            for i in range(1, total + 1)
        ],
    }


def migrate_legacy(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("version") == VERSION and isinstance(data.get("items"), list):
        return data
    batch_id = str(data.get("batch_id") or datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    total = max(1, min(int(data.get("total") or 1), MAX_TOTAL))
    current = max(0, min(int(data.get("current") or 0), total))
    legacy_status = str(data.get("status") or "running")
    items = []
    for i in range(1, total + 1):
        sid = item_short_id(batch_id, i)
        if i <= current:
            status = "completed" if release_ok(sid) else ("retry_pending" if artifacts_exist(sid) else "queued")
        else:
            status = "queued"
        if legacy_status == "retry_pending" and i == current + 1:
            status = "retry_pending" if artifacts_exist(sid) else "queued"
        items.append({
            "index": i, "short_id": sid, "status": status,
            "attempts": 0, "recovery_count": 0, "created_at": now(), "updated_at": now(),
            "last_stage": "", "last_error": "migrated_from_contiguous_state" if status == "retry_pending" else "",
            "error_class": "", "last_exit_code": None, "topic": "", "release": "PUBLISH" if status == "completed" else "UNKNOWN",
            "output_path": output_path(item_short_id(batch_id, i)), "log_path": "",
        })
    return {
        "version": VERSION, "batch_id": batch_id, "total": total,
        "status": "running", "created_at": str(data.get("updated_at") or now()),
        "updated_at": now(), "items": items, "migrated_from": str(data.get("version") or "legacy"),
    }


def load_state() -> dict[str, Any]:
    data = read_json(STATE_FILE)
    if not data:
        raise RuntimeError("BATCH_STATE_MISSING")
    migrated = migrate_legacy(data)
    if migrated != data:
        save_state(migrated)
    validate_state(migrated)
    return migrated


def validate_state(state: dict[str, Any]) -> None:
    if state.get("version") != VERSION:
        raise RuntimeError("STATE_CORRUPT version")
    items = state.get("items")
    if not isinstance(items, list) or len(items) != int(state.get("total") or 0):
        raise RuntimeError("STATE_CORRUPT items")
    seen = set()
    for item in items:
        sid = str(item.get("short_id") or "")
        if not sid or sid in seen:
            raise RuntimeError("STATE_CORRUPT duplicate_short_id")
        seen.add(sid)
        if str(item.get("status")) not in ITEM_STATES:
            raise RuntimeError("STATE_CORRUPT item_status")


def save_state(state: dict[str, Any]) -> None:
    state["version"] = VERSION
    state["updated_at"] = now()
    validate_state(state)
    atomic_json(STATE_FILE, state)


def summary(state: dict[str, Any]) -> dict[str, int]:
    result = {name: 0 for name in ITEM_STATES}
    for item in state["items"]:
        result[str(item["status"])] += 1
    return result


def write_report(state: dict[str, Any]) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    batch_id = state["batch_id"]
    counts = summary(state)
    payload = {
        "batch_id": batch_id, "total": state["total"], "status": state["status"],
        "updated_at": state["updated_at"], "counts": counts, "items": state["items"],
    }
    json_path = REPORT_DIR / f"batch_{batch_id}.json"
    txt_path = REPORT_DIR / f"batch_{batch_id}.txt"
    atomic_json(json_path, payload)
    lines = [
        f"BATCH: {batch_id}", f"TOTAL: {state['total']}",
        f"COMPLETED: {counts['completed']}",
        f"FAILED_PERMANENT: {counts['failed_permanent']}",
        f"RETRY_PENDING: {counts['retry_pending']}",
        f"BLOCKED_GLOBAL: {counts['blocked_global']}", "",
    ]
    for item in state["items"]:
        lines.append(
            f"{item['index']:02d} {str(item['status']).upper()} ID={item['short_id']} "
            f"attempts={item['attempts']} recovery={item['recovery_count']} "
            f"error={item.get('error_class') or '-'} release={item.get('release') or 'UNKNOWN'}"
        )
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, txt_path


def command_for(item: dict[str, Any]) -> tuple[list[str], str]:
    sid = str(item["short_id"])
    if release_ok(sid):
        return [], "complete"
    partial = artifacts_exist(sid) or str(item["status"]) in {"retry_pending", "recovering", "running"}
    if partial:
        return [sys.executable, str(BASE / "main.py"), "resume", "--short-id", sid], "resume"
    return [sys.executable, str(BASE / "main.py"), "run"], "fresh"


def run_item(state: dict[str, Any], item: dict[str, Any], recovering: bool = False) -> Failure | None:
    sid = str(item["short_id"])
    index = int(item["index"])
    if release_ok(sid):
        item.update(status="completed", release="PUBLISH", output_path=output_path(sid), updated_at=now())
        save_state(state)
        print(f"BATCH_ITEM_COMPLETE index={index} short_id={sid} release=PUBLISH existing=YES")
        return None

    cmd, mode = command_for(item)
    if mode == "complete":
        return None
    item["status"] = "recovering" if recovering or mode == "resume" else "running"
    item["attempts"] = int(item.get("attempts") or 0) + 1
    if mode == "resume":
        item["recovery_count"] = int(item.get("recovery_count") or 0) + 1
    item["updated_at"] = now()
    save_state(state)

    print(f"BATCH_ITEM_START index={index} short_id={sid} attempt={item['attempts']}")
    print(f"BATCH_ITEM_MODE={mode.upper()} short_id={sid}")

    env = clean_env(sid)
    try:
        item_timeout = int(os.getenv("SAP_BATCH_ITEM_TIMEOUT_SECONDS", "10800") or 10800)
    except ValueError:
        item_timeout = 10800
    item_timeout = max(600, min(item_timeout, 21600))
    log_path = LOG_DIR / f"batch_{state['batch_id']}_item_{index:02d}_{sid}.log"
    item["log_path"] = str(log_path)
    save_state(state)
    returncode, text, timed_out = run_logged(
        cmd,
        env=env,
        log_path=log_path,
        timeout=item_timeout,
    )
    if text:
        # Keep console diagnostics bounded while the complete output remains
        # available in the per-item log.
        sys.stdout.write(text[-12000:])
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    item["last_exit_code"] = int(returncode)
    item["last_stage"] = last_stage(sid)

    if returncode == 0 and release_ok(sid):
        item.update(
            status="completed", release="PUBLISH", output_path=output_path(sid),
            last_error="", error_class="", updated_at=now(),
        )
        save_state(state)
        print(f"BATCH_ITEM_COMPLETE index={index} short_id={sid} release=PUBLISH")
        return None

    if timed_out:
        failure = Failure("ITEM_TIMEOUT", "RECOVERABLE", f"batch item exceeded {item_timeout}s")
    else:
        failure = classify_failure(text if returncode else "RELEASE_BLOCK", returncode)
    item["last_error"] = failure.message
    item["error_class"] = failure.code
    item["release"] = "BLOCK"
    item["updated_at"] = now()
    if failure.kind == "GLOBAL_BLOCKER":
        item["status"] = "blocked_global"
    elif failure.kind == "PERMANENT_ITEM":
        item["status"] = "failed_permanent"
    else:
        item["status"] = "retry_pending"
    save_state(state)
    print(
        f"BATCH_ITEM_DEFERRED index={index} short_id={sid} "
        f"reason={failure.code} kind={failure.kind}"
    )
    return failure


def adaptive_cooldown(state: dict[str, Any]) -> int:
    try:
        base = int(os.getenv("SHORT_BATCH_COOLDOWN", "8"))
    except ValueError:
        base = 8
    base = max(2, min(base, 120))
    recent = state["items"]
    if recent:
        code = str(recent[-1].get("error_class") or "")
        if code == "MEDIA_RATE_LIMIT":
            return max(base, 30)
        if code in {"MEDIA_PROVIDER_TIMEOUT", "AI_TIMEOUT"}:
            return max(base, 12)
    return base


def finalize_status(state: dict[str, Any]) -> None:
    counts = summary(state)
    if counts["blocked_global"]:
        state["status"] = "blocked_global"
    elif counts["retry_pending"] or counts["running"] or counts["recovering"] or counts["queued"]:
        state["status"] = "incomplete"
    elif counts["failed_permanent"]:
        state["status"] = "completed_with_errors"
    else:
        state["status"] = "completed"
    save_state(state)
    write_report(state)


def execute(state: dict[str, Any], *, max_attempts: int, recovery_rounds: int) -> int:
    validate_state(state)
    stop = False

    # A persisted "completed" label is advisory. The exact release guard is
    # authoritative on every resume so stale/corrupt state cannot produce a
    # false batch success.
    for item in state["items"]:
        if item["status"] == "completed" and not release_ok(str(item["short_id"])):
            item["status"] = "retry_pending" if artifacts_exist(str(item["short_id"])) else "queued"
            item["release"] = "BLOCK"
            item["error_class"] = "RELEASE_BLOCK"
            item["last_error"] = "persisted completion failed exact release revalidation"
            item["updated_at"] = now()
    save_state(state)

    for item in state["items"]:
        if item["status"] in {"completed", "failed_permanent", "cancelled"}:
            continue
        if int(item.get("attempts") or 0) >= max_attempts:
            item["status"] = "failed_permanent"
            item["error_class"] = item.get("error_class") or "MAX_ATTEMPTS"
            save_state(state)
            continue
        failure = run_item(state, item, recovering=item["status"] != "queued")
        if failure and failure.kind == "GLOBAL_BLOCKER":
            stop = True
            break
        print(f"BATCH_CONTINUE next={int(item['index']) + 1}")
        if int(item["index"]) < int(state["total"]):
            time.sleep(adaptive_cooldown(state))

    if not stop:
        for round_no in range(1, recovery_rounds + 1):
            pending = [i for i in state["items"] if i["status"] == "retry_pending" and int(i.get("attempts") or 0) < max_attempts]
            if not pending:
                break
            print(f"BATCH_RECOVERY_ROUND={round_no} pending={len(pending)}")
            for item in pending:
                failure = run_item(state, item, recovering=True)
                if failure and failure.kind == "GLOBAL_BLOCKER":
                    stop = True
                    break
                if item["status"] == "retry_pending":
                    delay = min(60, adaptive_cooldown(state) * (round_no + 1))
                    print(f"BATCH_ITEM_RETRY attempt={item['attempts']} reason={item.get('error_class')} backoff={delay}s")
                    time.sleep(delay)
            if stop:
                break

    for item in state["items"]:
        if item["status"] == "retry_pending" and int(item.get("attempts") or 0) >= max_attempts:
            item["status"] = "failed_permanent"
            item["error_class"] = item.get("error_class") or "MAX_ATTEMPTS"
    finalize_status(state)
    return 0 if state["status"] == "completed" else 1


def status_text(state: dict[str, Any]) -> str:
    counts = summary(state)
    lines = [
        f"BATCH_ID={state['batch_id']}", f"STATUS={state['status']}",
        f"TOTAL={state['total']}", f"COMPLETED={counts['completed']}",
        f"RETRY_PENDING={counts['retry_pending']}", f"FAILED_PERMANENT={counts['failed_permanent']}",
    ]
    for item in state["items"]:
        lines.append(
            f"ITEM={item['index']} SHORT_ID={item['short_id']} STATUS={item['status']} "
            f"ATTEMPTS={item['attempts']} ERROR={item.get('error_class') or '-'}"
        )
    return "\n".join(lines)


def preflight(total: int = 1) -> None:
    required = ["main.py", "release_artifact_guard.py", "config.sh"]
    missing = [name for name in required if not (BASE / name).is_file()]
    if missing:
        raise RuntimeError("CONFIG_INVALID missing=" + ",".join(missing))
    try:
        usage = __import__("shutil").disk_usage(BASE)
        reserve_mb = int(os.getenv("SAP_BATCH_MIN_FREE_MB", "768"))
        per_short_mb = int(os.getenv("SAP_BATCH_ESTIMATED_SHORT_MB", "220"))
        reserve_mb = max(256, min(reserve_mb, 8192))
        per_short_mb = max(64, min(per_short_mb, 2048))
        min_free = max(reserve_mb, 256 + per_short_mb * max(1, int(total))) * 1024 * 1024
        if usage.free < min_free:
            raise RuntimeError(
                f"STORAGE_LOW free={usage.free} required={min_free} total={total}"
            )
    except FileNotFoundError:
        raise RuntimeError("CONFIG_INVALID base_missing")


def cli() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro canonical batch runtime")
    sub = parser.add_subparsers(dest="command")
    start = sub.add_parser("run")
    start.add_argument("count", type=int, nargs="?", default=3)
    resume = sub.add_parser("resume")
    status = sub.add_parser("status")
    sub.add_parser("report")
    for p in (start, resume):
        p.add_argument("--max-attempts", type=int, default=int(os.getenv("SAP_BATCH_MAX_ATTEMPTS", "3")))
        p.add_argument("--recovery-rounds", type=int, default=int(os.getenv("SAP_BATCH_RECOVERY_ROUNDS", "2")))
    args = parser.parse_args()
    command = args.command or "run"

    if command == "status":
        state = load_state()
        print(status_text(state))
        return 0
    if command == "report":
        state = load_state()
        j, t = write_report(state)
        print(f"BATCH_REPORT_JSON={j}\nBATCH_REPORT_TEXT={t}")
        return 0

    if command == "run":
        requested_total = max(1, min(int(args.count), MAX_TOTAL))
    else:
        requested_total = int(load_state().get("total") or 1)
    preflight(requested_total)
    with BatchLock():
        if command == "run":
            total = requested_total
            state = make_state(total)
            save_state(state)
        else:
            state = load_state()
            if state["status"] == "completed":
                print(status_text(state))
                return 0
            # Recover an item left RUNNING by SIGINT/SIGTERM/process death.
            for item in state["items"]:
                if item["status"] == "running":
                    item["status"] = "retry_pending" if artifacts_exist(item["short_id"]) else "queued"
            state["status"] = "running"
            save_state(state)

        def interrupted(signum, _frame):
            state["status"] = "interrupted"
            for item in state["items"]:
                if item["status"] in {"running", "recovering"}:
                    item["status"] = "retry_pending" if artifacts_exist(item["short_id"]) else "queued"
                    item["last_error"] = f"signal_{signum}"
                    item["error_class"] = "INTERRUPTED"
            save_state(state)
            write_report(state)
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, interrupted)
        signal.signal(signal.SIGTERM, interrupted)
        try:
            return execute(
                state,
                max_attempts=max(1, min(int(args.max_attempts), 5)),
                recovery_rounds=max(0, min(int(args.recovery_rounds), 4)),
            )
        except KeyboardInterrupt:
            print("BATCH_INTERRUPTED=YES")
            return 130


if __name__ == "__main__":
    raise SystemExit(cli())

#!/usr/bin/env python3
"""Execute ShortAutoPro client jobs safely and resumably.

Jobs are created by client_job_create.py and live under the ignored runtime
reports/evolution/client_jobs directory. English production is intentionally
blocked until its dedicated future phase.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from subprocess_guard import run_group
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
JOBS = BASE / "reports" / "evolution" / "client_jobs"
PROFILE_RUN = BASE / "profile_run.sh"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def load_job(job_id: str | None) -> tuple[Path, dict[str, Any]]:
    if job_id:
        path = JOBS / f"{job_id}.json"
    else:
        candidates = sorted(JOBS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if JOBS.exists() else []
        if not candidates:
            raise SystemExit("ERRO: nenhum job de cliente encontrado.")
        path = candidates[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERRO: job inválido ({path}): {exc}")
    if not isinstance(data, dict):
        raise SystemExit("ERRO: job precisa ser um objeto JSON.")
    return path, data


def sanitize_id(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)
    return clean[:60].strip("_") or "client"


def validate_job(job: dict[str, Any]) -> None:
    required = ("job_id", "client", "topic", "quantity", "profile")
    missing = [key for key in required if not str(job.get(key, "")).strip()]
    if missing:
        raise SystemExit("ERRO: job incompleto: " + ", ".join(missing))
    try:
        qty = int(job.get("quantity"))
    except (TypeError, ValueError):
        raise SystemExit("ERRO: quantity inválida.")
    if not 1 <= qty <= 100:
        raise SystemExit("ERRO: quantity precisa estar entre 1 e 100.")
    language = str(job.get("language", "pt-BR")).strip() or "pt-BR"
    if not language.lower().startswith("pt"):
        raise SystemExit("ERRO: jobs em inglês estão desabilitados nesta fase; use PT-BR.")
    if not PROFILE_RUN.is_file():
        raise SystemExit(f"ERRO: profile_run.sh não encontrado: {PROFILE_RUN}")


def ensure_items(job: dict[str, Any]) -> list[dict[str, Any]]:
    qty = int(job["quantity"])
    old_items = job.get("items", []) if isinstance(job.get("items"), list) else []
    by_index = {
        int(item.get("index")): item
        for item in old_items
        if isinstance(item, dict) and str(item.get("index", "")).isdigit()
    }
    items = []
    for index in range(1, qty + 1):
        item = by_index.get(index, {"index": index, "status": "PENDING"})
        items.append(item)
    job["items"] = items
    return items


def output_ok(short_id: str) -> bool:
    video = BASE / "videos" / f"short_v6_{short_id}.mp4"
    quality = BASE / "manifests" / f"{short_id}_quality.json"
    if not video.is_file() or video.stat().st_size <= 0 or not quality.is_file():
        return False
    try:
        data = json.loads(quality.read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(data, dict) and bool(data.get("approved"))


def all_items_approved(items: list[dict[str, Any]]) -> bool:
    return all(
        item.get("status") == "PASS"
        and output_ok(str(item.get("short_id")))
        for item in items
    )


def run_job(path: Path, job: dict[str, Any], execute: bool) -> int:
    validate_job(job)
    items = ensure_items(job)
    job_id = sanitize_id(str(job["job_id"]))
    profile = str(job.get("profile", "default")).strip() or "default"
    topic = str(job.get("topic", "")).strip()
    language = "pt-BR"
    topic_mode = str(job.get("topic_mode", "theme")).strip().lower()
    if topic_mode not in {"theme", "exact"}:
        raise SystemExit("ERRO: topic_mode precisa ser theme ou exact.")

    print("========================================")
    print(" SHORTAUTOPRO - CLIENT JOB RUNNER")
    print("========================================")
    print(f"Job: {job_id}")
    print(f"Cliente: {job['client']}")
    print(f"Tema/assunto: {topic}")
    print(f"Modo: {topic_mode}")
    print(f"Perfil: {profile}")
    print(f"Quantidade: {job['quantity']}")
    print(f"Execução real: {'SIM' if execute else 'NÃO (dry-run)'}")
    print()

    job["status"] = "RUNNING" if execute else "DRY_RUN"
    job["updated_at"] = now_iso()
    atomic_json(path, job)

    for item in items:
        index = int(item["index"])
        sid = str(item.get("short_id") or f"client_{job_id}_{index:03d}")
        item["short_id"] = sid

        if item.get("status") == "PASS" and output_ok(sid):
            print(f"[{index}/{job['quantity']}] já aprovado: {sid} — pulando.")
            continue

        print(f"[{index}/{job['quantity']}] {sid}")
        if not execute:
            print(f"  DRY-RUN: bash profile_run.sh {profile}")
            continue

        env = os.environ.copy()
        env["SHORT_ID"] = sid
        env["SAP_CHANNEL_PROFILE"] = profile
        env["SHORT_LANGUAGE"] = language
        if topic_mode == "exact":
            env["SHORT_TOPIC_EXACT"] = topic
            env.pop("SHORT_TEMA", None)
        else:
            env["SHORT_TEMA"] = topic
            env.pop("SHORT_TOPIC_EXACT", None)

        item["status"] = "RUNNING"
        item["started_at"] = now_iso()
        item["attempts"] = int(item.get("attempts", 0) or 0) + 1
        atomic_json(path, job)

        try:
            job_timeout = int(
                os.getenv("SAP_CLIENT_JOB_TIMEOUT", "7200") or 7200
            )
        except (TypeError, ValueError):
            job_timeout = 7200
        job_timeout = max(600, min(job_timeout, 21600))

        try:
            result = run_group(
                ["bash", str(PROFILE_RUN), profile],
                cwd=str(BASE),
                env=env,
                timeout=job_timeout,
            )
            returncode = int(result.returncode)
        except subprocess.TimeoutExpired:
            returncode = 124
            print(
                f"  TIMEOUT: produção excedeu {job_timeout}s."
            )

        item["finished_at"] = now_iso()
        item["returncode"] = returncode
        if returncode == 0 and output_ok(sid):
            item["status"] = "PASS"
            item["video"] = str(BASE / "videos" / f"short_v6_{sid}.mp4")
            print(f"  PASS: {item['video']}")
        else:
            item["status"] = "FAIL"
            job["status"] = "PARTIAL"
            job["updated_at"] = now_iso()
            atomic_json(path, job)
            print(f"  FAIL: retorno={returncode}. Job preservado para retomada.")
            return returncode or 1
        job["updated_at"] = now_iso()
        atomic_json(path, job)

    approved = all_items_approved(items)
    if approved:
        job["status"] = "PASS"
        job.setdefault("completed_at", now_iso())
    elif not execute:
        job["status"] = "QUEUED"
    else:
        job["status"] = "PARTIAL"
    job["updated_at"] = now_iso()
    atomic_json(path, job)
    print()
    print(f"JOB_STATUS={job['status']}")
    return 0 if job["status"] in {"PASS", "QUEUED"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro client job runner")
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--execute", action="store_true", help="run production; default is dry-run")
    args = parser.parse_args()
    path, job = load_job(args.job_id)
    return run_job(path, job, args.execute)


if __name__ == "__main__":
    raise SystemExit(main())

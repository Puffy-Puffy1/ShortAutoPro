#!/usr/bin/env python3
"""Unified operational center for ShortAutoPro production.

This is an orchestration/visibility layer over the canonical pipeline. It does
not implement a second renderer, selector or quality path.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import production_doctor
import production_profiler

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()


def resolve_sid(value: str | None) -> str:
    sid = str(value or "").strip()
    return sid or production_doctor.latest_short_id()


def run_command(command: list[str]) -> int:
    print("EXEC:", " ".join(command))
    return subprocess.call(command, cwd=BASE, env=os.environ.copy())


def status(sid: str, as_json: bool = False) -> int:
    report = production_doctor.diagnose(sid)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print("==============================================")
    print(" SHORTAUTOPRO - PRODUCTION CENTER")
    print("==============================================")
    print(f"ID: {sid}")
    print(f"STATUS: {report['status']} | BOUNDARY: {report['boundary']}")
    media = report["media"]
    print(f"MEDIA: {media['count']} cenas | vídeos={media['videos']} fotos={media['photos']}")
    if report["missing_scenes"]:
        print("MISSING: " + ",".join(map(str, report["missing_scenes"])))
    quality = report["quality"]
    print(
        "QUALITY: "
        f"professional={quality.get('professional_score')} "
        f"release={quality.get('release_decision')} "
        f"score={quality.get('release_score')}"
    )
    if report["issues"]:
        print("ISSUES:")
        for item in report["issues"]:
            print(f"  [{item['severity']}] {item['code']} - {item['detail']}")
    print("NEXT:")
    print("  " + report["next_action"])
    return 0


def profile(sid: str, history: bool, top: int) -> int:
    run_id = "" if history else production_profiler.latest_run_id(sid)
    rows = production_profiler.summarize(sid, run_id=run_id or None)
    print("==============================================")
    print(" SHORTAUTOPRO - PRODUCTION PROFILE")
    print("==============================================")
    print(f"ID: {sid}")
    print(f"RUN: {'HISTORY' if history else (run_id or '-')}")
    print(f"{'TOTAL':>10} {'AVG':>10} {'MAX':>10} {'N':>4}  ETAPA")
    for item in rows[:max(1, top)]:
        print(
            f"{item['total_seconds']:>10.2f} "
            f"{item['avg_seconds']:>10.2f} "
            f"{item['max_seconds']:>10.2f} "
            f"{item['count']:>4}  "
            f"{item['category']}/{item['name']}"
        )
    return 0


def batch_status() -> int:
    path = BASE / "queue" / "batch_state.json"
    if not path.is_file():
        print("Nenhum lote salvo.")
        return 0
    try:
        print(json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    except Exception:
        print(path.read_text(encoding="utf-8", errors="ignore"))
    return 0


def watch(sid: str, interval: float, iterations: int) -> int:
    count = 0
    try:
        while True:
            os.system("clear 2>/dev/null")
            status(sid)
            count += 1
            if iterations > 0 and count >= iterations:
                return 0
            time.sleep(max(1.0, interval))
    except KeyboardInterrupt:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro unified production center")
    sub = parser.add_subparsers(dest="command", required=True)

    latest = sub.add_parser("latest")
    latest.add_argument("--json", action="store_true")

    stat = sub.add_parser("status")
    stat.add_argument("--short-id", default="")
    stat.add_argument("--json", action="store_true")

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--short-id", default="")
    doctor.add_argument("--json", action="store_true")

    prof = sub.add_parser("profile")
    prof.add_argument("--short-id", default="")
    prof.add_argument("--history", action="store_true")
    prof.add_argument("--top", type=int, default=20)

    resume = sub.add_parser("resume")
    resume.add_argument("--short-id", default="")
    resume.add_argument("--execute", action="store_true")

    batch = sub.add_parser("batch")
    batch.add_argument("action", choices=["status", "resume"])
    batch.add_argument("--execute", action="store_true")

    watcher = sub.add_parser("watch")
    watcher.add_argument("--short-id", default="")
    watcher.add_argument("--interval", type=float, default=5.0)
    watcher.add_argument("--iterations", type=int, default=0)

    args = parser.parse_args()

    if args.command == "latest":
        sid = production_doctor.latest_short_id()
        if args.json:
            print(json.dumps({"short_id": sid}, ensure_ascii=False))
        else:
            print(sid or "Nenhuma produção encontrada.")
        return 0 if sid else 1

    if args.command == "batch":
        if args.action == "status":
            return batch_status()
        command = ["bash", str(BASE / "batch_recovery.sh"), "--resume"]
        if not args.execute:
            print("PLAN:", " ".join(command))
            print("Use --execute para executar.")
            return 0
        return run_command(command)

    sid = resolve_sid(getattr(args, "short_id", ""))
    if not sid:
        print("ERRO: nenhuma produção encontrada")
        return 1

    if args.command == "status":
        return status(sid, args.json)
    if args.command == "doctor":
        report = production_doctor.diagnose(sid)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            production_doctor.print_report(report)
        return 0 if report["status"] != "BLOCKED" else 20
    if args.command == "profile":
        return profile(sid, args.history, args.top)
    if args.command == "resume":
        command = [sys.executable, str(BASE / "resume_short_runtime.py"), "--short-id", sid]
        if not args.execute:
            report = production_doctor.diagnose(sid)
            print("PLAN:", " ".join(command))
            print(f"BOUNDARY: {report['boundary']}")
            print("Use --execute para executar.")
            return 0
        return run_command(command)
    if args.command == "watch":
        return watch(sid, args.interval, args.iterations)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

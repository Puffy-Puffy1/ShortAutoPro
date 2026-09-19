#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
REPORT_DIR = BASE / "reports" / "performance"
_ACTIVE_RUNS: dict[str, str] = {}


def _sid(value: str | None = None) -> str:
    return str(value or os.getenv("SHORT_ID", "") or "unknown").strip()


def _path(short_id: str | None = None) -> Path:
    sid = _sid(short_id)
    return REPORT_DIR / f"profile_{sid}.jsonl"


def begin_run(short_id: str, run_id: str | None = None) -> str:
    sid = _sid(short_id)
    rid = str(run_id or f"{int(time.time())}-{os.getpid()}").strip()
    _ACTIVE_RUNS[sid] = rid
    os.environ["SAP_PROFILE_RUN_ID"] = rid
    record(
        "__run_start__",
        0.0,
        short_id=sid,
        category="run",
        run_id=rid,
    )
    return rid


def current_run_id(short_id: str | None = None) -> str:
    return (
        _ACTIVE_RUNS.get(_sid(short_id), "")
        or str(os.getenv("SAP_PROFILE_RUN_ID", "") or "")
    )


def record(
    name: str,
    elapsed_seconds: float,
    *,
    short_id: str | None = None,
    category: str = "runtime",
    run_id: str | None = None,
    **meta: Any,
) -> None:
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "short_id": _sid(short_id),
            "name": str(name),
            "category": str(category),
            "elapsed_seconds": round(max(0.0, float(elapsed_seconds)), 4),
            "run_id": str(run_id or current_run_id(short_id) or ""),
            "meta": meta,
        }
        with _path(short_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


class Timer:
    def __init__(self, name: str, *, short_id: str | None = None, category: str = "runtime", **meta: Any):
        self.name = name
        self.short_id = short_id
        self.category = category
        self.meta = meta
        self.started = 0.0

    def __enter__(self):
        self.started = time.monotonic()
        return self

    def __exit__(self, exc_type, exc, tb):
        record(
            self.name,
            time.monotonic() - self.started,
            short_id=self.short_id,
            category=self.category,
            status="error" if exc is not None else "ok",
            **self.meta,
        )
        return False


def read(short_id: str) -> list[dict[str, Any]]:
    path = _path(short_id)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def latest_run_id(short_id: str) -> str:
    rows = read(short_id)
    for row in reversed(rows):
        rid = str(row.get("run_id", "") or "")
        if rid:
            return rid
    return ""


def summarize(short_id: str, *, run_id: str | None = None) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in read(short_id):
        if run_id and str(row.get("run_id", "") or "") != run_id:
            continue
        if str(row.get("name", "")) == "__run_start__":
            continue
        try:
            elapsed = float(row.get("elapsed_seconds", 0) or 0)
        except (TypeError, ValueError):
            continue
        key = (str(row.get("category", "runtime")), str(row.get("name", "?")))
        groups[key].append(elapsed)

    out = []
    for (category, name), values in groups.items():
        total = sum(values)
        out.append(
            {
                "category": category,
                "name": name,
                "count": len(values),
                "total_seconds": round(total, 3),
                "avg_seconds": round(total / len(values), 3),
                "max_seconds": round(max(values), 3),
            }
        )
    out.sort(key=lambda item: item["total_seconds"], reverse=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro production performance profiler")
    parser.add_argument("--short-id", required=True)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--history", action="store_true", help="agrega todas as execuções")
    parser.add_argument("--run-id", default="", help="mostra uma execução específica")
    args = parser.parse_args()

    selected_run = ""
    if not args.history:
        selected_run = args.run_id.strip() or latest_run_id(args.short_id)

    rows = summarize(
        args.short_id,
        run_id=selected_run or None,
    )
    print("==============================================")
    print(" SHORTAUTOPRO - PRODUCTION PERFORMANCE")
    print("==============================================")
    print(f"ID: {args.short_id}")
    if selected_run:
        print(f"RUN: {selected_run}")
    elif args.history:
        print("RUN: HISTÓRICO COMPLETO")
    if not rows:
        print("Sem métricas registradas.")
        return 0

    print()
    print(f"{'TOTAL':>10} {'AVG':>10} {'MAX':>10} {'N':>4}  ETAPA")
    for item in rows[: max(1, args.top)]:
        print(
            f"{item['total_seconds']:>10.2f} "
            f"{item['avg_seconds']:>10.2f} "
            f"{item['max_seconds']:>10.2f} "
            f"{item['count']:>4}  "
            f"{item['category']}/{item['name']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
JOBS = BASE / "reports" / "evolution" / "client_jobs"


def atomic_json(path: Path, data: object) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a ShortAutoPro client job")
    parser.add_argument("--client", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--language", default="pt-BR")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--topic-mode", choices=("theme", "exact"), default="theme")
    args = parser.parse_args()

    if not 1 <= args.quantity <= 100:
        parser.error("--quantity precisa estar entre 1 e 100")
    if not args.client.strip() or not args.topic.strip():
        parser.error("client/topic não podem estar vazios")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    client_slug = re.sub(r"[^A-Za-z0-9_-]+", "_", args.client.strip()).strip("_")[:24] or "client"
    job_id = f"{stamp}_{client_slug}"
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "job_id": job_id,
        "client": args.client.strip(),
        "topic": args.topic.strip(),
        "topic_mode": args.topic_mode,
        "quantity": args.quantity,
        "language": args.language.strip() or "pt-BR",
        "profile": args.profile.strip() or "default",
        "deliverables": ["video", "title", "description", "hashtags", "credits", "quality_report"],
        "status": "QUEUED",
        "created_at": now,
        "updated_at": now,
        "items": [],
    }
    path = JOBS / f"{job_id}.json"
    atomic_json(path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"JOB_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

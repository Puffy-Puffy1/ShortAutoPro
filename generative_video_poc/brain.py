"""Minimal local control surface for the Termux-first POC queue."""
from __future__ import annotations
import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

from generative_video_poc.state_store import ProjectStore, StoreError
from generative_video_poc.termux_runtime import TermuxRuntime, TermuxPreflightError
from generative_video_poc.worker import LocalQueueWorker, load_backend_config
from generative_video_poc.manifest import build_ready_manifest, verify_ready_manifest


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shortauto-brain", description="ShortAutoPro local Termux controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("device", help="inspect Termux hardware and local tools")
    create = sub.add_parser("create", help="create a resumable project from a JSON spec")
    create.add_argument("project_id")
    create.add_argument("--spec-file", required=True)
    create.add_argument("--max-attempts", type=int, default=3)
    create.add_argument("--root")
    listing = sub.add_parser("list", help="list local projects and progress")
    listing.add_argument("--root")
    show = sub.add_parser("show", help="show project state and clip checkpoints")
    show.add_argument("project_id")
    show.add_argument("--root")
    claim = sub.add_parser("claim", help="claim the next pending clip")
    claim.add_argument("--project-id")
    claim.add_argument("--worker", default=f"{socket.gethostname()}-{os.getpid()}")
    claim.add_argument("--lease-seconds", type=int, default=900)
    claim.add_argument("--root")
    work = sub.add_parser("work", help="generate one real clip from the local model queue")
    work.add_argument("--project-id")
    work.add_argument("--backend-config", required=True)
    work.add_argument("--worker", default=f"{socket.gethostname()}-{os.getpid()}")
    work.add_argument("--drain", action="store_true", help="keep processing until the project is complete or fails")
    work.add_argument("--root")
    export = sub.add_parser("export", help="write an integrity-checked manifest for a completed project")
    export.add_argument("project_id")
    export.add_argument("--root")
    verify = sub.add_parser("verify-manifest", help="verify a generated clip manifest and all clip checksums")
    verify.add_argument("manifest_path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "device":
        runtime = TermuxRuntime()
        try:
            _print(runtime.require_ready())
            print("TERMUX_PREFLIGHT=PASS")
            return 0
        except TermuxPreflightError as exc:
            _print({"preflight": "FAIL", "reason": str(exc), **runtime.inspect()})
            return 2
    try:
        if args.command == "verify-manifest":
            _print(verify_ready_manifest(args.manifest_path))
            return 0
        if args.command == "work":
            backend, config = load_backend_config(args.backend_config)
            store = ProjectStore(Path(args.root) if args.root else None)
            worker = LocalQueueWorker(
                store, backend, fps=config["fps"], seed=config["seed"],
                model=config["model"], worker_id=args.worker,
                timeout_seconds=config["timeout_seconds"],
            )
            if args.drain and not args.project_id:
                raise ValueError("--drain requires --project-id")
            result = worker.run_until_idle(args.project_id) if args.drain else worker.run_one(project_id=args.project_id)
            if args.drain and result["status"] == "PROJECT_COMPLETE":
                result["manifest"] = build_ready_manifest(store, args.project_id)
            _print(result)
            return 0 if result["status"] in {"CLIP_READY", "QUEUE_EMPTY", "PROJECT_COMPLETE"} else 2
        store = ProjectStore(Path(args.root) if args.root else None)
        if args.command == "create":
            spec_path = Path(args.spec_file).expanduser().resolve()
            data = json.loads(spec_path.read_text(encoding="utf-8"))
            _print(store.create_project(args.project_id, data, max_attempts=args.max_attempts))
        elif args.command == "list":
            _print(store.list_projects())
        elif args.command == "show":
            _print(store.get_project(args.project_id))
        elif args.command == "claim":
            result = store.claim_next_clip(
                args.worker, project_id=args.project_id, lease_seconds=args.lease_seconds,
            )
            _print(result if result is not None else {"status": "QUEUE_EMPTY"})
        elif args.command == "export":
            _print(build_ready_manifest(store, args.project_id))
        return 0
    except (OSError, json.JSONDecodeError, ValueError, KeyError, StoreError) as exc:
        print(f"SHORTAUTOPRO_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

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
    store = ProjectStore(Path(args.root) if args.root else None)
    try:
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
        return 0
    except (OSError, json.JSONDecodeError, ValueError, KeyError, StoreError) as exc:
        print(f"SHORTAUTOPRO_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

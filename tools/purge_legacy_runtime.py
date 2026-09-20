#!/usr/bin/env python3
"""Remove only explicitly forbidden legacy ShortAutoPro artifacts from the local worktree."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()

FORBIDDEN_RELATIVE = (
    Path("31"),
    Path("SYNC_TEST.TXT"),
    Path(".resume_vi710_after_semantic_fix.sh.pre_segment_fix"),
    Path("gerar_short.sh"),
    Path("gerar_short_professional.sh"),
    Path("professional_pipeline_runtime.py"),
    Path("resume_short_professional_runtime.py"),
    Path("v6_professional_runtime.py"),
    Path("v6_runtime.py"),
    Path("v6.py"),
    Path("video.py"),
    Path("limpar_storage.sh"),
    Path("tools/apply_consolidation_1_0.py"),
    Path("_arquivo_historico"),
)


def safe_target(relative: Path) -> Path:
    target = (BASE / relative).resolve()
    if target == BASE or BASE not in target.parents:
        raise RuntimeError(f"legacy target escapou da base: {relative}")
    return target


def remove_target(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink(missing_ok=True)
        return
    if target.is_dir():
        shutil.rmtree(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Somente verifica; não remove.")
    args = parser.parse_args()

    found: list[str] = []
    removed: list[str] = []

    for relative in FORBIDDEN_RELATIVE:
        target = safe_target(relative)
        if not target.exists() and not target.is_symlink():
            continue
        found.append(str(relative))
        if not args.check:
            remove_target(target)
            removed.append(str(relative))

    remaining = []
    for relative in FORBIDDEN_RELATIVE:
        target = safe_target(relative)
        if target.exists() or target.is_symlink():
            remaining.append(str(relative))

    if args.check:
        if found:
            print("LEGACY_PURGE=BLOCK")
            for item in found:
                print(f"LEGACY_PRESENT={item}")
            return 1
        print("LEGACY_PURGE=PASS")
        return 0

    for item in removed:
        print(f"LEGACY_REMOVED={item}")

    if remaining:
        print("LEGACY_PURGE=FAIL")
        for item in remaining:
            print(f"LEGACY_REMAINING={item}")
        return 1

    print(f"LEGACY_PURGE=PASS removed={len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

"""Fail-closed runtime guard for the current media selector control-flow bug.

The production selector is intentionally kept in ``midia.py``.  A previous
refactor left a small set of stray ``break`` statements in its top-level
per-scene loop.  The first media file could be downloaded successfully and
then the loop stopped before common bookkeeping, producing ``Total: 0/12``.

This launcher removes only those known stray statements in memory, validates
the transformed source, and executes it.  It does not rewrite ``midia.py`` on
disk.  When the source is later repaired directly, the launcher detects that
no hotfix is needed and executes the original source unchanged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


EXPECTED_BROKEN_COUNTS = {
    "before_destino": 1,
    "before_success_commit": 1,
    "outer_cleanup": 4,
    "local_commit": 1,
}


def _next_nonblank(lines: list[str], index: int) -> str:
    for item in lines[index + 1 :]:
        stripped = item.strip()
        if stripped:
            return stripped
    return ""


def _previous_nonblank(lines: list[str], index: int) -> str:
    for item in reversed(lines[:index]):
        stripped = item.strip()
        if stripped:
            return stripped
    return ""


def fix_source(source: str) -> tuple[str, dict[str, int]]:
    """Remove only the seven known premature breaks from ``midia.py``.

    Returns ``(source_fixed, counters)``.  A completely fixed source is
    accepted unchanged.  A partially matching/unknown source fails closed so
    that a future refactor cannot be silently modified in the wrong place.
    """

    lines = source.splitlines(keepends=True)
    counters = {key: 0 for key in EXPECTED_BROKEN_COUNTS}
    remove_indexes: set[int] = set()

    for index, line in enumerate(lines):
        if line.strip() != "break":
            continue

        indent = len(line) - len(line.lstrip(" "))
        nxt = _next_nonblank(lines, index)
        prev = _previous_nonblank(lines, index)

        # Success path: this break made destino/bookkeeping unreachable.
        if indent == 16 and nxt == "destino = destino_teste":
            counters["before_destino"] += 1
            remove_indexes.add(index)
            continue

        # Same success path: keep the final inner-loop break, but allow the
        # VSE42 success-commit block immediately below this older stray break.
        if indent == 16 and nxt == "# SHORTAUTOPRO VSE42 SUCCESS COMMIT":
            counters["before_success_commit"] += 1
            remove_indexes.add(index)
            continue

        # These breaks are already outside the candidate/retry loops and were
        # terminating the outer per-scene loop before common bookkeeping.
        if indent == 8 and prev == "_vse42_cleanup_scene_sibling(destino)":
            counters["outer_cleanup"] += 1
            remove_indexes.add(index)
            continue

        # Local fallback has no inner loop at this point; this break also
        # targets the outer scene loop and must not run before bookkeeping.
        if indent == 12 and prev == "_vse42_commit_safe(escolhido)":
            counters["local_commit"] += 1
            remove_indexes.add(index)
            continue

    if not remove_indexes:
        # Directly repaired source: launcher becomes a transparent pass-through.
        return source, counters

    if counters != EXPECTED_BROKEN_COUNTS:
        details = ", ".join(f"{k}={v}" for k, v in counters.items())
        expected = ", ".join(
            f"{k}={v}" for k, v in EXPECTED_BROKEN_COUNTS.items()
        )
        raise RuntimeError(
            "midia.py mudou e o hotfix nao e seguro; "
            f"encontrado [{details}], esperado [{expected}]"
        )

    fixed = "".join(
        line for index, line in enumerate(lines) if index not in remove_indexes
    )
    return fixed, counters


def run() -> None:
    base = Path(os.path.expanduser("~/ShortAutoPro"))
    target = base / "midia.py"

    if not target.is_file():
        raise SystemExit(f"ERRO: midia.py nao encontrado: {target}")

    try:
        source = target.read_text(encoding="utf-8")
        fixed, counters = fix_source(source)
        code = compile(fixed, str(target), "exec")
    except Exception as exc:
        raise SystemExit(f"ERRO MIDIA CONTROL FLOW GUARD: {exc}") from exc

    applied = sum(counters.values())
    if applied:
        print(f"MIDIA_CONTROL_FLOW_FIX=APPLIED removed_breaks={applied}")
    else:
        print("MIDIA_CONTROL_FLOW_FIX=NOT_NEEDED")

    namespace = {
        "__name__": "__main__",
        "__file__": str(target),
        "__package__": None,
        "__cached__": None,
    }

    old_argv0 = sys.argv[0]
    sys.argv[0] = str(target)
    try:
        exec(code, namespace, namespace)
    finally:
        sys.argv[0] = old_argv0


if __name__ == "__main__":
    run()

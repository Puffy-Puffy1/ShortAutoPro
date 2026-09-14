#!/usr/bin/env python3

"""Fail-closed runtime guard for the current media selector control-flow bugs.

The production selector remains in ``midia.py``. A previous refactor left a
small set of stray ``break`` statements in its top-level per-scene loop. The
first media file could be downloaded successfully and then the loop stopped
before common bookkeeping, producing ``Total: 0/12``.

This launcher removes only those known stray statements in memory. It also
ensures the legacy cleanup block removes stale WebP assets when an explicit
SHORT_ID is reused for a debug/recovery run. It now also rejects critically
small downloaded media at acquisition time, using the same floor enforced by
the Media Master Gate, so the selector can fail over to another candidate
before a bad scene is committed. Unknown partial layouts fail closed instead
of being rewritten heuristically.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


EXPECTED_BROKEN_COUNTS = {
    "before_destino": 1,
    "before_success_commit": 1,
    "outer_cleanup": 3,
    "local_commit": 2,
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
    """Remove only the seven known premature breaks from ``midia.py``."""

    lines = source.splitlines(keepends=True)
    counters = {key: 0 for key in EXPECTED_BROKEN_COUNTS}
    remove_indexes: set[int] = set()

    for index, line in enumerate(lines):
        if line.strip() != "break":
            continue

        indent = len(line) - len(line.lstrip(" "))
        nxt = _next_nonblank(lines, index)
        prev = _previous_nonblank(lines, index)

        if indent == 16 and nxt == "destino = destino_teste":
            counters["before_destino"] += 1
            remove_indexes.add(index)
            continue

        if indent == 16 and nxt == "# SHORTAUTOPRO VSE42 SUCCESS COMMIT":
            counters["before_success_commit"] += 1
            remove_indexes.add(index)
            continue

        if indent == 8 and prev == "_vse42_cleanup_scene_sibling(destino)":
            counters["outer_cleanup"] += 1
            remove_indexes.add(index)
            continue

        if indent in {8, 12} and prev == "_vse42_commit_safe(escolhido)":
            counters["local_commit"] += 1
            remove_indexes.add(index)
            continue

    if not remove_indexes:
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


def harden_cleanup(source: str) -> tuple[str, bool]:
    """Add WebP to the known legacy media cleanup block, if still needed."""

    start_marker = "# LIMPAR MÍDIA ANTIGA"
    end_marker = "# TEXTO"
    start = source.find(start_marker)
    if start < 0:
        return source, False
    end = source.find(end_marker, start)
    if end < 0:
        raise RuntimeError("bloco de limpeza de midia sem marcador final")

    block = source[start:end]
    if '".webp"' in block:
        return source, False

    old = '            ".png",\n            ".mp4"'
    new = '            ".png",\n            ".webp",\n            ".mp4"'
    count = block.count(old)
    if count != 1:
        raise RuntimeError(
            "bloco de limpeza de midia mudou e a inclusao de WebP nao e segura"
        )

    hardened_block = block.replace(old, new, 1)
    return source[:start] + hardened_block + source[end:], True


def harden_download_resolution(source: str) -> tuple[str, bool]:
    """Reject media below the Media Master Gate critical resolution floor.

    midia.py already probes every downloaded visual before committing it. The
    old downloader accepted any positive dimensions, while the next pipeline
    stage blocks anything below 320x180 total pixels. That mismatch allowed a
    low-resolution Wikimedia asset to be committed and then fail minutes later.
    This guarded in-memory rewrite aligns the acquisition floor with the gate,
    allowing the existing candidate failover loop to try the next source.
    """

    marker = '''        if largura <= 0 or altura <= 0:\n            raise RuntimeError(\n                "dimensões inválidas"\n            )\n'''
    if marker not in source:
        raise RuntimeError(
            "bloco de validação de resolução mudou; hardening de download não é seguro"
        )

    if "mídia abaixo do piso técnico" in source:
        return source, False

    replacement = marker + '''\n        if largura * altura < 320 * 180:\n            raise RuntimeError(\n                f"mídia abaixo do piso técnico: {largura}x{altura}"\n            )\n'''

    if source.count(marker) != 1:
        raise RuntimeError(
            "foram encontrados múltiplos blocos de validação de resolução; abortando"
        )

    return source.replace(marker, replacement, 1), True


def run() -> None:
    base = Path(os.path.expanduser("~/ShortAutoPro"))
    target = base / "midia.py"

    if not target.is_file():
        raise SystemExit(f"ERRO: midia.py nao encontrado: {target}")

    try:
        source = target.read_text(encoding="utf-8")
        fixed, counters = fix_source(source)
        fixed, cleanup_applied = harden_cleanup(fixed)
        fixed, resolution_applied = harden_download_resolution(fixed)
        code = compile(fixed, str(target), "exec")
    except Exception as exc:
        raise SystemExit(f"ERRO MIDIA CONTROL FLOW GUARD: {exc}") from exc

    applied = sum(counters.values())
    if applied:
        print(f"MIDIA_CONTROL_FLOW_FIX=APPLIED removed_breaks={applied}")
    else:
        print("MIDIA_CONTROL_FLOW_FIX=NOT_NEEDED")

    print(
        "MIDIA_WEBP_CLEANUP="
        + ("APPLIED" if cleanup_applied else "NOT_NEEDED")
    )
    print(
        "MIDIA_MIN_RESOLUTION_GUARD="
        + ("APPLIED" if resolution_applied else "ALREADY_PRESENT")
    )

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

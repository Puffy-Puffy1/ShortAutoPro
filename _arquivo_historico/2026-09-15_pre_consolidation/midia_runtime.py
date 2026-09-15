#!/usr/bin/env python3

"""Fail-closed runtime guard for the current media selector control-flow bugs.

The production selector remains in ``midia.py``. A previous refactor left a
small set of stray ``break`` statements in its top-level per-scene loop. The
first media file could be downloaded successfully and then the loop stopped
before common bookkeeping, producing ``Total: 0/12``.

This launcher removes only those known stray statements in memory. It also
ensures the legacy cleanup block removes stale WebP assets when an explicit
SHORT_ID is reused for a debug/recovery run. It rejects critically small media
at acquisition time and, in Professional Edit mode, adds a stronger 720p-class
pixel floor for ordinary stock while allowing a traceable exception for direct
Wikimedia case evidence. Unknown layouts fail closed.
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
        expected = ", ".join(f"{k}={v}" for k, v in EXPECTED_BROKEN_COUNTS.items())
        raise RuntimeError(
            "midia.py mudou e o hotfix nao e seguro; "
            f"encontrado [{details}], esperado [{expected}]"
        )

    fixed = "".join(line for index, line in enumerate(lines) if index not in remove_indexes)
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
        raise RuntimeError("bloco de limpeza de midia mudou e a inclusao de WebP nao e segura")

    hardened_block = block.replace(old, new, 1)
    return source[:start] + hardened_block + source[end:], True


def harden_download_resolution(source: str) -> tuple[str, bool]:
    """Reject media below the Media Master Gate critical resolution floor."""

    marker = '''        if largura <= 0 or altura <= 0:\n            raise RuntimeError(\n                "dimensões inválidas"\n            )\n'''
    if marker not in source:
        raise RuntimeError("bloco de validação de resolução mudou; hardening de download não é seguro")

    if "mídia abaixo do piso técnico" in source:
        return source, False

    replacement = marker + '''\n        if largura * altura < 320 * 180:\n            raise RuntimeError(\n                f"mídia abaixo do piso técnico: {largura}x{altura}"\n            )\n'''

    if source.count(marker) != 1:
        raise RuntimeError("foram encontrados múltiplos blocos de validação de resolução; abortando")

    return source.replace(marker, replacement, 1), True


def harden_professional_media_floor(source: str) -> tuple[str, bool]:
    """Add candidate-aware Professional Edit quality floor.

    Ordinary stock below the configured pixel floor is deleted so the existing
    failover loop can try the next candidate. Direct Wikimedia evidence is the
    only default exception because authentic historic/case material can be rare
    and more valuable than a generic high-resolution substitute.
    """

    helper_name = "_sap_professional_media_accept_v1"
    if helper_name in source:
        return source, False

    function_marker = "\ndef baixar_candidato_5_2(\n"
    if source.count(function_marker) != 1:
        raise RuntimeError("baixar_candidato_5_2 mudou; Professional Media Floor não é seguro")

    helper = r'''

def _sap_professional_media_accept_v1(candidato, destino):
    if str(os.getenv("SAP_PRO_EDIT", "0")).strip() != "1":
        return True

    try:
        floor = int(os.getenv("SAP_PRO_MEDIA_MIN_PIXELS", str(1280 * 720)))
    except (TypeError, ValueError):
        floor = 1280 * 720

    floor = max(320 * 180, min(floor, 3840 * 2160))

    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json", destino,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if probe.returncode != 0:
            raise RuntimeError("ffprobe_failed")
        payload = json.loads(probe.stdout)
        streams = payload.get("streams", [])
        if not streams:
            raise RuntimeError("visual_stream_missing")
        width = int(streams[0].get("width", 0) or 0)
        height = int(streams[0].get("height", 0) or 0)
    except Exception as exc:
        print(
            "    PRO_MEDIA_FLOOR=REJECT probe="
            + type(exc).__name__
            + ":"
            + str(exc)
        )
        try:
            os.remove(destino)
        except OSError:
            pass
        return False

    pixels = width * height
    if pixels >= floor:
        print(
            f"    PRO_MEDIA_FLOOR=PASS dimensions={width}x{height} "
            f"pixels={pixels} floor={floor}"
        )
        return True

    source_name = str(candidato.get("fonte", "")).strip().lower()
    evidence_class = str(candidato.get("evidence_class", "")).strip().upper()
    if source_name == "wikimedia" and evidence_class == "CASE_DIRECT":
        print(
            f"    PRO_MEDIA_FLOOR=EVIDENCE_EXCEPTION dimensions={width}x{height} "
            f"pixels={pixels} floor={floor} class={evidence_class}"
        )
        candidato["_professional_resolution_exception"] = True
        return True

    print(
        f"    PRO_MEDIA_FLOOR=REJECT dimensions={width}x{height} "
        f"pixels={pixels} floor={floor} source={candidato.get('fonte', '?')} "
        f"evidence={evidence_class or 'NONE'}"
    )
    try:
        os.remove(destino)
    except OSError:
        pass
    return False
'''

    patched = source.replace(function_marker, helper + function_marker, 1)

    download_marker = '''    ok = baixar(\n        candidato.get(\n            "url",\n            ""\n        ),\n        destino\n    )\n'''
    if patched.count(download_marker) != 1:
        raise RuntimeError("chamada baixar em baixar_candidato_5_2 mudou; Professional Media Floor não é seguro")

    replacement = download_marker + '''\n    if ok:\n        ok = _sap_professional_media_accept_v1(\n            candidato,\n            destino\n        )\n'''
    return patched.replace(download_marker, replacement, 1), True


def run() -> None:
    base = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
    target = base / "midia.py"

    if not target.is_file():
        raise SystemExit(f"ERRO: midia.py nao encontrado: {target}")

    try:
        source = target.read_text(encoding="utf-8")
        fixed, counters = fix_source(source)
        fixed, cleanup_applied = harden_cleanup(fixed)
        fixed, resolution_applied = harden_download_resolution(fixed)
        fixed, professional_floor_applied = harden_professional_media_floor(fixed)
        code = compile(fixed, str(target), "exec")
    except Exception as exc:
        raise SystemExit(f"ERRO MIDIA CONTROL FLOW GUARD: {exc}") from exc

    applied = sum(counters.values())
    if applied:
        print(f"MIDIA_CONTROL_FLOW_FIX=APPLIED removed_breaks={applied}")
    else:
        print("MIDIA_CONTROL_FLOW_FIX=NOT_NEEDED")

    print("MIDIA_WEBP_CLEANUP=" + ("APPLIED" if cleanup_applied else "NOT_NEEDED"))
    print("MIDIA_MIN_RESOLUTION_GUARD=" + ("APPLIED" if resolution_applied else "ALREADY_PRESENT"))
    print("PROFESSIONAL_MEDIA_FLOOR=" + ("APPLIED" if professional_floor_applied else "ALREADY_PRESENT"))

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

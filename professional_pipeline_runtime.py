#!/usr/bin/env python3
"""Execute the stable ShortAutoPro pipeline with the professional edit path.

The base gerar_short.sh remains untouched as a rollback asset. This launcher
applies a small, exact, fail-closed patch to a temporary copy and executes it.
If expected markers change, production stops rather than guessing.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SOURCE = BASE / "gerar_short.sh"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"professional patch inseguro ({label}): esperado 1 marcador, encontrado {count}")
    return source.replace(old, new, 1)


def build(source: str) -> str:
    source = replace_once(
        source,
        'set -e\nset -o pipefail\n',
        'set -e\nset -o pipefail\n\nexport SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"\nexport SAP_PROFESSIONAL_MIN_SCORE="${SAP_PROFESSIONAL_MIN_SCORE:-88}"\nexport SAP_PROFESSIONAL_ENFORCE="${SAP_PROFESSIONAL_ENFORCE:-0}"\n',
        "professional_flags",
    )
    source = replace_once(
        source,
        'rodar_python "6C/12 - MONTAGE RHYTHM DIRECTOR" "rhythm_director.py"\n',
        'rodar_python "6C/12 - MONTAGE RHYTHM DIRECTOR" "rhythm_director.py"\n'
        'rodar_python "6C1/12 - PROFESSIONAL EDIT DIRECTOR" "professional_edit_director.py"\n'
        'rodar_python "6C2/12 - PROFESSIONAL EDIT AUTO-REPAIR" "professional_edit_repair.py"\n',
        "professional_director",
    )
    source = replace_once(
        source,
        'rodar_python "9/12 - MONTANDO CENAS SEMÂNTICAS" "video.py"\n',
        'rodar_python "9/12 - PROFESSIONAL SCENE ASSEMBLER" "video_professional.py"\n',
        "professional_scene_assembler",
    )

    legacy_renderer_count = source.count('v6_runtime.py')
    if legacy_renderer_count < 4:
        raise RuntimeError(
            "professional patch inseguro (v6 renderer): "
            f"esperado >=4 referências, encontrado {legacy_renderer_count}"
        )
    source = source.replace('v6_runtime.py', 'v6_professional_runtime.py')
    source = source.replace('RENDER FINAL V6', 'RENDER FINAL V6 PROFESSIONAL')
    source = source.replace(
        'VERSAO="V6 PRINCIPAL + EVOLUTION 1.1"',
        'VERSAO="V6 PROFESSIONAL + EVOLUTION 1.2"',
    )

    marker = '# =====================================================\n# COPIAR PARA DOWNLOADS\n# =====================================================\n'
    professional_gate = (
        'rodar_python "12D/12 - PROFESSIONAL QUALITY GATE" "professional_quality_gate.py"\n\n'
        + marker
    )
    source = replace_once(source, marker, professional_gate, "professional_quality_gate")
    return source


def main() -> int:
    if not SOURCE.is_file():
        print(f"ERRO PROFESSIONAL PIPELINE: gerar_short.sh ausente: {SOURCE}")
        return 1
    try:
        patched = build(SOURCE.read_text(encoding="utf-8"))
        required = [
            "professional_edit_director.py",
            "professional_edit_repair.py",
            "video_professional.py",
            "v6_professional_runtime.py",
            "professional_quality_gate.py",
        ]
        missing = [name for name in required if name not in patched]
        if missing:
            raise RuntimeError("patch profissional incompleto: " + ", ".join(missing))
    except Exception as exc:
        print(f"ERRO PROFESSIONAL PIPELINE: {exc}")
        return 1

    fd, temp_name = tempfile.mkstemp(prefix="shortautopro_professional_", suffix=".sh")
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(patched, encoding="utf-8")
        print("PROFESSIONAL_PIPELINE_RUNTIME=ACTIVE")
        print(f"BASE_PIPELINE={SOURCE}")
        result = subprocess.run(["bash", str(temp_path)], cwd=str(BASE), env=os.environ.copy())
        return int(result.returncode)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

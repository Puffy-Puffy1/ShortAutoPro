#!/usr/bin/env python3
"""Safe resume path for Professional Edit productions."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import resume_short_runtime as base
import shortautopro_evolution as evo

BASE = base.BASE


def pro_plan_ok(sid: str) -> bool:
    data = base.read_json(BASE / "roteiros" / f"pro_edit_plan_{sid}.json")
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    return (
        str(data.get("version", "")).startswith("PRO_EDIT_")
        and isinstance(scenes, list)
        and len(scenes) == base.expected_scenes()
    )


def boundary(sid: str) -> str:
    point = base.boundary(sid)
    if point in {"complete", "full"}:
        return point
    if not pro_plan_ok(sid):
        return "full"
    return point


def full_rerun(sid: str) -> int:
    generator = BASE / "gerar_short_professional.sh"
    if not generator.is_file():
        raise RuntimeError("gerar_short_professional.sh ausente")
    print("Nenhum checkpoint profissional parcial é seguro. Reexecutando pipeline profissional completo.")
    env = os.environ.copy()
    env["SHORT_ID"] = sid
    env["SAP_PRO_EDIT"] = "1"
    return subprocess.run(["bash", str(generator)], cwd=str(BASE), env=env).returncode


def resume(sid: str) -> int:
    os.environ["SHORT_ID"] = sid
    os.environ["SAP_PRO_EDIT"] = "1"
    point = boundary(sid)
    print("========================================")
    print(" SHORTAUTOPRO - PROFESSIONAL SAFE RESUME")
    print("========================================")
    print(f"ID: {sid}")
    print(f"Boundary: {point}")
    print()

    if point == "complete":
        print("Produção já possui vídeo e Quality Gate aprovados.")
        return 0
    if point == "full":
        return full_rerun(sid)

    lock = base.acquire_generation_lock()
    try:
        order = {"post_media": 1, "post_audio": 2, "post_captions": 3, "post_assembly": 4, "post_render": 5}
        rank = order[point]
        if rank <= 1:
            base.run_python(sid, "PROFESSIONAL EDIT DIRECTOR", "professional_edit_director.py")
            base.run_python(sid, "FINAL EDITORIAL GATE", "editorial_gate.py")
            base.run_python(sid, "GERANDO VOZ PIPER", "audio.py")
        if rank <= 2:
            base.run_python(sid, "WHISPER + LEGENDA", "legenda_dinamica.py")
            base.run_python(sid, "CAPTION AUDIT", "shortautopro_evolution.py", "caption-audit")
        if rank <= 3:
            base.run_python(sid, "PROFESSIONAL SCENE ASSEMBLER", "video_professional.py")
        if rank <= 4:
            base.run_python(sid, "RENDER FINAL V6 PROFESSIONAL", "v6_professional_runtime.py")
            if not base.render_ok(sid):
                raise RuntimeError("V6 Professional terminou sem artefato técnico válido")

        base.run_python(sid, "EVOLUTION E2E", "shortautopro_evolution.py", "e2e")
        base.run_python(sid, "QUALITY GATE", "quality_check.py")
        base.run_python(sid, "PUBLISH PACK", "publish_pack.py")
        base.run_python(sid, "SOURCE LEDGER", "source_ledger.py")
        base.run_python(sid, "PUBLISH INTEGRITY", "publish_integrity_gate.py")
        base.run_python(sid, "PRODUCTION MANIFEST", "production_manifest.py")
        base.run_python(sid, "FINAL QUALITY", "final_quality.py")
        quality_args = ["quality-score"]
        if os.getenv("SAP_EVOLUTION_ENFORCE", "0") == "1":
            quality_args.append("--enforce")
        base.run_python(sid, "EVOLUTION QUALITY SCORE", "shortautopro_evolution.py", *quality_args)
        base.run_python(sid, "PROFESSIONAL QUALITY GATE", "professional_quality_gate.py")
        if not base.final_ok(sid):
            raise RuntimeError("retomada profissional terminou sem Quality Gate aprovado")
        base.run_python(sid, "REGISTRANDO ASSUNTO", "register_topic.py")
        destination = base.copy_download(sid)
        evo.finish_production("SUCCESS", sid)
        print("\nPROFESSIONAL_RESUME_STATUS=PASS")
        print(f"Vídeo: {destination}")
        return 0
    except Exception as exc:
        evo.finish_production("FAILED", sid)
        print(f"PROFESSIONAL_RESUME_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if lock is not None:
            try:
                lock.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro professional safe resume runtime")
    parser.add_argument("--short-id", default=None)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    sid = args.short_id or os.getenv("SHORT_ID", "").strip() or base.latest_incomplete()
    if not sid:
        print("Nenhuma produção encontrada para retomar.")
        return 0
    if args.status:
        print(json.dumps({
            "short_id": sid,
            "boundary": boundary(sid),
            "professional_plan": pro_plan_ok(sid),
            "plan": evo.resume_plan(sid),
        }, ensure_ascii=False, indent=2))
        return 0
    return resume(sid)


if __name__ == "__main__":
    raise SystemExit(main())

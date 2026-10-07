#!/usr/bin/env python3
"""Resume a canonical ShortAutoPro run after a semantic-gate code fix.

This helper is intentionally narrow: it reuses already validated script/scene
artifacts, reruns the semantic gate with the current code, rebuilds the media and
professional planning tail, then hands control to the canonical safe-resume
runtime. It never switches to a legacy pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import main as canonical
from production_profiler import begin_run as profile_begin_run
from production_profiler import record as profile_record

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def nonempty(path: Path, minimum: int = 1) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= minimum
    except OSError:
        return False


def expected_scenes() -> int:
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except ValueError:
        value = 12
    return max(6, min(20, value))


def validate_checkpoint(sid: str) -> None:
    r = BASE / "roteiros"
    required = [
        r / f"short_{sid}.txt",
        r / f"fonte_{sid}.txt",
        r / f"scene_map_{sid}.json",
        r / f"post_script_truth_{sid}.json",
        r / f"visual_continuity_{sid}.json",
    ]
    missing = [str(path) for path in required if not nonempty(path, 10)]
    if missing:
        raise RuntimeError(
            "checkpoint insuficiente para retomada sem perda: " + ", ".join(missing)
        )

    scene_map = read_json(r / f"scene_map_{sid}.json")
    scenes = scene_map.get("scenes", []) if isinstance(scene_map, dict) else []
    if not isinstance(scenes, list) or len(scenes) != expected_scenes():
        raise RuntimeError(
            f"scene_map inválido: esperado {expected_scenes()} cenas, encontrado "
            f"{len(scenes) if isinstance(scenes, list) else 0}"
        )

    truth = read_json(r / f"post_script_truth_{sid}.json")
    if str(truth.get("status", "")).upper() != "PASS":
        raise RuntimeError("POST-SCRIPT TRUTH LOCK não está PASS; retomada recusada")


def run_stage(
    sid: str,
    title: str,
    script: str,
    args: tuple[str, ...] = (),
    retries: int = 0,
) -> None:
    path = BASE / script
    if not path.is_file():
        raise RuntimeError(f"arquivo obrigatório ausente: {script}")

    env = os.environ.copy()
    env["SHORT_ID"] = sid
    last = 1

    print(f"\n{'-' * 52}\n{title}\n{'-' * 52}\n")
    stage_started = time.monotonic()
    for attempt in range(retries + 1):
        try:
            stage_timeout = int(
                os.getenv("SAP_STAGE_TIMEOUT_SECONDS", "1800") or 1800
            )
        except (TypeError, ValueError):
            stage_timeout = 1800
        stage_timeout = max(60, min(stage_timeout, 7200))

        try:
            proc = subprocess.run(
                [sys.executable, str(path), *args],
                cwd=str(BASE),
                env=env,
                check=False,
                timeout=stage_timeout,
            )
            last = proc.returncode
        except subprocess.TimeoutExpired:
            last = 124
            elapsed = time.monotonic() - stage_started
            profile_record(
                script,
                elapsed,
                short_id=sid,
                category="stage",
                title=title,
                status="timeout",
                timeout_seconds=stage_timeout,
            )
            raise RuntimeError(
                f"{script} excedeu timeout de {stage_timeout}s"
            )
        if last == 0:
            elapsed = time.monotonic() - stage_started
            profile_record(
                script,
                elapsed,
                short_id=sid,
                category="stage",
                title=title,
                status="pass",
            )
            print(f"ETAPA OK: {title} ({elapsed:.1f}s)")
            return
        if attempt < retries:
            delay = min(8, 2 * (attempt + 1))
            print(
                f"AUTO-RECOVERY {attempt + 1}/{retries}: {script} retornou {last}; "
                f"nova tentativa em {delay}s"
            )
            time.sleep(delay)

    profile_record(
        script,
        time.monotonic() - stage_started,
        short_id=sid,
        category="stage",
        title=title,
        status="fail",
        code=last,
    )
    raise RuntimeError(f"{script} falhou com código {last}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retoma ShortAutoPro após correção do Semantic Integrity Gate"
    )
    parser.add_argument("--short-id", required=True)
    args = parser.parse_args()
    sid = args.short_id.strip()
    if not sid:
        raise SystemExit("--short-id vazio")

    canonical.source_config()
    canonical.setup_env()
    os.environ["SHORT_ID"] = sid
    validate_checkpoint(sid)

    stages = [
        ("5E - SEMANTIC INTEGRITY GATE", "semantic_integrity_gate.py", (), 0),
        ("6 - MEDIA ACQUISITION V3", "media_acquisition_v3.py", ("--short-id", sid), 0),
        ("6A - RENDER PLAN V2", "render_plan_v2.py", ("--short-id", sid), 0),
        ("6A - MEDIA MASTER GATE", "media_master_gate.py", (), 0),
        ("6A1 - MULTIDIMENSIONAL VISUAL SCORE", "visual_score_engine.py", (), 0),
        ("6B - CINEMATIC MOTION DIRECTOR", "motion_director.py", (), 0),
        ("6C - MONTAGE RHYTHM DIRECTOR", "rhythm_director.py", (), 0),
        ("6C1 - PROFESSIONAL EDIT DIRECTOR", "professional_edit_director.py", (), 0),
        ("6C2 - PROFESSIONAL EDIT AUTO-REPAIR", "professional_edit_repair.py", (), 0),
        ("6C2B - MULTI-ASSET DIRECTOR", "multi_asset_director.py", (), 1),
        ("6C3 - RETENTION ENGINE", "retention_engine.py", ("--repair", "--enforce"), 0),
        ("6C4 - SOUND DESIGN ENGINE", "sound_design_engine.py", (), 0),
        ("6D - PRODUCTION SUPERVISOR", "production_supervisor.py", (), 0),
        ("6D1 - EVOLUTION VISUAL AUDIT", "shortautopro_evolution.py", ("visual-audit",), 0),
    ]

    print("==============================================")
    print(" SHORTAUTOPRO - RESUME AFTER SEMANTIC FIX")
    print("==============================================")
    print(f"ID: {sid}")
    print("PIPELINE: PROFESSIONAL_CANONICAL")
    run_id = profile_begin_run(sid)
    print(f"PROFILE_RUN_ID={run_id}")

    try:
        with canonical.RunLock(sid):
            for title, script, stage_args, retries in stages:
                run_stage(sid, title, script, stage_args, retries)
    except Exception as exc:
        print(f"RESUME_AFTER_SEMANTIC_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # The professional planning checkpoint now exists. Hand off to the canonical
    # artifact-validated resume runtime for editorial/audio/captions/render/QA.
    resume = BASE / "resume_short_runtime.py"
    if not resume.is_file():
        print("RESUME_AFTER_SEMANTIC_ERROR=resume_short_runtime.py ausente", file=sys.stderr)
        return 1

    try:
        handoff_timeout = int(
            os.getenv("SAP_RESUME_HANDOFF_TIMEOUT", "7200") or 7200
        )
    except (TypeError, ValueError):
        handoff_timeout = 7200
    handoff_timeout = max(600, min(handoff_timeout, 21600))
    try:
        proc = subprocess.run(
            [sys.executable, str(resume), "--short-id", sid],
            cwd=str(BASE),
            env=os.environ.copy(),
            check=False,
            timeout=handoff_timeout,
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        print(
            "RESUME_AFTER_SEMANTIC_ERROR="
            f"resume handoff excedeu {handoff_timeout}s",
            file=sys.stderr,
        )
        return 124


if __name__ == "__main__":
    raise SystemExit(main())

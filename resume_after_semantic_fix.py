#!/usr/bin/env python3
"""Resume a canonical ShortAutoPro run after semantic/media runtime fixes.

The helper preserves validated research/script/scene truth artifacts, reruns the
semantic gate, resets only stale media-and-later outputs for the same Short ID,
rebuilds the professional planning tail, then hands control to the canonical
artifact-validated resume runtime. It never switches to a legacy pipeline.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import main as canonical

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


def _remove_file(path: Path, removed: list[str]) -> None:
    try:
        if path.is_file() or path.is_symlink():
            path.unlink()
            removed.append(str(path.relative_to(BASE)))
    except OSError as exc:
        raise RuntimeError(f"não foi possível limpar {path}: {exc}") from exc


def _remove_tree(path: Path, removed: list[str]) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path.relative_to(BASE)) + "/")
    except OSError as exc:
        raise RuntimeError(f"não foi possível limpar {path}: {exc}") from exc


def reset_media_tail(sid: str) -> None:
    """Remove only stage-6-and-later artifacts for a deterministic clean rerun."""
    removed: list[str] = []

    _remove_tree(BASE / "imagens" / f"short_{sid}", removed)
    _remove_tree(BASE / "imagens" / f"short_{sid}_secondary", removed)
    _remove_tree(BASE / "temp" / sid, removed)
    _remove_file(BASE / "temp" / f"visual_unified_state_{sid}.json", removed)

    _remove_file(BASE / "audios" / f"short_{sid}.mp3", removed)
    _remove_file(BASE / "videos" / f"short_{sid}.ass", removed)
    _remove_file(BASE / "videos" / f"short_v6_{sid}.mp4", removed)

    r = BASE / "roteiros"
    tail_names = [
        f"media_selection_{sid}.json",
        f"media_quality_{sid}.json",
        f"visual_intelligence_6_{sid}.json",
        f"visual_score_{sid}.json",
        f"motion_plan_{sid}.json",
        f"motion_plan_pre_rhythm_{sid}.json",
        f"rhythm_plan_{sid}.json",
        f"pro_edit_plan_{sid}.json",
        f"pro_edit_runtime_{sid}.json",
        f"multi_asset_{sid}.json",
        f"retention_{sid}.json",
        f"sound_design_{sid}.json",
        f"supervisor_{sid}.json",
        f"pro_caption_{sid}.json",
        f"caption_layout_{sid}.json",
    ]
    for name in tail_names:
        _remove_file(r / name, removed)

    m = BASE / "manifests"
    for name in (
        f"{sid}_quality.json",
        f"{sid}_release.json",
        f"{sid}_professional.json",
    ):
        _remove_file(m / name, removed)

    evolution = BASE / "reports" / "evolution"
    for name in (
        f"visual_qa_{sid}.json",
        f"final_audio_{sid}.json",
    ):
        _remove_file(evolution / name, removed)

    print("MEDIA_TAIL_RESET=PASS")
    print(f"MEDIA_TAIL_RESET_REMOVED={len(removed)}")
    for item in removed[:24]:
        print(f"  RESET: {item}")
    if len(removed) > 24:
        print(f"  RESET: ... +{len(removed) - 24} artefatos")


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
    for attempt in range(retries + 1):
        proc = subprocess.run(
            [sys.executable, str(path), *args],
            cwd=str(BASE),
            env=env,
            check=False,
        )
        last = proc.returncode
        if last == 0:
            print(f"ETAPA OK: {title}")
            return
        if attempt < retries:
            if script == "midia.py":
                print("MEDIA_RETRY_RESET=YES")
                reset_media_tail(sid)
            delay = min(8, 2 * (attempt + 1))
            print(
                f"AUTO-RECOVERY {attempt + 1}/{retries}: {script} retornou {last}; "
                f"nova tentativa em {delay}s"
            )
            time.sleep(delay)

    raise RuntimeError(f"{script} falhou com código {last}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retoma ShortAutoPro após correções semânticas/de mídia"
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
        ("6 - SMART MEDIA SELECTOR", "midia.py", (), 1),
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
    print(" SHORTAUTOPRO - CLEAN RESUME FROM MEDIA")
    print("==============================================")
    print(f"ID: {sid}")
    print("PIPELINE: PROFESSIONAL_CANONICAL")

    try:
        with canonical.RunLock(sid):
            reset_media_tail(sid)
            for title, script, stage_args, retries in stages:
                run_stage(sid, title, script, stage_args, retries)
    except Exception as exc:
        print(f"RESUME_AFTER_SEMANTIC_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    resume = BASE / "resume_short_runtime.py"
    if not resume.is_file():
        print("RESUME_AFTER_SEMANTIC_ERROR=resume_short_runtime.py ausente", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, str(resume), "--short-id", sid],
        cwd=str(BASE),
        env=os.environ.copy(),
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Artifact-validated resume for the single ShortAutoPro 3.0 pipeline.

Resume never switches pipelines. If the saved production does not contain the
Consolidation 3.0 planning artifacts, it restarts through main.py with the same
Short ID rather than trying to interpret legacy state.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import main as canonical
from subprocess_guard import check_output_group, run_group
from runtime_config import env_int
import shortautopro_evolution as evo

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()


def read_json(path: Path) -> dict[str, Any]:
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
    return max(6, min(value, 20))


def scene_count(sid: str) -> int:
    data = read_json(BASE / "roteiros" / f"scene_map_{sid}.json")
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    return len(scenes) if isinstance(scenes, list) else 0


def media_ok(sid: str) -> bool:
    report = read_json(BASE / "roteiros" / f"media_quality_{sid}.json")
    if str(report.get("status", "")).upper() != "PASS" or report.get("critical"):
        return False
    folder = BASE / "imagens" / f"short_{sid}"
    if not folder.is_dir():
        return False
    valid = [
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
        and path.stat().st_size > 1000
    ]
    return len(valid) >= expected_scenes()


def supervisor_ok(sid: str) -> bool:
    data = read_json(BASE / "roteiros" / f"supervisor_{sid}.json")
    return str(data.get("status", "")).upper() in {"PASS", "QUALITY_PASS", "OK"}


def pro_plan_ok(sid: str) -> bool:
    data = read_json(BASE / "roteiros" / f"pro_edit_plan_{sid}.json")
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    return (
        str(data.get("version", "")).startswith("PRO_EDIT_")
        and isinstance(scenes, list)
        and len(scenes) == expected_scenes()
    )


def consolidation_plan_ok(sid: str) -> bool:
    if not pro_plan_ok(sid):
        return False
    required = [
        BASE / "roteiros" / f"retention_{sid}.json",
        BASE / "roteiros" / f"sound_design_{sid}.json",
        BASE / "roteiros" / f"multi_asset_{sid}.json",
        BASE / "roteiros" / f"visual_score_{sid}.json",
        BASE / "roteiros" / f"visual_continuity_{sid}.json",
    ]
    if not all(nonempty(path, 20) for path in required):
        return False
    retention = read_json(required[0])
    return float(retention.get("retention_score", retention.get("score", 0)) or 0) >= float(
        os.getenv("SAP_RETENTION_MIN_SCORE", "78")
    )


def audio_ok(sid: str) -> bool:
    return nonempty(BASE / "audios" / f"short_{sid}.mp3", 5000)


def captions_ok(sid: str) -> bool:
    path = BASE / "videos" / f"short_{sid}.ass"
    if not nonempty(path, 200):
        return False
    try:
        return "Dialogue:" in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def assembly_ok(sid: str) -> bool:
    return nonempty(BASE / "temp" / sid / "video_sem_audio.mp4", 100_000)


def render_ok(sid: str) -> bool:
    video = BASE / "videos" / f"short_v6_{sid}.mp4"
    if not nonempty(video, 100_000) or shutil.which("ffprobe") is None:
        return False
    try:
        raw = check_output_group(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_name,codec_type,width,height",
                "-of", "json", str(video),
            ],
            text=True,
            timeout=45,
        )
        streams = json.loads(raw).get("streams", [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})
        return (
            video_stream.get("codec_name") == "h264"
            and audio_stream.get("codec_name") == "aac"
            and int(video_stream.get("width", 0) or 0) == 1080
            and int(video_stream.get("height", 0) or 0) == 1920
        )
    except Exception:
        return False


def final_ok(sid: str, render_valid: bool | None = None) -> bool:
    quality = read_json(BASE / "manifests" / f"{sid}_quality.json")
    release = read_json(BASE / "manifests" / f"{sid}_release.json")
    if render_valid is None:
        render_valid = render_ok(sid)
    return (
        render_valid
        and quality.get("approved") is True
        and release.get("decision") in {"PUBLISH", "ACCEPTABLE"}
    )


def boundary(sid: str) -> str:
    render_valid = render_ok(sid)
    if final_ok(sid, render_valid):
        return "complete"
    # Never partially resume an older architecture. This is intentionally
    # conservative because new 3.0 gates depend on these planning artifacts.
    if not consolidation_plan_ok(sid):
        return "full"
    if render_valid:
        return "post_render"
    if assembly_ok(sid) and audio_ok(sid) and captions_ok(sid):
        return "post_assembly"
    if captions_ok(sid) and audio_ok(sid):
        return "post_captions"
    if audio_ok(sid):
        return "post_audio"
    if supervisor_ok(sid) and media_ok(sid) and scene_count(sid) == expected_scenes():
        return "post_planning"
    return "full"


def checkpoint(stage: str, status: str, title: str, sid: str) -> None:
    try:
        evo.checkpoint(stage, status, title, sid)
    except Exception:
        pass


def run_python(
    sid: str,
    title: str,
    script: str,
    *args: str,
    allow: set[int] | None = None,
) -> int:
    path = BASE / script
    if not path.is_file():
        raise RuntimeError(f"arquivo ausente: {script}")
    print(f"\n--- {title} ---")
    checkpoint(script, "start", title, sid)
    try:
        stage_timeout = int(
            os.getenv("SAP_STAGE_TIMEOUT_SECONDS", "1800") or 1800
        )
    except (TypeError, ValueError):
        stage_timeout = 1800
    stage_timeout = max(60, min(stage_timeout, 7200))
    try:
        result = run_group(
            [sys.executable, str(path), *args],
            cwd=str(BASE),
            env=os.environ.copy(),
            timeout=stage_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        checkpoint(script, "fail", title, sid)
        raise RuntimeError(
            f"{script} excedeu timeout de {stage_timeout}s"
        ) from exc
    allowed = allow or {0}
    if result.returncode not in allowed:
        checkpoint(script, "fail", title, sid)
        raise RuntimeError(f"{script} falhou com código {result.returncode}")
    checkpoint(script, "pass", title, sid)
    return result.returncode


def full_rerun(sid: str) -> int:
    main_path = BASE / "main.py"
    if not main_path.is_file():
        raise RuntimeError("main.py ausente")
    print("Checkpoint parcial incompatível ou insuficiente. Reexecutando o pipeline oficial com o mesmo ID.")
    env = os.environ.copy()
    env["SHORT_ID"] = sid
    rerun_timeout = env_int("SAP_RESUME_FULL_RERUN_TIMEOUT", 7200, 600, 21600)
    try:
        return run_group(
            [sys.executable, str(main_path), "run"],
            cwd=str(BASE),
            env=env,
            timeout=rerun_timeout,
        ).returncode
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"full rerun excedeu timeout de {rerun_timeout}s"
        ) from exc


def copy_download(sid: str) -> str:
    final = BASE / "videos" / f"short_v6_{sid}.mp4"
    downloads = Path(os.path.expanduser("~/storage/shared/Download"))
    if downloads.is_dir() and final.is_file():
        target = downloads / f"ShortAutoPro_{sid}.mp4"
        tmp = downloads / f".{target.name}.{os.getpid()}.tmp"
        try:
            source_size = final.stat().st_size
            if source_size < 500_000:
                return str(final)
            with final.open("rb") as src, tmp.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
            if tmp.stat().st_size != source_size:
                raise RuntimeError("exportação resume incompleta")
            os.replace(tmp, target)
            return str(target)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
    return str(final)


def final_gates(sid: str) -> int:
    stages = [
        ("EVOLUTION E2E", "shortautopro_evolution.py", ("e2e",)),
        ("QUALITY GATE", "quality_check.py", ()),
        ("PUBLISH PACK", "publish_pack.py", ()),
        ("SOURCE LEDGER", "source_ledger.py", ()),
        ("PUBLISH INTEGRITY", "publish_integrity_gate.py", ()),
        ("PRODUCTION MANIFEST", "production_manifest.py", ()),
        ("FINAL QUALITY", "final_quality.py", ()),
    ]
    for title, script, args in stages:
        run_python(sid, title, script, *args)
    quality_args = ["quality-score"] + (["--enforce"] if os.getenv("SAP_EVOLUTION_ENFORCE", "0") == "1" else [])
    run_python(sid, "EVOLUTION QUALITY SCORE", "shortautopro_evolution.py", *quality_args)
    run_python(sid, "PROFESSIONAL QUALITY GATE", "professional_quality_gate.py")
    return run_python(sid, "SHORTAUTOPRO RELEASE GATE", "release_gate.py", "--enforce", allow={0, 20})


def render_tail(sid: str) -> None:
    run_python(sid, "PROFESSIONAL MULTI-BEAT ASSEMBLER", "video_professional.py")
    run_python(sid, "FINAL RENDER V6 PROFESSIONAL", "v6_professional.py")
    if not render_ok(sid):
        raise RuntimeError("renderer terminou sem artefato técnico válido")
    run_python(sid, "FINAL AUDIO MASTER", "audio_finalizer.py")
    run_python(sid, "VISUAL QA", "visual_qa.py")


def resume(sid: str) -> int:
    os.environ["SHORT_ID"] = sid
    point = boundary(sid)
    print("========================================")
    print(" SHORTAUTOPRO 3.0 - SAFE RESUME")
    print("========================================")
    print(f"ID: {sid}")
    print("Pipeline: PROFESSIONAL_CANONICAL")
    print(f"Boundary: {point}\n")

    if point == "complete":
        print("Produção já aprovada pelo Release Gate.")
        return 0
    if point == "full":
        return full_rerun(sid)

    try:
        with canonical.RunLock(sid):
            order = {
                "post_planning": 1,
                "post_audio": 2,
                "post_captions": 3,
                "post_assembly": 4,
                "post_render": 5,
            }
            rank = order[point]

            if rank <= 1:
                run_python(sid, "FINAL EDITORIAL GATE", "editorial_gate.py")
                run_python(sid, "SPEECH DIRECTOR", "speech_director.py")
                run_python(sid, "GERANDO VOZ PIPER", "audio.py")
            if rank <= 2:
                run_python(sid, "WHISPER + LEGENDA", "legenda_dinamica.py")
                run_python(sid, "PROFESSIONAL CAPTION DIRECTOR", "professional_caption_director.py")
                run_python(sid, "CAPTION SAFE-ZONE GUARD", "caption_layout_guard.py")
                run_python(sid, "CAPTION AUDIT", "shortautopro_evolution.py", "caption-audit")
            if rank <= 3:
                render_tail(sid)
            elif rank <= 4:
                run_python(sid, "FINAL RENDER V6 PROFESSIONAL", "v6_professional.py")
                if not render_ok(sid):
                    raise RuntimeError("renderer terminou sem artefato técnico válido")
                run_python(sid, "FINAL AUDIO MASTER", "audio_finalizer.py")
                run_python(sid, "VISUAL QA", "visual_qa.py")
            else:
                run_python(sid, "FINAL AUDIO MASTER", "audio_finalizer.py")
                run_python(sid, "VISUAL QA", "visual_qa.py")

            code = final_gates(sid)
            if code == 20:
                run_python(sid, "REPAIR EDIT", "professional_edit_repair.py")
                run_python(sid, "REPAIR MULTI-ASSET", "multi_asset_director.py")
                run_python(sid, "REPAIR RETENTION", "retention_engine.py", "--repair")
                run_python(sid, "REPAIR SOUND", "sound_design_engine.py")
                render_tail(sid)
                code = final_gates(sid)
            if code == 20 or not final_ok(sid):
                raise RuntimeError("retomada terminou sem Release Gate aprovado")

            run_python(sid, "REGISTRANDO ASSUNTO", "register_topic.py")
            destination = copy_download(sid)
            evo.finish_production("SUCCESS", sid)
            print("\nRESUME_STATUS=PASS")
            print("PIPELINE=PROFESSIONAL_CANONICAL")
            print(f"Vídeo: {destination}")
            return 0
    except Exception as exc:
        evo.finish_production("FAILED", sid)
        print(f"RESUME_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def latest_incomplete() -> str | None:
    if not evo.STATE_DIR.is_dir():
        return None
    states = []
    for path in evo.STATE_DIR.glob("*.json"):
        try:
            states.append((path.stat().st_mtime, path))
        except OSError:
            continue
    ordered = [path for _, path in sorted(states, key=lambda item: item[0], reverse=True)]
    for path in ordered:
        data = read_json(path)
        if str(data.get("production_status", "")).upper() != "SUCCESS":
            return path.stem
    return ordered[0].stem if ordered else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume the canonical ShortAutoPro 3.0 pipeline")
    parser.add_argument("--short-id", default=None)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    canonical.source_config()
    canonical.setup_env()
    sid = args.short_id or os.getenv("SHORT_ID", "").strip() or latest_incomplete()
    if not sid:
        print("Nenhuma produção encontrada para retomar.")
        return 0
    if args.status:
        print(
            json.dumps(
                {
                    "short_id": sid,
                    "pipeline": "PROFESSIONAL_CANONICAL",
                    "boundary": boundary(sid),
                    "consolidation_plan": consolidation_plan_ok(sid),
                    "plan": evo.resume_plan(sid),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    return resume(sid)


if __name__ == "__main__":
    raise SystemExit(main())

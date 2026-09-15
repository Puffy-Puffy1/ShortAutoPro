#!/usr/bin/env python3
"""Resume ShortAutoPro from conservative, artifact-validated boundaries.

One runtime serves both Professional Edit and the explicit standard rollback.
The early narrative/media chain is intentionally NOT skipped unless the
Production Supervisor boundary is proven. Professional partial resume also
requires a valid professional edit plan before any stage can be skipped.
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

import shortautopro_evolution as evo

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()


def professional_enabled() -> bool:
    return os.getenv("SAP_PRO_EDIT", "1").strip() == "1"


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


def scene_count(sid: str) -> int:
    data = read_json(BASE / "roteiros" / f"scene_map_{sid}.json")
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    return len(scenes) if isinstance(scenes, list) else 0


def expected_scenes() -> int:
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except ValueError:
        value = 12
    return max(6, min(value, 20))


def media_ok(sid: str) -> bool:
    """Only certify the media boundary after Media Master Gate PASS."""
    report = read_json(BASE / "roteiros" / f"media_quality_{sid}.json")
    if str(report.get("status", "")).upper() != "PASS":
        return False
    if report.get("critical"):
        return False

    folder = BASE / "imagens" / f"short_{sid}"
    if not folder.is_dir():
        return False
    valid = [
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
        and p.stat().st_size > 1000
    ]
    return len(valid) >= expected_scenes()


def supervisor_ok(sid: str) -> bool:
    data = read_json(BASE / "roteiros" / f"supervisor_{sid}.json")
    status = str(data.get("status", "")).upper()
    state = evo.load_state(sid)
    stage = state.get("stages", {}).get("production_supervisor.py", {}) if isinstance(state.get("stages"), dict) else {}
    return status in {"PASS", "QUALITY_PASS", "OK"} and isinstance(stage, dict) and stage.get("status") == "PASS"


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
        raw = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_name,codec_type,width,height", "-of", "json", str(video),
        ], text=True, timeout=45)
        data = json.loads(raw)
        streams = data.get("streams", [])
        v = next((x for x in streams if x.get("codec_type") == "video"), {})
        a = next((x for x in streams if x.get("codec_type") == "audio"), {})
        return (
            v.get("codec_name") == "h264" and a.get("codec_name") == "aac"
            and int(v.get("width", 0) or 0) == 1080 and int(v.get("height", 0) or 0) == 1920
        )
    except Exception:
        return False


def final_ok(sid: str) -> bool:
    quality = read_json(BASE / "manifests" / f"{sid}_quality.json")
    return render_ok(sid) and quality.get("approved") is True


def pro_plan_ok(sid: str) -> bool:
    data = read_json(BASE / "roteiros" / f"pro_edit_plan_{sid}.json")
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    return (
        str(data.get("version", "")).startswith("PRO_EDIT_")
        and isinstance(scenes, list)
        and len(scenes) == expected_scenes()
    )


def base_boundary(sid: str) -> str:
    if final_ok(sid):
        return "complete"
    if render_ok(sid):
        return "post_render"
    if assembly_ok(sid) and audio_ok(sid) and captions_ok(sid):
        return "post_assembly"
    if captions_ok(sid) and audio_ok(sid) and supervisor_ok(sid) and media_ok(sid):
        return "post_captions"
    if audio_ok(sid) and supervisor_ok(sid) and media_ok(sid):
        return "post_audio"
    if supervisor_ok(sid) and media_ok(sid) and scene_count(sid) == expected_scenes():
        return "post_media"
    return "full"


def boundary(sid: str) -> str:
    point = base_boundary(sid)
    if professional_enabled() and point not in {"complete", "full"} and not pro_plan_ok(sid):
        return "full"
    return point


def checkpoint(stage: str, status: str, title: str, sid: str) -> None:
    try:
        evo.checkpoint(stage, status, title, sid)
    except Exception:
        pass


def run_python(sid: str, title: str, script: str, *args: str) -> None:
    path = BASE / script
    if not path.is_file():
        raise RuntimeError(f"arquivo ausente: {script}")
    print(f"\n--- {title} ---")
    checkpoint(script, "start", title, sid)
    result = subprocess.run([sys.executable, str(path), *args], cwd=str(BASE), env=os.environ.copy())
    if result.returncode != 0:
        checkpoint(script, "fail", title, sid)
        raise RuntimeError(f"{script} falhou com código {result.returncode}")
    checkpoint(script, "pass", title, sid)


def acquire_generation_lock():
    try:
        import fcntl
    except ImportError:
        return None
    lock_root = BASE / ".locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    handle = (lock_root / "gerar_short.lock").open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError("já existe uma geração ShortAutoPro em andamento")
    return handle


def copy_download(sid: str) -> str:
    final = BASE / "videos" / f"short_v6_{sid}.mp4"
    downloads = Path(os.path.expanduser("~/storage/shared/Download"))
    if downloads.is_dir() and final.is_file():
        target = downloads / f"ShortAutoPro_{sid}.mp4"
        try:
            shutil.copy2(final, target)
            if target.stat().st_size > 0:
                return str(target)
        except Exception:
            pass
    return str(final)


def full_rerun(sid: str) -> int:
    generator = BASE / "gerar_short.sh"
    if not generator.is_file():
        raise RuntimeError("gerar_short.sh ausente")
    mode = "profissional" if professional_enabled() else "standard rollback"
    print(f"Nenhum checkpoint parcial é seguro. Reexecutando pipeline completo ({mode}).")
    env = os.environ.copy()
    env["SHORT_ID"] = sid
    env["SAP_PRO_EDIT"] = "1" if professional_enabled() else "0"
    return subprocess.run(["bash", str(generator)], cwd=str(BASE), env=env).returncode


def resume(sid: str) -> int:
    os.environ["SHORT_ID"] = sid
    point = boundary(sid)
    pro = professional_enabled()
    mode = "PROFESSIONAL" if pro else "STANDARD_ROLLBACK"
    print("========================================")
    print(" SHORTAUTOPRO - UNIFIED SAFE RESUME")
    print("========================================")
    print(f"ID: {sid}")
    print(f"Mode: {mode}")
    print(f"Boundary: {point}")
    print()

    if point == "complete":
        print("Produção já possui vídeo e Quality Gate aprovados.")
        return 0
    if point == "full":
        return full_rerun(sid)

    lock = acquire_generation_lock()
    try:
        order = {"post_media": 1, "post_audio": 2, "post_captions": 3, "post_assembly": 4, "post_render": 5}
        rank = order[point]
        if rank <= 1:
            if pro:
                run_python(sid, "PROFESSIONAL EDIT DIRECTOR", "professional_edit_director.py")
                run_python(sid, "PROFESSIONAL EDIT AUTO-REPAIR", "professional_edit_repair.py")
            run_python(sid, "FINAL EDITORIAL GATE", "editorial_gate.py")
            run_python(sid, "GERANDO VOZ PIPER", "audio.py")
        if rank <= 2:
            run_python(sid, "WHISPER + LEGENDA", "legenda_dinamica.py")
            if pro:
                run_python(sid, "PROFESSIONAL CAPTION DIRECTOR", "professional_caption_director.py")
            run_python(sid, "CAPTION AUDIT", "shortautopro_evolution.py", "caption-audit")
        if rank <= 3:
            if pro:
                run_python(sid, "PROFESSIONAL SCENE ASSEMBLER", "video_professional.py")
            else:
                run_python(sid, "MONTANDO CENAS", "video.py")
        if rank <= 4:
            run_python(sid, "RENDER FINAL V6", "v6_runtime.py")
            if not render_ok(sid):
                raise RuntimeError("V6 terminou sem artefato técnico válido")

        run_python(sid, "EVOLUTION E2E", "shortautopro_evolution.py", "e2e")
        run_python(sid, "QUALITY GATE", "quality_check.py")
        run_python(sid, "PUBLISH PACK", "publish_pack.py")
        run_python(sid, "SOURCE LEDGER", "source_ledger.py")
        run_python(sid, "PUBLISH INTEGRITY", "publish_integrity_gate.py")
        run_python(sid, "PRODUCTION MANIFEST", "production_manifest.py")
        run_python(sid, "FINAL QUALITY", "final_quality.py")
        quality_args = ["quality-score"]
        if os.getenv("SAP_EVOLUTION_ENFORCE", "0") == "1":
            quality_args.append("--enforce")
        run_python(sid, "EVOLUTION QUALITY SCORE", "shortautopro_evolution.py", *quality_args)
        if pro:
            run_python(sid, "PROFESSIONAL QUALITY GATE", "professional_quality_gate.py")
        if not final_ok(sid):
            raise RuntimeError("retomada terminou sem Quality Gate aprovado")
        run_python(sid, "REGISTRANDO ASSUNTO", "register_topic.py")
        destination = copy_download(sid)
        evo.finish_production("SUCCESS", sid)
        print("\nRESUME_STATUS=PASS")
        print(f"MODE={mode}")
        print(f"Vídeo: {destination}")
        return 0
    except Exception as exc:
        evo.finish_production("FAILED", sid)
        print(f"RESUME_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if lock is not None:
            try:
                lock.close()
            except Exception:
                pass


def latest_incomplete() -> str | None:
    if not evo.STATE_DIR.is_dir():
        return None
    states = sorted(evo.STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in states:
        data = read_json(path)
        if str(data.get("production_status", "")).upper() != "SUCCESS":
            return path.stem
    return states[0].stem if states else None


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro unified safe resume runtime")
    parser.add_argument("--short-id", default=None)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    sid = args.short_id or os.getenv("SHORT_ID", "").strip() or latest_incomplete()
    if not sid:
        print("Nenhuma produção encontrada para retomar.")
        return 0
    if args.status:
        payload = {
            "short_id": sid,
            "mode": "PROFESSIONAL" if professional_enabled() else "STANDARD_ROLLBACK",
            "boundary": boundary(sid),
            "plan": evo.resume_plan(sid),
        }
        if professional_enabled():
            payload["professional_plan"] = pro_plan_ok(sid)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    return resume(sid)


if __name__ == "__main__":
    raise SystemExit(main())

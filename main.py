#!/usr/bin/env python3
"""ShortAutoPro canonical entrypoint — Consolidation 3.0.

Official Short flow:
  tema -> roteiro -> cenas -> midia -> audio -> legenda -> edicao -> QA -> exportacao

There is exactly one production pipeline. Specialized files are stages, never
alternate pipelines. Recovery means resuming validated checkpoints from this
same pipeline, not switching to a legacy renderer or assembler.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import shortautopro_evolution as evo
import production_profiler
from subprocess_guard import run_group

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
EVOLUTION = BASE / "shortautopro_evolution.py"
STATE_DIR = BASE / ".sap_state"
LOCK_DIR = BASE / ".locks" / "runs"

DEFAULT_ENV = {
    "SAP_VQE5": "1",
    "SAP_VQE5_RESCUE": "1",
    "SAP_VQE5_QUERY_EXTRA": "2",
    "SAP_VQE5_COMMIT": "1",
    # Retired experimental selectors stay disabled. VI6 ACTIVE is the
    # conservative semantic/documentary layer on top of the canonical selector.
    "SAP_VSE_V2": "0",
    "SAP_VSE_V3": "0",
    "SAP_VSE_V4": "0",
    "SAP_VSE_V42": "0",
    "SAP_VSE4": "0",
    "SAP_VSE42": "0",
    "SAP_VSE4_RUNTIME": "0",
    "SAP_SCENE_COMMIT_LOCK": "0",
    "VISUAL_INTELLIGENCE_MODE": "ACTIVE",
    "VISUAL_INTELLIGENCE_6_SHADOW": "1",
    "SAP_PROFESSIONAL_MIN_SCORE": "88",
    "SAP_PROFESSIONAL_ENFORCE": "0",
    "SAP_PRO_MEDIA_MIN_PIXELS": "921600",
    "SAP_RETENTION_MIN_SCORE": "78",
    "SAP_VISUAL_SCORE_MIN": "72",
    "SAP_RELEASE_ENFORCE": "1",
    "SAP_MULTI_ASSET_MAX": "4",
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def source_config() -> None:
    cfg = BASE / "config.sh"
    if not cfg.is_file():
        raise RuntimeError("config.sh não encontrado")
    proc = subprocess.run(
        ["bash", "-c", 'set -a; source "$1"; env -0', "bash", str(cfg)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError("config.sh falhou ao carregar")
    for item in proc.stdout.split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        try:
            os.environ[key.decode()] = value.decode()
        except UnicodeDecodeError:
            continue


def setup_env() -> None:
    for key, value in DEFAULT_ENV.items():
        os.environ.setdefault(key, value)
    os.environ["SHORTAUTOPRO_BASE"] = str(BASE)


def allocate_id() -> str:
    existing = os.getenv("SHORT_ID", "").strip()
    allow_reuse = os.getenv("SAP_REUSE_SHORT_ID", "0").strip() == "1"

    if existing:
        if allow_reuse:
            return existing

        artifact_candidates = (
            STATE_DIR / f"pipeline_{existing}.json",
            BASE / "videos" / f"short_v6_{existing}.mp4",
            BASE / "roteiros" / f"scene_map_{existing}.json",
            BASE / "roteiros" / f"short_{existing}.txt",
        )
        if not any(path.exists() for path in artifact_candidates):
            return existing

        print(
            "SAP_SHORT_ID_STALE_ENV=IGNORED "
            f"id={existing} reason=EXISTING_ARTIFACTS"
        )

    return datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + secrets.token_hex(3)


class RunLock:
    """Per-production lock: different Short IDs may run concurrently."""

    def __init__(self, sid: str):
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LOCK_DIR / f"{sid}.lock"
        self.handle = None

    def __enter__(self):
        self.handle = self.path.open("a+")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"produção {self.path.stem} já está em andamento") from exc
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(str(os.getpid()))
        self.handle.flush()
        return self

    def __exit__(self, *_):
        if self.handle:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.handle.close()
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass


class Pipeline:
    def __init__(self, sid: str):
        self.sid = sid
        self.state_path = STATE_DIR / f"pipeline_{sid}.json"
        self.state = {
            "short_id": sid,
            "version": "CONSOLIDATION_3_0",
            "pipeline": "PROFESSIONAL_CANONICAL",
            "started_at": now(),
            "status": "RUNNING",
            "stages": [],
        }
        atomic_json(self.state_path, self.state)

    def checkpoint(self, name: str, status: str, title: str, elapsed: float | None = None) -> None:
        entry = {"stage": name, "title": title, "status": status, "at": now()}
        if elapsed is not None:
            entry["elapsed_seconds"] = round(elapsed, 3)
        self.state["stages"].append(entry)
        self.state["updated_at"] = now()
        atomic_json(self.state_path, self.state)
        try:
            evo.checkpoint(name, status, title, self.sid)
        except Exception:
            pass

    def finish(self, status: str) -> None:
        self.state["status"] = status
        self.state["finished_at"] = now()
        atomic_json(self.state_path, self.state)
        try:
            evo.finish_production(status, self.sid)
        except Exception:
            pass

    def run(
        self,
        title: str,
        file: str,
        *args: str,
        shell: bool = False,
        retries: int = 0,
        allow_codes: set[int] | None = None,
    ) -> int:
        path = BASE / file
        if not path.is_file():
            raise RuntimeError(f"arquivo obrigatório ausente: {file}")
        allow_codes = allow_codes or {0}
        print(f"\n{'-' * 48}\n{title}\n{'-' * 48}\n")
        self.checkpoint(file, "start", title)
        start = time.monotonic()
        last = 1
        cmd: list[str] = []
        for attempt in range(retries + 1):
            cmd = ["bash", str(path), *args] if shell else [sys.executable, str(path), *args]
            try:
                stage_timeout = int(
                    os.getenv("SAP_STAGE_TIMEOUT_SECONDS", "1800") or 1800
                )
            except (TypeError, ValueError):
                stage_timeout = 1800
            stage_timeout = max(60, min(stage_timeout, 7200))

            try:
                proc = run_group(
                    cmd,
                    cwd=BASE,
                    env=os.environ.copy(),
                    check=False,
                    timeout=stage_timeout,
                )
                last = proc.returncode
            except subprocess.TimeoutExpired as exc:
                elapsed = time.monotonic() - start
                self.checkpoint(file, "fail", title, elapsed)
                try:
                    production_profiler.record(
                        file,
                        elapsed,
                        short_id=self.sid,
                        category="pipeline_stage",
                        status="timeout",
                        title=title,
                        timeout_seconds=stage_timeout,
                    )
                except Exception:
                    pass
                raise RuntimeError(
                    f"{file} excedeu timeout de {stage_timeout}s"
                ) from exc
            if last in allow_codes:
                elapsed = time.monotonic() - start
                self.checkpoint(file, "pass", title, elapsed)
                try:
                    production_profiler.record(
                        file,
                        elapsed,
                        short_id=self.sid,
                        category="pipeline_stage",
                        status="pass",
                        title=title,
                    )
                except Exception:
                    pass
                print(f"ETAPA OK: {elapsed:.1f}s")
                return last
            if attempt < retries:
                print(f"AUTO-RECOVERY {attempt + 1}/{retries}: {file} retornou {last}")
                time.sleep(min(8, 2 * (attempt + 1)))
        elapsed = time.monotonic() - start
        self.checkpoint(file, "fail", title, elapsed)
        try:
            production_profiler.record(
                file,
                elapsed,
                short_id=self.sid,
                category="pipeline_stage",
                status="fail",
                title=title,
                returncode=last,
            )
        except Exception:
            pass
        raise subprocess.CalledProcessError(last, cmd)


def probe_video(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration,size",
                "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate",
                "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=45,
        )
        return json.loads(proc.stdout)
    except Exception:
        return {}


def stages_before_render(p: Pipeline) -> None:
    p.run("0 - LEGACY RUNTIME PURGE", "tools/purge_legacy_runtime.py")
    p.run("PREFLIGHT CHECK", "preflight_check.sh", shell=True)
    p.run("HEALTH CHECK", "health_check.sh", shell=True)
    p.run("STORAGE PREFLIGHT", "storage_manager.py", "preflight")
    p.run("1 - TOPIC ENGINE", "topic_engine_runtime.py", retries=1)
    p.run("2 - ROTEIRO + PESQUISA FACTUAL", "script_runtime.py")
    p.run("2A - INTELLIGENCE PRE: STORY + CLAIM LOCK", "shortauto_intelligence_layer.py", "pre", "--short-id", p.sid)
    p.run("3 - CONFIRMANDO ASSUNTO", "used_topic.py")
    p.run("4 - HOOK ENGINE", "hook_runtime.py")
    p.run("4B - NARRATIVE DIRECTOR", "narrative_director.py", retries=1)
    p.run("4C - COLD OPEN DIRECTOR", "cold_open_director.py", retries=1)
    p.run("5 - SCENE DIRECTOR", "scene_director.py")
    p.run("5A0 - SCENE TRUTH REFINER", "scene_truth_refiner_6_7.py")
    p.run("5A - DOCUMENTARY DIRECTOR", "documentary_director.py")
    p.run("5B - AI VISUAL DIRECTOR", "visual_director.py", retries=1)
    p.run("5B0 - DIRECTOR AI PROVENANCE + VISUAL INTENT", "shortauto_director_ai.py")
    p.run("5B0A - INTELLIGENCE SCENE: ENTITY/TIME/GEO/VISUAL ROLES", "shortauto_intelligence_layer.py", "scene", "--short-id", p.sid)
    p.run("5B1 - HUMANIZED SHOT GRAMMAR", "visual_shot_bridge.py")
    p.run("5C - FACTUAL VISUAL RISK GUARD", "visual_risk_guard.py")
    p.run("5D - EDITORIAL CONTINUITY GUARD", "editorial_continuity.py")
    p.run("5D0 - VISUAL CONTINUITY SCORE", "visual_continuity_engine.py")
    p.run("5D1 - LOSSLESS COVERAGE REPAIR", "scene_lossless_repair.py")
    p.run("5D2 - POST-SCRIPT TRUTH LOCK", "post_script_truth_lock.py")
    p.run("5E - SEMANTIC INTEGRITY GATE", "semantic_integrity_gate.py")

    p.run("6 - SMART MEDIA SELECTOR", "media_stage_runtime.py")
    p.run("6A - MEDIA MASTER GATE", "media_master_gate.py")
    p.run("6A0 - ASSET LIBRARY + FIRST FRAME", "shortauto_asset_library.py", "index", "--short-id", p.sid)
    p.run("6A0A - INTELLIGENCE MEDIA: SOURCE/CACHE/AGING", "shortauto_intelligence_layer.py", "media", "--short-id", p.sid)
    p.run("6A1 - MULTIDIMENSIONAL VISUAL SCORE", "visual_score_engine.py")
    p.run("6B - CINEMATIC MOTION DIRECTOR", "motion_director.py")
    p.run("6C - MONTAGE RHYTHM DIRECTOR", "rhythm_director.py")
    p.run("6C1 - PROFESSIONAL EDIT DIRECTOR", "professional_edit_director.py")
    p.run("6C2 - PROFESSIONAL EDIT AUTO-REPAIR", "professional_edit_repair.py")
    p.run("6C2B - MULTI-ASSET DIRECTOR", "multi_asset_director.py", retries=1)
    p.run("6C3 - RETENTION ENGINE + SAFE REPAIR", "retention_engine.py", "--repair", "--enforce")
    p.run("6C4 - SOUND DESIGN ENGINE", "sound_design_engine.py")
    p.run("6D - PRODUCTION SUPERVISOR", "production_supervisor.py")
    p.run("6D1 - EVOLUTION VISUAL AUDIT", "shortautopro_evolution.py", "visual-audit")
    p.run("6E - FINAL EDITORIAL GATE", "editorial_gate.py")

    p.run("6F - SPEECH DIRECTOR", "speech_director.py")
    p.run("7 - VOZ PIPER", "audio.py", retries=1)
    p.run("8 - WHISPER + LEGENDA DINÂMICA", "legenda_dinamica.py", retries=1)
    p.run("8A - PROFESSIONAL CAPTION DIRECTOR", "professional_caption_director.py")
    p.run("8A1 - CAPTION SAFE-ZONE GUARD", "caption_layout_guard.py")
    p.run("8B - EVOLUTION CAPTION AUDIT", "shortautopro_evolution.py", "caption-audit")


def assemble_and_render(p: Pipeline) -> None:
    p.run("9 - PROFESSIONAL MULTI-BEAT ASSEMBLER", "video_professional.py")
    p.run("10 - FINAL RENDER V6 PROFESSIONAL", "v6_professional.py", retries=1)
    final = BASE / "videos" / f"short_v6_{p.sid}.mp4"
    if not final.is_file() or final.stat().st_size < 500_000:
        raise RuntimeError(f"vídeo final ausente/inválido: {final}")
    p.run("10.1 - FINAL AUDIO MEASURED MASTER", "audio_finalizer.py")
    p.run("10.2 - VISUAL QA", "visual_qa.py")


def final_gates(p: Pipeline) -> int:
    p.run("10A - EVOLUTION E2E", "shortautopro_evolution.py", "e2e")
    p.run("10B - QUALITY GATE", "quality_check.py")
    p.run("11A - PUBLISH PACK", "publish_pack.py")
    p.run("11B - SOURCE & ATTRIBUTION LEDGER", "source_ledger.py")
    p.run("11C - PUBLISH INTEGRITY", "publish_integrity_gate.py")
    p.run("12A - PRODUCTION MANIFEST", "production_manifest.py")
    p.run("12B - FINAL QUALITY", "final_quality.py")
    evo_args = ["quality-score"] + (["--enforce"] if os.getenv("SAP_EVOLUTION_ENFORCE", "0") == "1" else [])
    p.run("12C - EVOLUTION QUALITY SCORE", "shortautopro_evolution.py", *evo_args)
    p.run("12D - PROFESSIONAL QUALITY GATE", "professional_quality_gate.py")
    p.run("12D1 - INTELLIGENCE FINAL: EXPLAINABLE QA + CONFIDENCE", "shortauto_intelligence_layer.py", "final", "--short-id", p.sid)
    enforce = os.getenv("SAP_RELEASE_ENFORCE", "1") == "1"
    return p.run(
        "12E - SHORTAUTOPRO RELEASE GATE",
        "release_gate.py",
        *(["--enforce"] if enforce else []),
        allow_codes={0, 20},
    )


def repair_cycle(p: Pipeline) -> None:
    print("\nRELEASE GATE solicitou auto-reparo limitado (1 ciclo).")
    code = p.run(
        "REPAIR - EVIDENCE-DRIVEN REPAIR ENGINE",
        "shortauto_repair_engine.py",
        "--short-id", p.sid, "--execute", "--max-cycles", "1",
        allow_codes={0, 20},
    )
    if code == 20:
        print("REPAIR ENGINE=HOLD; mantendo gates rígidos e seguindo para revalidação canônica.")
    p.run("REPAIR - MULTI-ASSET", "multi_asset_director.py", retries=1)
    p.run("REPAIR - SOUND PLAN", "sound_design_engine.py")
    assemble_and_render(p)


def export(p: Pipeline) -> Path:
    final = BASE / "videos" / f"short_v6_{p.sid}.mp4"
    downloads = Path.home() / "storage" / "shared" / "Download"
    destination = final
    if downloads.is_dir():
        candidate = downloads / f"ShortAutoPro_{p.sid}.mp4"
        try:
            shutil.copy2(final, candidate)
            if candidate.stat().st_size > 0:
                destination = candidate
        except Exception as exc:
            print(f"AVISO: cópia para Downloads falhou: {exc}")
    p.run("REGISTRANDO ASSUNTO", "register_topic.py")
    return destination


def run_pipeline() -> int:
    source_config()
    setup_env()
    sid = allocate_id()
    os.environ["SHORT_ID"] = sid
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        production_profiler.begin_run(sid)
    except Exception:
        pass

    with RunLock(sid):
        p = Pipeline(sid)
        print("\n==============================================")
        print(" SHORTAUTOPRO CONSOLIDATION 3.0 - MAIN.PY")
        print("==============================================")
        print(f"ID: {sid}")
        print("FLUXO: tema -> roteiro -> cenas -> midia -> audio -> legenda -> edicao -> QA -> exportacao")
        print("PIPELINE: PROFESSIONAL_CANONICAL")
        try:
            stages_before_render(p)
            assemble_and_render(p)
            code = final_gates(p)
            if code == 20:
                repair_cycle(p)
                code = final_gates(p)
                if code == 20:
                    raise RuntimeError("Release Gate ainda requer reparo após ciclo automático")
            destination = export(p)
            p.run("STORAGE CLEANUP", "storage_manager.py", "cleanup", "--execute")
            p.checkpoint("pipeline", "pass", "ShortAutoPro Consolidation 3.0")
            p.finish("SUCCESS")
        except Exception as exc:
            p.checkpoint("pipeline", "fail", "ShortAutoPro Consolidation 3.0")
            p.finish("FAILED")
            print(f"\nPIPELINE BLOCKED: {exc}")
            return 1

        info = probe_video(BASE / "videos" / f"short_v6_{sid}.mp4")
        release_path = BASE / "manifests" / f"{sid}_release.json"
        release = json.loads(release_path.read_text(encoding="utf-8")) if release_path.is_file() else {}
        print("\n==============================================")
        print(" PRODUÇÃO FINALIZADA")
        print("==============================================")
        print(f"ID: {sid}")
        print(f"ShortAutoPro Score: {release.get('shortautopro_score', '?')}/100")
        print(f"Release: {release.get('decision', 'UNKNOWN')}")
        print(f"Vídeo: {destination}")
        if info:
            print("Contrato técnico: ffprobe OK")
        return 0


def cli() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro official entrypoint")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run")
    resume = sub.add_parser("resume")
    resume.add_argument("--short-id", default=None)
    resume.add_argument("--status", action="store_true")
    sub.add_parser("audit")
    production = sub.add_parser("production")
    production.add_argument("production_args", nargs=argparse.REMAINDER)
    storage = sub.add_parser("storage")
    storage.add_argument("storage_command", choices=["status", "preflight", "cleanup"], default="status", nargs="?")
    storage.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    command_name = args.command or "run"

    if command_name == "run":
        return run_pipeline()

    setup_env()
    if command_name == "resume":
        command = [sys.executable, str(BASE / "resume_short_runtime.py")]
        if args.short_id:
            command.extend(["--short-id", args.short_id])
        if args.status:
            command.append("--status")
        return subprocess.call(command, cwd=BASE, env=os.environ.copy())
    if command_name == "audit":
        return subprocess.call([sys.executable, str(BASE / "tools" / "repo_audit.py")], cwd=BASE, env=os.environ.copy())
    if command_name == "production":
        command = [
            sys.executable,
            str(BASE / "production_center.py"),
            *list(args.production_args or []),
        ]
        return subprocess.call(command, cwd=BASE, env=os.environ.copy())
    if command_name == "storage":
        command = [sys.executable, str(BASE / "storage_manager.py"), args.storage_command]
        if args.execute:
            command.append("--execute")
        return subprocess.call(command, cwd=BASE, env=os.environ.copy())
    return 2


if __name__ == "__main__":
    raise SystemExit(cli())

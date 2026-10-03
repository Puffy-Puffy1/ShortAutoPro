#!/usr/bin/env python3
"""ShortAutoPro canonical entrypoint — Consolidation 3.0.3.

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
import production_watchdog
from subprocess_guard import run_group
from runtime_config import env_int

# LEGACY_MEDIA_ENGINE_V2_COMPAT = "media_engine_v2.py" — retired from production execution; retained only as an explicit migration/rollback reference.

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
    proc = run_group(
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


def allocate_id(*, reuse_existing: bool = False) -> str:
    """Allocate the production ID.

    A normal `run` is always a fresh-production operation. Reusing an ID is
    only permitted when the caller explicitly opts in (the internal resume
    path). Persistent config/environment flags are intentionally ignored here
    so a completed Short cannot poison the next production.
    """
    existing = os.getenv("SHORT_ID", "").strip()

    if existing:
        if reuse_existing:
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
        except OSError as exc:
            self.handle.close()
            self.handle = None
            if isinstance(exc, BlockingIOError):
                raise RuntimeError(f"produção {self.path.stem} já está em andamento") from exc
            raise
        try:
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.write(str(os.getpid()))
            self.handle.flush()
        except BaseException:
            self.handle.close()
            self.handle = None
            raise
        return self

    def __exit__(self, *_):
        if self.handle:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.handle.close()
            self.handle = None
        # Keep the inode stable: another process may already have this file
        # open while waiting to acquire the lock. Unlinking splits ownership.


class Pipeline:
    def __init__(self, sid: str):
        self.sid = sid
        self.state_path = STATE_DIR / f"pipeline_{sid}.json"
        self.state = {
            "short_id": sid,
            "version": "CONSOLIDATION_3_0_3",
            "pipeline": "PROFESSIONAL_CANONICAL",
            "started_at": now(),
            "updated_at": now(),
            "heartbeat_at": now(),
            "current_stage": "pipeline",
            "last_stage_status": "start",
            "status": "RUNNING",
            "stages": [],
        }
        atomic_json(self.state_path, self.state)
        production_watchdog.record_heartbeat(self.state)

    def checkpoint(self, name: str, status: str, title: str, elapsed: float | None = None) -> None:
        entry = {"stage": name, "title": title, "status": status, "at": now()}
        if elapsed is not None:
            entry["elapsed_seconds"] = round(elapsed, 3)
        self.state["stages"].append(entry)
        self.state["updated_at"] = now()
        self.state["heartbeat_at"] = self.state["updated_at"]
        self.state["current_stage"] = name
        self.state["last_stage_status"] = status
        atomic_json(self.state_path, self.state)
        production_watchdog.record_heartbeat(self.state)
        try:
            evo.checkpoint(name, status, title, self.sid)
        except Exception:
            pass

    def finish(self, status: str) -> None:
        self.state["status"] = status
        self.state["finished_at"] = now()
        self.state["updated_at"] = self.state["finished_at"]
        self.state["heartbeat_at"] = self.state["finished_at"]
        self.state["current_stage"] = "pipeline"
        self.state["last_stage_status"] = status.lower()
        atomic_json(self.state_path, self.state)
        production_watchdog.record_heartbeat(self.state)
        try:
            evo.finish_production(status, self.sid)
        except Exception:
            pass

    def _stage_timeout_seconds(self, file: str) -> int:
        """Return a bounded timeout appropriate for the production stage."""
        explicit = os.getenv("SAP_STAGE_TIMEOUT_SECONDS", "").strip()
        if explicit:
            try:
                return max(60, min(int(explicit), 7200))
            except ValueError:
                pass

        name = str(file or "").strip().lower()

        # Network/AI refinement stages already have their own short retry logic.
        if name in {
            "topic_engine_runtime.py",
            "script_runtime.py",
            "hook_runtime.py",
            "narrative_director.py",
            "cold_open_director.py",
            "scene_director.py",
            "documentary_director.py",
            "visual_director.py",
        }:
            return env_int("SAP_STAGE_TIMEOUT_AI_SECONDS", 240, 60, 900)

        # Media acquisition is explicitly bounded and has emergency completion.
        if name == "media_acquisition_v3.py":
            return env_int("SAP_STAGE_TIMEOUT_MEDIA_ACQUISITION_V3_SECONDS", 1200, 180, 1800)

        # Pre-render recovery may rerun media plus downstream planning once.
        if name == "production_recovery.py":
            return env_int("SAP_STAGE_TIMEOUT_RECOVERY_SECONDS", 1800, 300, 3600)

        # Encoding/rendering legitimately needs more headroom on Android.
        if name in {
            "video_professional.py",
            "v6_professional.py",
            "audio_finalizer.py",
        }:
            return env_int("SAP_STAGE_TIMEOUT_RENDER_SECONDS", 1200, 180, 2400)

        # Analysis/gates should never need 30 minutes.
        return env_int("SAP_STAGE_TIMEOUT_DEFAULT_SECONDS", 600, 60, 1800)

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
            stage_timeout = self._stage_timeout_seconds(file)

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
        proc = run_group(
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
    p.run("5B0B - VISUAL QUERY SPECIFICITY GUARD", "visual_query_guard.py")
    p.run("5B1 - HUMANIZED SHOT GRAMMAR", "visual_shot_bridge.py")
    p.run("5C - FACTUAL VISUAL RISK GUARD", "visual_risk_guard.py")
    p.run("5D - EDITORIAL CONTINUITY GUARD", "editorial_continuity.py")
    p.run("5D0 - VISUAL CONTINUITY SCORE", "visual_continuity_engine.py")
    p.run("5D1 - LOSSLESS COVERAGE REPAIR", "scene_lossless_repair.py")
    p.run("5D2 - POST-SCRIPT TRUTH LOCK", "post_script_truth_lock.py")
    p.run("5E - SEMANTIC INTEGRITY GATE", "semantic_integrity_gate.py")

    # Stage 6 is no longer a production dependency. Media Acquisition V3 owns
    # acquisition/validation/freeze; Render Plan V2 owns deterministic timeline
    # planning; Render Engine V2 owns rendering only.
    p.run("MEDIA ACQUISITION V3 - ACQUIRE + VALIDATE + FREEZE MANIFEST", "media_acquisition_v3.py", "--short-id", p.sid)
    p.run("RENDER PLAN V2 - DETERMINISTIC TIMELINE INPUT", "render_plan_v2.py", "--short-id", p.sid)
    p.run("6F - SPEECH DIRECTOR", "speech_director.py")
    p.run("7 - VOZ PIPER", "audio.py", retries=1)
    p.run("8 - WHISPER + LEGENDA DINÂMICA", "legenda_dinamica.py", retries=1)
    p.run("8A - PROFESSIONAL CAPTION DIRECTOR", "professional_caption_director.py")
    p.run("8A1 - CAPTION SAFE-ZONE GUARD", "caption_layout_guard.py")
    p.run("8B - EVOLUTION CAPTION AUDIT", "shortautopro_evolution.py", "caption-audit")


def assemble_and_render(p: Pipeline) -> None:
    # Fail closed before expensive FFmpeg work. The bounded recovery module
    # repairs only artifacts proven invalid by render_preflight and then this
    # second gate independently certifies the exact render inputs.
    p.run(
        "8C - PRE-RENDER VALIDATION + BOUNDED AUTO-RECOVERY",
        "production_recovery.py",
        "--short-id", p.sid,
    )
    p.run(
        "8D - RENDER PREFLIGHT CERTIFICATION",
        "render_preflight.py",
        "--short-id", p.sid,
    )
    p.run(
        "8E - PRODUCTION HEALTH SNAPSHOT",
        "production_health.py",
        "--short-id", p.sid, "--phase", "pre_render",
    )
    render_engine = os.getenv("RENDER_ENGINE", "v2").strip().lower() or "v2"
    if render_engine != "v2":
        raise RuntimeError(
            "RENDER_ENGINE_LEGACY_DISABLED: Render Engine V2 is the only canonical renderer"
        )
    p.run(
        "9 - RENDER ENGINE V2 (REMOTION + FFMPEG + FFPROBE)",
        "render_engine_v2.py",
        "--short-id",
        p.sid,
    )
    final = BASE / "videos" / f"short_v6_{p.sid}.mp4"
    if not final.is_file() or final.stat().st_size <= 1000:
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
        print(
            "REPAIR ENGINE=HOLD; mantendo gates rígidos e "
            "seguindo para revalidação canônica."
        )

    repair_report = BASE / "reports" / "repair" / f"repair_{p.sid}.json"
    performed: set[str] = set()
    try:
        data = json.loads(repair_report.read_text(encoding="utf-8"))
        history = data.get("history", []) if isinstance(data, dict) else []
        for cycle in history if isinstance(history, list) else []:
            if not isinstance(cycle, dict):
                continue
            for action in cycle.get("actions", []) if isinstance(cycle.get("actions"), list) else []:
                if not isinstance(action, dict):
                    continue
                if str(action.get("status", "")).upper() == "PASS":
                    action_id = str(action.get("id", "") or "").strip()
                    if action_id:
                        performed.add(action_id)
    except Exception as exc:
        print(
            "REPAIR_ACTION_HISTORY=UNAVAILABLE "
            f"{type(exc).__name__}:{str(exc)[:140]}"
        )

    rerender_actions = {
        "media_reacquire",
        "media_quality_refresh",
        "retention_repair",
        "professional_edit_repair",
        "caption_repair",
    }

    if performed.intersection(rerender_actions):
        print(
            "REPAIR_RERENDER=YES actions="
            + ",".join(sorted(performed))
        )
        p.run("REPAIR - MULTI-ASSET", "multi_asset_director.py")
        p.run("REPAIR - SOUND PLAN", "sound_design_engine.py")
        assemble_and_render(p)
    else:
        print(
            "REPAIR_RERENDER=NO actions="
            + (",".join(sorted(performed)) or "none")
        )
        # audio_remaster mutates the final MP4 in place; rebuilding here would
        # discard that correction. Final gates below will revalidate it.


def export(p: Pipeline) -> Path:
    final = BASE / "videos" / f"short_v6_{p.sid}.mp4"
    downloads = Path.home() / "storage" / "shared" / "Download"
    destination = final
    if downloads.is_dir():
        candidate = downloads / f"ShortAutoPro_{p.sid}.mp4"
        tmp = downloads / f".{candidate.name}.{os.getpid()}.tmp"
        try:
            source_size = final.stat().st_size
            if source_size < 500_000:
                raise RuntimeError(f"vídeo final inválido para exportação: {source_size} bytes")
            with final.open("rb") as src, tmp.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
            copied_size = tmp.stat().st_size
            if copied_size != source_size:
                raise RuntimeError(
                    f"exportação incompleta: origem={source_size} destino={copied_size}"
                )
            os.replace(tmp, candidate)
            destination = candidate
        except Exception as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            print(f"AVISO: cópia para Downloads falhou: {exc}")
    p.run("REGISTRANDO ASSUNTO", "register_topic.py")
    return destination


def run_pipeline(*, reuse_short_id: bool = False) -> int:
    source_config()
    setup_env()
    sid = allocate_id(reuse_existing=reuse_short_id)
    os.environ["SHORT_ID"] = sid
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with RunLock(sid):
        try:
            production_profiler.begin_run(sid)
        except Exception:
            pass
        p = Pipeline(sid)
        print("\n==============================================")
        print(" SHORTAUTOPRO CONSOLIDATION 3.0.3 - MAIN.PY")
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
            p.run(
                "12F - FINAL PRODUCTION HEALTH",
                "production_health.py",
                "--short-id", p.sid, "--phase", "final",
            )
            destination = export(p)
            p.run("STORAGE CLEANUP", "storage_manager.py", "cleanup", "--execute")
            p.checkpoint("pipeline", "pass", "ShortAutoPro Consolidation 3.0.3")
            p.finish("SUCCESS")
        except Exception as exc:
            p.checkpoint("pipeline", "fail", "ShortAutoPro Consolidation 3.0.3")
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
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument(
        "--reuse-short-id",
        action="store_true",
        help=argparse.SUPPRESS,
    )
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
        return run_pipeline(
            reuse_short_id=bool(getattr(args, "reuse_short_id", False))
        )

    setup_env()
    control_timeout = env_int("SAP_CONTROL_COMMAND_TIMEOUT", 7200, 300, 21600)

    def run_control(command: list[str]) -> int:
        try:
            return run_group(
                command,
                cwd=BASE,
                env=os.environ.copy(),
                check=False,
                timeout=control_timeout,
            ).returncode
        except subprocess.TimeoutExpired:
            print(f"ERRO: comando auxiliar excedeu {control_timeout}s")
            return 124

    if command_name == "resume":
        command = [sys.executable, str(BASE / "resume_short_runtime.py")]
        if args.short_id:
            command.extend(["--short-id", args.short_id])
        if args.status:
            command.append("--status")
        return run_control(command)
    if command_name == "audit":
        return run_control([sys.executable, str(BASE / "tools" / "repo_audit.py")])
    if command_name == "production":
        command = [
            sys.executable,
            str(BASE / "production_center.py"),
            *list(args.production_args or []),
        ]
        return run_control(command)
    if command_name == "storage":
        command = [sys.executable, str(BASE / "storage_manager.py"), args.storage_command]
        if args.execute:
            command.append("--execute")
        return run_control(command)
    return 2


if __name__ == "__main__":
    raise SystemExit(cli())

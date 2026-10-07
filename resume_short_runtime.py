#!/usr/bin/env python3
"""Artifact-validated resume for the single ShortAutoPro 3.0 pipeline.

Resume never switches pipelines. If the saved production does not contain the
Consolidation 3.0 planning artifacts, it restarts through main.py with the same
Short ID rather than trying to interpret legacy state.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import main as canonical
from subprocess_guard import check_output_group, run_group
from runtime_config import env_int, env_float
from media_emergency_fallback import editorial_scene_metadata
import shortautopro_evolution as evo
import hashlib

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
    expected = expected_scenes()
    valid: set[int] = set()
    try:
        for path in folder.iterdir():
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}:
                continue
            match = re.match(r"^scene_(\d+)", path.name, flags=re.IGNORECASE)
            if not match:
                continue
            number = int(match.group(1))
            if 1 <= number <= expected and nonempty(path, 1001):
                valid.add(number)
    except OSError:
        return False
    return valid == set(range(1, expected + 1))


def media_integrity_ok(sid: str) -> bool:
    """Validate current media against the visual-content integrity contract."""
    folder = BASE / "imagens" / f"short_{sid}"
    report = read_json(BASE / "roteiros" / f"media_quality_{sid}.json")
    if not media_ok(sid):
        return False

    index_path = folder / ".editorial_reuse_index.json"
    if index_path.exists() and not read_json(index_path):
        return False

    try:
        editorial = editorial_scene_metadata(folder)
    except Exception:
        return False

    neutral = {
        number
        for number, meta in editorial.items()
        if bool(meta.get("neutral_slate"))
    }
    if neutral:
        return False

    editorial_limit = env_int(
        "SAP_MEDIA_EDITORIAL_REUSE_MAX_SCENES", 3, 0, 6
    )
    if len(editorial) > editorial_limit:
        return False

    reported_neutral = (
        report.get("neutral_editorial_scenes", [])
        if isinstance(report.get("neutral_editorial_scenes"), list)
        else []
    )
    if reported_neutral:
        return False

    return True


def supervisor_ok(sid: str) -> bool:
    data = read_json(BASE / "roteiros" / f"supervisor_{sid}.json")
    return str(data.get("status", "")).upper() in {"PASS", "QUALITY_PASS", "OK"}


def pro_plan_ok(sid: str) -> bool:
    data = read_json(BASE / "roteiros" / f"pro_edit_plan_{sid}.json")
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    return (
        data.get("schema_version") == "render-plan-v2"
        and data.get("short_id") == sid
        and isinstance(scenes, list)
        and len(scenes) == expected_scenes()
    )


def pre_media_plan_ok(sid: str) -> bool:
    """Return True when Stage 1-5E artifacts are safe to resume from Stage 6."""
    script = BASE / "roteiros" / f"short_{sid}.txt"
    source = BASE / "roteiros" / f"fonte_{sid}.txt"
    topic_real = BASE / "roteiros" / f"used_topic_{sid}.txt"
    topic = BASE / "roteiros" / f"topic_{sid}.txt"
    scene_map_path = BASE / "roteiros" / f"scene_map_{sid}.json"
    truth_path = BASE / "roteiros" / f"post_script_truth_{sid}.json"
    semantic_path = BASE / "roteiros" / f"semantic_integrity_{sid}.json"
    continuity_path = BASE / "roteiros" / f"visual_continuity_{sid}.json"

    if not nonempty(script, 40) or not nonempty(source, 40):
        return False
    if not (nonempty(topic_real, 3) or nonempty(topic, 3)):
        return False

    scene_map = read_json(scene_map_path)
    scenes = scene_map.get("scenes", []) if isinstance(scene_map, dict) else []
    if not isinstance(scenes, list) or len(scenes) != expected_scenes():
        return False

    truth = read_json(truth_path)
    semantic = read_json(semantic_path)
    if str(truth.get("status", "")).upper() not in {"PASS", "WARNING"}:
        return False
    if str(semantic.get("status", "")).upper() != "PASS":
        return False

    # Continuity may legitimately be REVIEW, but its existence proves the
    # Stage 5 visual planning chain completed before Stage 6.
    if not nonempty(continuity_path, 20) or not read_json(continuity_path):
        return False
    return True


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def consolidation_plan_ok(sid: str) -> bool:
    plan = read_json(BASE / "roteiros" / f"pro_edit_plan_{sid}.json")
    scenes = plan.get("scenes", []) if isinstance(plan, dict) else []
    if (
        plan.get("schema_version") != "render-plan-v2"
        or plan.get("short_id") != sid
        or not isinstance(scenes, list)
        or len(scenes) != expected_scenes()
    ):
        return False

    manifest = read_json(BASE / "manifests" / f"media_{sid}.json")
    media_scenes = manifest.get("scenes", []) if isinstance(manifest, dict) else []
    if (
        manifest.get("schema_version") != "media-manifest-v2"
        or manifest.get("short_id") != sid
        or not str(manifest.get("engine_version") or "").startswith(("2.","3."))
        or manifest.get("immutable") is not True
        or not isinstance(media_scenes, list)
        or len(media_scenes) != expected_scenes()
    ):
        return False

    integrity = str(manifest.get("integrity_sha256") or "")
    # Canonical V2/V3 manifests must be cryptographically intact.
    # V2 remains a compatibility format; V3 is the canonical acquisition engine.
    if integrity:
        unsigned = dict(manifest)
        unsigned.pop("integrity_sha256", None)
        canonical = json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != integrity:
            return False
    elif str(manifest.get("engine_version") or "").startswith("2."):
        return False

    # A manifest without a recognized engine version is not trusted for resume.
    # It must be rebuilt by Media Acquisition V3 so resume can never skip
    # acquisition based on legacy or partially migrated state.
    if not integrity and not str(manifest.get("engine_version") or ""):
        return False

    media_root = (BASE / "imagens" / f"short_{sid}").resolve()
    seen = set()
    for index, row in enumerate(media_scenes, 1):
        if not isinstance(row, dict):
            return False
        expected_scene_id = str(
            scenes[index - 1].get("scene_id", scenes[index - 1].get("scene", index))
        ).strip()
        if (
            int(row.get("scene_number", 0) or 0) != index
            or str(row.get("scene_id", "") or "").strip() != expected_scene_id
        ):
            return False
        asset = row.get("asset")
        if not isinstance(asset, dict) or asset.get("validated") is not True:
            return False
        scene_number = int(row.get("scene_number", 0) or 0)
        if scene_number in seen or not 1 <= scene_number <= expected_scenes():
            return False
        seen.add(scene_number)
        path = Path(str(asset.get("path") or "")).expanduser().resolve()
        try:
            path.relative_to(media_root)
        except ValueError:
            return False
        if not path.is_file() or path.stat().st_size <= 1000:
            return False
        expected_sha = str(asset.get("checksum_sha256") or "")
        if not expected_sha or _sha256(path) != expected_sha:
            return False
    return seen == set(range(1, expected_scenes() + 1))


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
    manifest = read_json(BASE / "manifests" / f"{sid}.json")
    vqa = read_json(BASE / "reports" / "evolution" / f"visual_qa_{sid}.json")
    if render_valid is None:
        render_valid = render_ok(sid)

    manifest_quality = (
        manifest.get("quality", {})
        if isinstance(manifest.get("quality"), dict)
        else {}
    )
    required_visual_flags = (
        "media_gate_pass",
        "neutral_editorial_absent",
        "visual_qa_present",
        "visual_qa_not_blocked",
        "rendered_content_verified",
    )
    visual_contract = all(
        manifest_quality.get(flag) is True
        for flag in required_visual_flags
    )

    rendered = (
        vqa.get("measurements", {}).get("rendered_content", {})
        if isinstance(vqa.get("measurements"), dict)
        else {}
    )
    rendered_ok = (
        bool(rendered)
        and rendered.get("available") is True
        and rendered.get("scene_timeline_available") is True
        and not rendered.get("opening_blank")
        and not rendered.get("blank_scenes")
    )

    return (
        render_valid
        and media_integrity_ok(sid)
        and quality.get("approved") is True
        and visual_contract
        and rendered_ok
        and str(release.get("version", "")).startswith(
            "RELEASE_GATE_1.6_VISUAL_CONTENT_INTEGRITY"
        )
        and release.get("decision") in {"PUBLISH", "ACCEPTABLE"}
    )


def boundary(sid: str) -> str:
    render_valid = render_ok(sid)
    if final_ok(sid, render_valid):
        return "complete"

    # A previously "successful" Short can predate the visual-content contract.
    # If its physical media is now known to contain a neutral placeholder (or
    # exceeds the editorial reuse limit), force reacquisition from Stage 6.
    if pre_media_plan_ok(sid) and not media_integrity_ok(sid):
        return "post_scene_plan"

    # Prefer the deepest validated checkpoint. If the Short completed Stage 5E
    # but failed during Stage 6, resume media acquisition directly instead of
    # regenerating topic/script/scenes under the same Short ID.
    if not consolidation_plan_ok(sid):
        if pre_media_plan_ok(sid):
            return "post_scene_plan"
        return "full"
    if render_valid:
        return "post_render"
    if assembly_ok(sid) and audio_ok(sid) and captions_ok(sid):
        return "post_assembly"
    # Audio/captions alone cannot rebuild an assembly if its inputs were
    # deleted by storage cleanup. Validate planning inputs before skipping.
    if not (supervisor_ok(sid) and media_ok(sid) and scene_count(sid) == expected_scenes()):
        return "full"
    if captions_ok(sid) and audio_ok(sid):
        return "post_captions"
    if audio_ok(sid):
        return "post_audio"
    return "post_planning"


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
            [sys.executable, str(main_path), "run", "--reuse-short-id"],
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


def media_planning_tail(sid: str) -> None:
    """Resume through canonical Media Acquisition V3 and deterministic Render Plan V2."""
    run_python(
        sid,
        "MEDIA ACQUISITION V3 - ACQUIRE + VALIDATE + FREEZE MANIFEST",
        "media_acquisition_v3.py",
        "--short-id",
        sid,
    )
    run_python(
        sid,
        "RENDER PLAN V2 - DETERMINISTIC TIMELINE INPUT",
        "render_plan_v2.py",
        "--short-id",
        sid,
    )

def render_tail(sid: str) -> None:
    """Render only from the frozen media manifest; acquisition stays outside the renderer."""
    run_python(sid, "PRE-RENDER VALIDATION + BOUNDED AUTO-RECOVERY", "production_recovery.py", "--short-id", sid)
    run_python(sid, "RENDER PREFLIGHT CERTIFICATION", "render_preflight.py", "--short-id", sid)
    run_python(sid, "PRODUCTION HEALTH SNAPSHOT", "production_health.py", "--short-id", sid, "--phase", "pre_render")
    run_python(sid, "RENDER ENGINE V2 (REMOTION + FFMPEG + FFPROBE)", "render_engine_v2.py", "--short-id", sid)
    if not render_ok(sid):
        raise RuntimeError("Render Engine V2 terminou sem artefato técnico válido")
    run_python(sid, "FINAL AUDIO MASTER", "audio_finalizer.py")
    run_python(sid, "VISUAL QA", "visual_qa.py")


def _resume_locked(sid: str, point: str) -> int:
    """Only the process owning the production lock may modify its state."""
    try:
        order = {
            "post_scene_plan": 0,
            "post_planning": 1,
            "post_audio": 2,
            "post_captions": 3,
            "post_assembly": 4,
            "post_render": 5,
        }
        rank = order[point]

        if rank <= 0:
            print("RESUME_FROM_V2_MEDIA=YES")
            media_planning_tail(sid)

        if rank <= 1:
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
            render_tail(sid)
        else:
            run_python(sid, "FINAL AUDIO MASTER", "audio_finalizer.py")
            run_python(sid, "VISUAL QA", "visual_qa.py")

        code = final_gates(sid)
        if code == 20:
            media_planning_tail(sid)
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


def resume(sid: str) -> int:
    os.environ["SHORT_ID"] = sid
    try:
        with canonical.RunLock(sid):
            point = boundary(sid)
            print("SHORTAUTOPRO 3.0 - SAFE RESUME")
            print(f"ID: {sid}\nPipeline: PROFESSIONAL_CANONICAL\nBoundary: {point}")
            if point == "complete":
                print("Produção já aprovada pelo Release Gate.")
                return 0
            if point != "full":
                return _resume_locked(sid, point)
        # main.py acquires the same lock; release ours before launching it.
        return full_rerun(sid)
    except Exception as exc:
        # Lock contention must not mark another process's production FAILED.
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

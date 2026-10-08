#!/usr/bin/env python3
"""Artifact-level render preflight for the canonical ShortAutoPro pipeline.

This gate runs after narration/captions exist and before expensive FFmpeg
assembly. It validates the real artifacts consumed by video_professional.py
and v6_professional.py. It does not select media or alter upstream outputs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile

from subprocess_guard import run_group
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime_config import env_int
from media_emergency_fallback import editorial_scene_metadata

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
REPORT_DIR = BASE / "reports" / "production"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path.name}: JSON inválido: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: raiz JSON precisa ser objeto")
    return value


def _duration(path: Path) -> float:
    result = run_group(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"ffprobe falhou em {path.name}: {(result.stderr or '').strip()[:240]}")
    try:
        value = float((result.stdout or "").strip())
    except ValueError as exc:
        raise ValueError(f"duração inválida em {path.name}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"duração não positiva em {path.name}")
    return value


def _ass_bounds(path: Path) -> tuple[float | None, float | None, int]:
    def parse(value: str) -> float:
        h, m, rest = value.strip().split(":")
        s, cs = rest.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0

    first = None
    last = None
    previous_start = -1.0
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if not raw.startswith("Dialogue:"):
            continue
        parts = raw.split(",", 9)
        if len(parts) != 10:
            raise ValueError("linha Dialogue ASS inválida")
        start = parse(parts[1])
        end = parse(parts[2])
        if start < 0 or end <= start:
            raise ValueError("timestamp ASS inválido")
        if first is None:
            first = start
        if start + 0.05 < previous_start:
            raise ValueError("timestamps ASS fora de ordem")
        previous_start = start
        last = end if last is None else max(last, end)
        count += 1
    return first, last, count


def _probe_media(path: Path) -> None:
    result = run_group(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,width,height:format=format_name,duration,size",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"asset corrompido/ilegível {path.name}: {(result.stderr or '').strip()[:180]}")
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe JSON inválido para {path.name}") from exc
    streams = data.get("streams", []) if isinstance(data, dict) else []
    if not isinstance(streams, list) or not streams:
        raise ValueError(f"asset sem stream detectável: {path.name}")


def inspect(short_id: str) -> dict[str, Any]:
    scene_map_path = BASE / "manifests" / f"scene_map_{short_id}.json"
    media_manifest_path = BASE / "manifests" / f"media_{short_id}.json"
    pro_plan_path = BASE / "roteiros" / f"pro_edit_plan_{short_id}.json"
    audio_path = BASE / "audios" / f"short_{short_id}.mp3"
    subtitle_path = BASE / "videos" / f"short_{short_id}.ass"
    temp_dir = BASE / "temp" / short_id
    output_dir = BASE / "videos"

    checks: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []

    if not short_id.strip():
        errors.append("SHORT_ID vazio")
    checks["short_id"] = bool(short_id.strip())
    checks["ffmpeg"] = shutil.which("ffmpeg") is not None
    checks["ffprobe"] = shutil.which("ffprobe") is not None
    if not checks["ffmpeg"]:
        errors.append("ffmpeg não encontrado")
    if not checks["ffprobe"]:
        errors.append("ffprobe não encontrado")

    # SceneMap is the frozen editorial boundary. The number of scenes is
    # derived from the artifact itself so FIRST_VIDEO (2 scenes) is not forced
    # through the normal-production default (12 scenes).
    scene_map: dict[str, Any] = {}
    scenes: list[dict[str, Any]] = []
    try:
        scene_map = _read_json(scene_map_path)
        if scene_map.get("schema_version") != "SCENE_MAP_FROZEN_1.0":
            raise ValueError("scene_map: frozen schema ausente")
        if scene_map.get("short_id") != short_id:
            raise ValueError("scene_map: short_id incompatível")
        if scene_map.get("mutable_upstream_closed") is not True:
            raise ValueError("scene_map: upstream não está fechado")
        raw = scene_map.get("scenes", [])
        if not isinstance(raw, list) or not raw:
            raise ValueError("scene_map: nenhuma cena")
        for idx, item in enumerate(raw, 1):
            if not isinstance(item, dict):
                raise ValueError(f"scene_map cena {idx} não é objeto")
        scenes = raw
        checks["scene_map"] = True
    except Exception as exc:
        checks["scene_map"] = False
        errors.append(str(exc))

    expected = len(scenes)
    checks["expected_scenes"] = expected

    # MediaManifest is the only canonical media source for rendering. The
    # preflight gate never rebuilds media_by_scene from the media directory.
    media: dict[str, Any] = {}
    media_rows: list[dict[str, Any]] = []
    try:
        media = _read_json(media_manifest_path)
        if media.get("schema_version") != "media-manifest-v2":
            raise ValueError("media_manifest: schema inválido")
        if media.get("short_id") != short_id:
            raise ValueError("media_manifest: short_id incompatível")
        if int(media.get("scene_count", -1)) != expected:
            raise ValueError("media_manifest: scene_count incompatível")
        rows = media.get("scenes", [])
        if not isinstance(rows, list) or len(rows) != expected:
            raise ValueError("media_manifest: quantidade de cenas incompatível")
        media_rows = rows
        checks["media_manifest"] = True
    except Exception as exc:
        checks["media_manifest"] = False
        errors.append(str(exc))

    for idx, row in enumerate(media_rows, 1):
        try:
            if not isinstance(row, dict):
                raise ValueError(f"media_manifest cena {idx:02d} inválida")
            asset = row.get("asset")
            if not isinstance(asset, dict) or asset.get("validated") is not True:
                raise ValueError(f"media_manifest cena {idx:02d} não validada")
            path = Path(str(asset.get("path") or "")).expanduser().resolve()
            media_root = (BASE / "imagens" / f"short_{short_id}").resolve()
            path.relative_to(media_root)
            if not path.is_file() or path.stat().st_size <= 1000:
                raise ValueError(f"asset ausente/pequeno: cena {idx:02d}")
            expected_sha = str(asset.get("checksum_sha256") or "")
            if not expected_sha or sha256_file(path) != expected_sha:
                raise ValueError(f"asset checksum inválido: cena {idx:02d}")
            _probe_media(path)
        except Exception as exc:
            errors.append(str(exc))
    checks["assets"] = len(media_rows) == expected and expected > 0 and not any(
        "media_manifest cena" in e or "asset " in e for e in errors
    )

    plan: dict[str, Any] = {}
    try:
        plan = _read_json(pro_plan_path)
        if plan.get("schema_version") != "render-plan-v2":
            raise ValueError("render_plan: schema inválido")
        if plan.get("short_id") != short_id:
            raise ValueError("render_plan: short_id incompatível")
        pro_scenes = plan.get("scenes", [])
        if not isinstance(pro_scenes, list) or len(pro_scenes) != expected:
            raise ValueError("render_plan: quantidade de cenas incompatível")
        if plan.get("immutable") is not True:
            raise ValueError("render_plan: contrato não congelado")
        if not plan.get("integrity_sha256"):
            raise ValueError("render_plan: integridade ausente")
        checks["edit_plan"] = True
    except Exception as exc:
        checks["edit_plan"] = False
        errors.append(str(exc))

    audio_duration = 0.0
    try:
        if not audio_path.is_file() or audio_path.stat().st_size < 5000:
            raise ValueError(f"áudio ausente/vazio: {audio_path}")
        audio_duration = _duration(audio_path)
        checks["audio"] = True
    except Exception as exc:
        checks["audio"] = False
        errors.append(str(exc))

    try:
        if not subtitle_path.is_file() or subtitle_path.stat().st_size < 100:
            raise ValueError(f"legenda ausente/vazia: {subtitle_path}")
        first, last, count = _ass_bounds(subtitle_path)
        if count == 0:
            raise ValueError("legenda ASS sem Dialogue")
        subtitle_end = float(last or 0.0)
        if first is not None and first > 2.0:
            warnings.append(f"legenda começa tarde: {first:.2f}s")
        if audio_duration > 0 and subtitle_end > audio_duration + 0.75:
            errors.append(f"legenda ultrapassa narração: subtitle={subtitle_end:.2f}s audio={audio_duration:.2f}s")
        checks["subtitles"] = True
    except Exception as exc:
        checks["subtitles"] = False
        errors.append(str(exc))

    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = temp_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks["directories"] = True
    except OSError as exc:
        checks["directories"] = False
        errors.append(f"diretório de trabalho não gravável: {exc}")

    try:
        usage = shutil.disk_usage(BASE)
        free_mb = usage.free // (1024 * 1024)
        required_mb = max(700, int(max(audio_duration, 30.0) * 18))
        checks["disk_free_mb"] = free_mb
        checks["disk_required_mb"] = required_mb
        if free_mb < required_mb:
            errors.append(f"espaço insuficiente: {free_mb}MB livres, {required_mb}MB estimados")
        elif free_mb < required_mb * 2:
            warnings.append(f"espaço baixo: {free_mb}MB livres")
    except OSError as exc:
        warnings.append(f"não foi possível medir armazenamento: {exc}")

    status = "READY" if not errors else "FAILED"
    return {
        "short_id": short_id,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "version": "RENDER_PREFLIGHT_2.0_CANONICAL_CONTRACTS",
        "status": status,
        "expected_scenes": expected,
        "valid_assets": len(media_rows),
        "audio_duration": round(audio_duration, 3),
        "subtitle_end": round(subtitle_end if 'subtitle_end' in locals() else 0.0, 3),
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }

def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def print_report(report: dict[str, Any]) -> None:
    checks = report["checks"]
    print("==================================")
    print(" SHORTAUTOPRO RENDER PRE-FLIGHT")
    print("==================================")
    print(f"SHORT_ID ............. {'OK' if checks.get('short_id') else 'FAILED'}")
    print(f"Scene Map ............ {'OK' if checks.get('scene_map') else 'FAILED'}")
    print(f"Edit Plan ............ {'OK' if checks.get('edit_plan') else 'FAILED'}")
    print(f"Assets ............... {report['valid_assets']}/{report['expected_scenes']}")
    print(
        "Neutral Placeholders .. "
        + (
            "NONE"
            if not report.get("neutral_editorial_scenes")
            else ",".join(map(str, report.get("neutral_editorial_scenes", [])))
        )
    )
    print(f"Audio ................ {'OK' if checks.get('audio') else 'FAILED'}")
    print(f"Audio Duration ....... {report['audio_duration']:.2f}s")
    print(f"Subtitles ............ {'OK' if checks.get('subtitles') else 'FAILED'}")
    print(f"FFmpeg ............... {'OK' if checks.get('ffmpeg') else 'FAILED'}")
    print(f"ffprobe .............. {'OK' if checks.get('ffprobe') else 'FAILED'}")
    print(f"Directories .......... {'OK' if checks.get('directories') else 'FAILED'}")
    if "disk_free_mb" in checks:
        print(f"Disk Space ........... {checks['disk_free_mb']}MB free / {checks['disk_required_mb']}MB required")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    for error in report["errors"]:
        print(f"FAILED: {error}")
    print(f"RESULT: {report['status']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro render preflight")
    parser.add_argument("--short-id", default=os.getenv("SHORT_ID", ""))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = inspect(args.short_id.strip())
    if report.get("short_id"):
        _atomic_json(
            REPORT_DIR / f"render_preflight_{report['short_id']}.json",
            report,
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

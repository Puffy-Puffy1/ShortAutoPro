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
    expected = env_int("SHORT_QTD_CENAS", 12, 6, 20)
    scene_map_path = BASE / "roteiros" / f"scene_map_{short_id}.json"
    pro_plan_path = BASE / "roteiros" / f"pro_edit_plan_{short_id}.json"
    media_dir = BASE / "imagens" / f"short_{short_id}"
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

    if shutil.which("ffmpeg") is None:
        errors.append("ffmpeg não encontrado")
    if shutil.which("ffprobe") is None:
        errors.append("ffprobe não encontrado")
    checks["ffmpeg"] = shutil.which("ffmpeg") is not None
    checks["ffprobe"] = shutil.which("ffprobe") is not None

    scene_map: dict[str, Any] = {}
    try:
        scene_map = _read_json(scene_map_path)
        scenes = scene_map.get("scenes", [])
        if not isinstance(scenes, list) or len(scenes) != expected:
            raise ValueError(f"scene_map: {len(scenes) if isinstance(scenes, list) else 0}/{expected} cenas")
        numbers = []
        for idx, item in enumerate(scenes, 1):
            if not isinstance(item, dict):
                raise ValueError(f"scene_map cena {idx} não é objeto")
            try:
                number = int(item.get("scene", 0) or 0)
            except (TypeError, ValueError):
                number = 0
            numbers.append(number)
        if numbers != list(range(1, expected + 1)):
            raise ValueError("scene_map numeração não sequencial")
        checks["scene_map"] = True
    except Exception as exc:
        checks["scene_map"] = False
        errors.append(str(exc))

    try:
        plan = _read_json(pro_plan_path)
        pro_scenes = plan.get("scenes", [])
        if not isinstance(pro_scenes, list) or len(pro_scenes) != expected:
            raise ValueError(f"pro_edit_plan: {len(pro_scenes) if isinstance(pro_scenes, list) else 0}/{expected} cenas")
        checks["edit_plan"] = True
    except Exception as exc:
        checks["edit_plan"] = False
        errors.append(str(exc))

    media_by_scene: dict[int, Path] = {}
    if not media_dir.is_dir():
        errors.append(f"pasta de mídia ausente: {media_dir}")
    else:
        for path in sorted(media_dir.glob("scene_*")):
            if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS:
                continue
            match = re.match(r"^scene_(\d+)", path.name, flags=re.IGNORECASE)
            if not match:
                errors.append(f"asset com nome inválido: {path.name}")
                continue
            number = int(match.group(1))
            if number in media_by_scene:
                errors.append(f"asset duplicado para cena {number:02d}")
                continue
            if not 1 <= number <= expected:
                errors.append(f"asset fora da faixa: {path.name}")
                continue
            try:
                if path.stat().st_size <= 1000:
                    raise ValueError(f"asset vazio/pequeno: {path.name}")
                _probe_media(path)
                media_by_scene[number] = path
            except Exception as exc:
                errors.append(str(exc))
    missing = sorted(set(range(1, expected + 1)) - set(media_by_scene))
    if missing:
        errors.append("assets ausentes: " + ",".join(f"{n:02d}" for n in missing))
    checks["assets"] = len(media_by_scene) == expected

    audio_duration = 0.0
    try:
        if not audio_path.is_file() or audio_path.stat().st_size < 5000:
            raise ValueError(f"áudio ausente/vazio: {audio_path}")
        audio_duration = _duration(audio_path)
        checks["audio"] = True
    except Exception as exc:
        checks["audio"] = False
        errors.append(str(exc))

    subtitle_end = 0.0
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
            errors.append(
                f"legenda ultrapassa narração: subtitle={subtitle_end:.2f}s audio={audio_duration:.2f}s"
            )
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
        # Conservative floor plus a duration-sensitive allowance.
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
        "version": "RENDER_PREFLIGHT_1.0",
        "status": status,
        "expected_scenes": expected,
        "valid_assets": len(media_by_scene),
        "audio_duration": round(audio_duration, 3),
        "subtitle_end": round(subtitle_end, 3),
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }


def print_report(report: dict[str, Any]) -> None:
    checks = report["checks"]
    print("==================================")
    print(" SHORTAUTOPRO RENDER PRE-FLIGHT")
    print("==================================")
    print(f"SHORT_ID ............. {'OK' if checks.get('short_id') else 'FAILED'}")
    print(f"Scene Map ............ {'OK' if checks.get('scene_map') else 'FAILED'}")
    print(f"Edit Plan ............ {'OK' if checks.get('edit_plan') else 'FAILED'}")
    print(f"Assets ............... {report['valid_assets']}/{report['expected_scenes']}")
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

#!/usr/bin/env python3

import glob
import json
import math
import os
import re
import subprocess
from datetime import date
from pathlib import Path


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except (TypeError, ValueError):
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

SUPERVISOR = BASE / "roteiros" / f"supervisor_{SHORT_ID}.json"
VIDEO = BASE / "videos" / f"short_v6_{SHORT_ID}.mp4"
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
VALID_SUPERVISOR = {"EXCELLENT", "PASS", "WARNING"}


def safe_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def safe_float(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def parse_fps(value):
    raw = str(value or "0/1")
    try:
        if "/" in raw:
            num, den = raw.split("/", 1)
            den_f = float(den)
            result = float(num) / den_f if den_f else 0.0
        else:
            result = float(raw)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def ffprobe_json(path: Path):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=45,
        )
        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffprobe excedeu 45 segundos") from exc
    except Exception as exc:
        raise RuntimeError(f"ffprobe falhou: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("ffprobe retornou JSON inválido")
    return data


def media_inventory(media_dir: Path):
    if not media_dir.is_dir():
        return []
    return sorted(
        p for p in media_dir.glob("scene_*")
        if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
    )


def evaluate(video_path, media_dir, scene_map_path, supervisor_path, expected, probe_data=None):
    video_path = Path(video_path)
    media_dir = Path(media_dir)
    scene_map_path = Path(scene_map_path)
    supervisor_path = Path(supervisor_path)
    errors = []
    warnings = []

    if not video_path.is_file():
        errors.append("Vídeo final V6 não encontrado.")
        info = {}
    else:
        try:
            if video_path.stat().st_size < 500_000:
                errors.append("Arquivo final pequeno demais.")
        except OSError as exc:
            errors.append(f"Não foi possível medir o vídeo: {exc}")
        if probe_data is None:
            try:
                info = ffprobe_json(video_path)
            except RuntimeError as exc:
                errors.append(str(exc))
                info = {}
        else:
            info = probe_data if isinstance(probe_data, dict) else {}

    streams = info.get("streams", []) if isinstance(info, dict) else []
    fmt = info.get("format", {}) if isinstance(info, dict) else {}
    if not isinstance(streams, list):
        streams = []
    if not isinstance(fmt, dict):
        fmt = {}

    video_streams = [
        item for item in streams
        if isinstance(item, dict) and item.get("codec_type") == "video"
    ]
    audio_streams = [
        item for item in streams
        if isinstance(item, dict) and item.get("codec_type") == "audio"
    ]

    width = height = 0
    fps = 0.0
    codec = ""
    if not video_streams:
        errors.append("Nenhuma faixa de vídeo encontrada.")
    else:
        stream = video_streams[0]
        width = safe_int(stream.get("width"))
        height = safe_int(stream.get("height"))
        codec = str(stream.get("codec_name", "") or "")
        fps = parse_fps(stream.get("avg_frame_rate"))
        if width != 1080:
            errors.append(f"Largura incorreta: {width}")
        if height != 1920:
            errors.append(f"Altura incorreta: {height}")
        if codec != "h264":
            warnings.append(f"Codec inesperado: {codec or '?'}")
        if not 29.0 <= fps <= 31.0:
            errors.append(f"FPS fora do esperado: {fps:.2f}")

    if not audio_streams:
        errors.append("Nenhuma faixa de áudio encontrada.")
    else:
        audio_codec = str(audio_streams[0].get("codec_name", "") or "")
        if audio_codec != "aac":
            warnings.append(f"Codec de áudio: {audio_codec or '?'}")

    duration = safe_float(fmt.get("duration"))
    if duration < 15:
        errors.append(f"Vídeo curto demais: {duration:.2f}s")
    elif duration > 180:
        errors.append(f"Vídeo longo demais para Short: {duration:.2f}s")
    elif duration > 60:
        warnings.append(f"Vídeo acima de 60s: {duration:.2f}s")

    media = media_inventory(media_dir)
    if len(media) != expected:
        errors.append(f"Cenas físicas: {len(media)}/{expected}")

    numbers = []
    for path in media:
        match = re.fullmatch(r"scene_(\d+)(?:_[A-Za-z0-9-]+)?", path.stem, flags=re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
        else:
            errors.append(f"Nome de mídia inválido: {path.name}")

    expected_numbers = list(range(1, expected + 1))
    if sorted(numbers) != expected_numbers:
        missing = sorted(set(expected_numbers) - set(numbers))
        extras = sorted(set(numbers) - set(expected_numbers))
        duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
        if missing:
            errors.append("Cenas ausentes: " + ", ".join(f"{n:02d}" for n in missing))
        if extras:
            errors.append("Cenas fora da faixa: " + ", ".join(f"{n:02d}" for n in extras))
        if duplicates:
            errors.append("Cenas duplicadas: " + ", ".join(f"{n:02d}" for n in duplicates))

    scene_map = safe_json(scene_map_path)
    if scene_map is None:
        errors.append("scene_map ausente ou inválido.")
    else:
        scenes = scene_map.get("scenes")
        if not isinstance(scenes, list):
            errors.append("scene_map.scenes não é lista.")
        else:
            if len(scenes) != expected:
                errors.append(f"Scene map: {len(scenes)}/{expected}")
            map_numbers = []
            for index, scene in enumerate(scenes, start=1):
                if not isinstance(scene, dict):
                    errors.append(f"Scene map cena {index} inválida.")
                    continue
                map_numbers.append(safe_int(scene.get("scene")))
            if map_numbers != expected_numbers:
                errors.append("Numeração do scene_map não é sequencial.")

    supervisor = safe_json(supervisor_path)
    if supervisor is None:
        errors.append("Relatório do Production Supervisor ausente ou inválido.")
    else:
        status = str(supervisor.get("status", "") or "").upper()
        if status == "BLOCK":
            errors.append("Production Supervisor marcou BLOCK.")
        elif status not in VALID_SUPERVISOR:
            errors.append(f"Status do Production Supervisor inválido: {status or 'AUSENTE'}")

    return {
        "errors": errors,
        "warnings": warnings,
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "media_count": len(media),
    }


def main():
    result = evaluate(
        VIDEO,
        MEDIA_DIR,
        SCENE_MAP,
        SUPERVISOR,
        QTD_CENAS,
    )

    print()
    print("================================")
    print("SHORTAUTO PRO - QUALITY GATE 5.2")
    print("================================")
    print()
    print(f"Arquivo: {VIDEO}")
    print(f"Duração: {result['duration']:.2f}s")
    print(f"Resolução: {result['width']}x{result['height']}")
    print(f"FPS: {result['fps']:.2f}")
    print(f"Cenas físicas: {result['media_count']}/{QTD_CENAS}")
    print()

    if result["warnings"]:
        print("AVISOS:")
        for warning in result["warnings"]:
            print(f"- {warning}")
        print()

    if result["errors"]:
        print("QUALITY FAIL")
        for error in result["errors"]:
            print(f"- {error}")
        print()
        return 1

    print("QUALITY PASS")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

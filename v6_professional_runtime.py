#!/usr/bin/env python3
"""Supervise the professional V6 renderer and validate its final contract."""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
TARGET = BASE / "v6_professional.py"
OUTPUT = BASE / "videos" / f"short_v6_{SHORT_ID}.mp4"


def safe_float(value):
    try:
        result = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return result if math.isfinite(result) else 0.0


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


def validate_probe(data):
    errors = []
    if not isinstance(data, dict):
        return ["ffprobe_json_invalid"]
    streams = data.get("streams", []) if isinstance(data.get("streams"), list) else []
    fmt = data.get("format", {}) if isinstance(data.get("format"), dict) else {}
    video = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "video"), None)
    audio = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "audio"), None)
    if video is None:
        errors.append("video_stream_missing")
    else:
        try:
            width = int(video.get("width", 0) or 0)
            height = int(video.get("height", 0) or 0)
        except (TypeError, ValueError, OverflowError):
            width = height = 0
        fps = parse_fps(video.get("avg_frame_rate"))
        codec = str(video.get("codec_name", "") or "").strip().lower()
        if (width, height) != (1080, 1920):
            errors.append(f"resolution_invalid={width}x{height}")
        if not 29.0 <= fps <= 31.0:
            errors.append(f"fps_invalid={fps:.3f}")
        if codec != "h264":
            errors.append(f"video_codec_invalid={codec or 'missing'}")
    if audio is None:
        errors.append("audio_stream_missing")
    else:
        codec = str(audio.get("codec_name", "") or "").strip().lower()
        if codec != "aac":
            errors.append(f"audio_codec_invalid={codec or 'missing'}")
    duration = safe_float(fmt.get("duration"))
    if not 15.0 <= duration <= 180.0:
        errors.append(f"duration_invalid={duration:.3f}")
    return errors


def probe(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ], capture_output=True, text=True, check=True, timeout=45)
    return json.loads(result.stdout)


def remove_output():
    try:
        OUTPUT.unlink()
    except OSError:
        pass


def render_timeout():
    try:
        value = int(os.getenv("SHORT_RENDER_TIMEOUT", "1200"))
    except (TypeError, ValueError):
        value = 1200
    return max(180, min(value, 2400))


def terminate(process):
    if process.poll() is not None:
        return
    try:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
        return
    except Exception:
        pass
    try:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except Exception:
        pass


def main() -> int:
    if not SHORT_ID:
        print("ERRO V6 PROFESSIONAL RUNTIME: SHORT_ID vazio")
        return 1
    if not TARGET.is_file():
        print(f"ERRO V6 PROFESSIONAL RUNTIME: arquivo ausente: {TARGET}")
        return 1
    remove_output()
    timeout = render_timeout()
    print(f"V6_PROFESSIONAL_RUNTIME=ACTIVE timeout={timeout}s")
    process = subprocess.Popen(
        [sys.executable, str(TARGET)], cwd=str(BASE), stdin=subprocess.DEVNULL,
        start_new_session=(os.name != "nt"),
    )
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate(process)
        remove_output()
        print(f"ERRO V6 PROFESSIONAL RUNTIME: render excedeu {timeout}s")
        return 1
    except Exception as exc:
        terminate(process)
        remove_output()
        print(f"ERRO V6 PROFESSIONAL RUNTIME: {exc}")
        return 1
    if returncode != 0:
        remove_output()
        print(f"ERRO V6 PROFESSIONAL RUNTIME: renderer retornou {returncode}")
        return returncode or 1
    try:
        if not OUTPUT.is_file() or OUTPUT.stat().st_size < 500_000:
            raise RuntimeError("vídeo final ausente ou pequeno demais")
        errors = validate_probe(probe(OUTPUT))
        if errors:
            raise RuntimeError("; ".join(errors))
    except Exception as exc:
        remove_output()
        print(f"ERRO V6 PROFESSIONAL RUNTIME: saída inválida: {exc}")
        return 1
    print(f"V6_PROFESSIONAL_RUNTIME=PASS output={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

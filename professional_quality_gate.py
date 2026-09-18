#!/usr/bin/env python3
"""Professional edit quality gate for ShortAutoPro.

The first rollout is observational unless SAP_PROFESSIONAL_ENFORCE=1. Existing
legacy/factual/publish gates remain authoritative while this score is calibrated
with real Termux renders.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", "").strip()
PLAN = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"
RUNTIME = BASE / "roteiros" / f"pro_edit_runtime_{SHORT_ID}.json"
CAPTION = BASE / "roteiros" / f"pro_caption_{SHORT_ID}.json"
MEDIA = BASE / "roteiros" / f"media_quality_{SHORT_ID}.json"
VIDEO = BASE / "videos" / f"short_v6_{SHORT_ID}.mp4"
LEGACY = BASE / "manifests" / f"{SHORT_ID}_quality.json"
PRODUCTION_MANIFEST = BASE / "manifests" / f"{SHORT_ID}.json"
AUDIO_REPORT = BASE / "reports" / "evolution" / f"final_audio_{SHORT_ID}.json"
OUTPUT = BASE / "manifests" / f"{SHORT_ID}_professional.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    except Exception:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def parse_fps(value: Any) -> float:
    raw = str(value or "0/1")
    try:
        if "/" in raw:
            a, b = raw.split("/", 1)
            den = float(b)
            return float(a) / den if den else 0.0
        return float(raw)
    except Exception:
        return 0.0


def media_score(report: dict[str, Any]) -> tuple[float, list[str]]:
    if not report:
        return 75.0, ["media_report_missing"]
    critical = report.get("critical", []) if isinstance(report.get("critical"), list) else []
    warnings = report.get("warnings", []) if isinstance(report.get("warnings"), list) else []
    if critical or str(report.get("status", "")).upper() == "BLOCK":
        return 0.0, ["media_master_blocked"] + [str(x) for x in critical]

    score = 100.0
    notes: list[str] = []
    for warning in warnings:
        text = str(warning)
        if text.startswith("low_resolution:"):
            score -= 4.0
            notes.append(text)
        elif text.startswith("near_duplicate:"):
            score -= 5.0
            notes.append(text)
        elif text.startswith("low_motion_mix="):
            score -= 4.0
            notes.append(text)
        elif text.startswith("short_video:"):
            score -= 2.0
            notes.append(text)
    return max(0.0, score), notes


def cached_technical_score() -> tuple[float, list[str], dict[str, Any]] | None:
    manifest = read_json(PRODUCTION_MANIFEST)
    if not manifest:
        return None
    try:
        if not VIDEO.is_file() or not PRODUCTION_MANIFEST.is_file():
            return None
        if VIDEO.stat().st_mtime > PRODUCTION_MANIFEST.stat().st_mtime:
            return None
    except OSError:
        return None

    video = manifest.get("video", {}) if isinstance(manifest.get("video"), dict) else {}
    quality = manifest.get("quality", {}) if isinstance(manifest.get("quality"), dict) else {}
    if not video or not quality:
        return None

    width = int(video.get("width", 0) or 0)
    height = int(video.get("height", 0) or 0)
    fps = safe_float(video.get("fps"), 0.0)
    video_codec = str(video.get("video_codec", "") or "").strip().lower()
    audio_codec = str(video.get("audio_codec", "") or "").strip().lower()

    errors: list[str] = []
    score = 100.0
    if video_codec != "h264":
        errors.append("video_codec")
        score -= 35
    if (width, height) != (1080, 1920):
        errors.append(f"resolution={width}x{height}")
        score -= 35
    if not 29 <= fps <= 31:
        errors.append(f"fps={fps:.2f}")
        score -= 15
    if audio_codec != "aac":
        errors.append("audio_codec")
        score -= 35

    return max(0.0, score), errors, {
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "cached": True,
        "source": str(PRODUCTION_MANIFEST),
    }


def technical_score() -> tuple[float, list[str], dict[str, Any]]:
    if not VIDEO.is_file():
        return 0.0, ["video_missing"], {}
    try:
        proc = subprocess.run([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(VIDEO),
        ], capture_output=True, text=True, check=True, timeout=45)
        data = json.loads(proc.stdout)
    except Exception as exc:
        return 0.0, [f"ffprobe_failed:{exc}"], {}
    streams = data.get("streams", []) if isinstance(data, dict) else []
    video = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "video"), {})
    audio = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "audio"), {})
    errors: list[str] = []
    score = 100.0
    width = int(video.get("width", 0) or 0) if video else 0
    height = int(video.get("height", 0) or 0) if video else 0
    fps = parse_fps(video.get("avg_frame_rate")) if video else 0.0
    if video.get("codec_name") != "h264":
        errors.append("video_codec")
        score -= 35
    if (width, height) != (1080, 1920):
        errors.append(f"resolution={width}x{height}")
        score -= 35
    if not 29 <= fps <= 31:
        errors.append(f"fps={fps:.2f}")
        score -= 15
    if audio.get("codec_name") != "aac":
        errors.append("audio_codec")
        score -= 35
    return max(0.0, score), errors, {"width": width, "height": height, "fps": round(fps, 3)}


def measure_loudness(target_lufs: float, target_tp: float) -> dict[str, Any]:
    if not VIDEO.is_file():
        return {"available": False}
    try:
        proc = subprocess.run([
            "ffmpeg", "-hide_banner", "-nostdin", "-i", str(VIDEO),
            "-vn", "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=7:print_format=json",
            "-f", "null", "-",
        ], capture_output=True, text=True, timeout=180)
        text = proc.stderr or ""
        blocks = re.findall(r"\{\s*\"input_i\".*?\}", text, flags=re.S)
        if not blocks:
            return {"available": False, "returncode": proc.returncode}
        data = json.loads(blocks[-1])
        return {
            "available": True,
            "input_i": safe_float(data.get("input_i"), 0.0),
            "input_tp": safe_float(data.get("input_tp"), 0.0),
            "input_lra": safe_float(data.get("input_lra"), 0.0),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def cached_loudness(target_lufs: float, target_tp: float) -> dict[str, Any]:
    report = read_json(AUDIO_REPORT)
    if not report or str(report.get("status", "")).upper() != "PASS":
        return {}
    try:
        if not VIDEO.is_file() or not AUDIO_REPORT.is_file():
            return {}
        if VIDEO.stat().st_mtime > AUDIO_REPORT.stat().st_mtime:
            return {}
    except OSError:
        return {}

    target = report.get("target", {}) if isinstance(report.get("target"), dict) else {}
    after = report.get("after", {}) if isinstance(report.get("after"), dict) else {}
    report_lufs = safe_float(target.get("lufs"), 999.0)
    report_tp = safe_float(target.get("true_peak_db"), 999.0)
    if abs(report_lufs - target_lufs) > 0.01 or abs(report_tp - target_tp) > 0.01:
        return {}

    if not after:
        return {}

    return {
        "available": True,
        "input_i": safe_float(after.get("lufs"), 0.0),
        "input_tp": safe_float(after.get("true_peak_db"), 0.0),
        "input_lra": safe_float(after.get("lra"), 0.0),
        "cached": True,
        "source": str(AUDIO_REPORT),
    }


def main() -> int:
    if not SHORT_ID:
        print("ERRO PROFESSIONAL QUALITY: SHORT_ID vazio")
        return 1
    plan = read_json(PLAN)
    runtime = read_json(RUNTIME)
    caption = read_json(CAPTION)
    media = read_json(MEDIA)
    legacy = read_json(LEGACY)
    critical: list[str] = []

    plan_score = safe_float(plan.get("professional_score"), 0.0)
    runtime_score = 100.0 if runtime.get("status") == "PASS" else 0.0
    caption_score = safe_float(caption.get("score"), 75.0 if not caption else 0.0)
    media_quality_score, media_notes = media_score(media)
    if "media_master_blocked" in media_notes:
        critical.append("media_master_blocked")

    cached_tech = cached_technical_score()
    if cached_tech is not None:
        print("PRO_QUALITY_TECHNICAL=MANIFEST_CACHE_HIT")
        tech_score, tech_errors, tech_details = cached_tech
    else:
        print("PRO_QUALITY_TECHNICAL=FFPROBE")
        tech_score, tech_errors, tech_details = technical_score()
    if tech_errors:
        critical.extend(x for x in tech_errors if x in {"video_missing", "video_codec", "audio_codec"} or x.startswith("resolution="))

    audio_policy = plan.get("audio", {}) if isinstance(plan.get("audio"), dict) else {}
    target_lufs = safe_float(audio_policy.get("target_lufs"), -14.0)
    target_tp = safe_float(audio_policy.get("true_peak_db"), -1.5)
    loudness = cached_loudness(target_lufs, target_tp)
    if loudness:
        print("PRO_QUALITY_AUDIO_MEASURE=CACHE_HIT")
    else:
        print("PRO_QUALITY_AUDIO_MEASURE=FFMPEG")
        loudness = measure_loudness(target_lufs, target_tp)
    if loudness.get("available"):
        lufs_error = abs(safe_float(loudness.get("input_i")) - target_lufs)
        tp = safe_float(loudness.get("input_tp"))
        loudness_score = max(0.0, 100.0 - lufs_error * 12.0)
        if tp > target_tp + 0.5:
            loudness_score -= min(30.0, (tp - target_tp) * 12.0)
        loudness_score = max(0.0, loudness_score)
    else:
        loudness_score = 80.0

    legacy_editorial = safe_float(legacy.get("total_score"), 80.0 if legacy else 0.0)
    components = {
        "edit_plan": round(plan_score, 1),
        "media": round(media_quality_score, 1),
        "captions": round(max(0.0, min(100.0, caption_score)), 1),
        "assembly": round(runtime_score, 1),
        "technical": round(tech_score, 1),
        "audio_master": round(loudness_score, 1),
        "editorial": round(max(0.0, min(100.0, legacy_editorial)), 1),
    }
    weights = {
        "edit_plan": 0.20,
        "media": 0.10,
        "captions": 0.10,
        "assembly": 0.10,
        "technical": 0.20,
        "audio_master": 0.10,
        "editorial": 0.20,
    }
    total = round(sum(components[key] * weights[key] for key in weights), 1)
    threshold = safe_float(os.getenv("SAP_PROFESSIONAL_MIN_SCORE", "88"), 88.0)
    status = "PASS" if total >= threshold and not critical else ("REVIEW" if not critical else "BLOCK")
    remediation: list[str] = []
    if components["edit_plan"] < 88:
        remediation.append("melhorar variedade de enquadramento, pacing e transições")
    if components["media"] < 88:
        remediation.append("substituir mídia fraca/repetida quando não for evidência documental rara")
    if components["captions"] < 88:
        remediation.append("recalibrar densidade/quebra/área segura das legendas")
    if components["audio_master"] < 88:
        remediation.append("recalibrar loudness/true peak")
    if components["editorial"] < 88:
        remediation.append("refinar hook, progressão narrativa e payoff")

    result = {
        "short_id": SHORT_ID,
        "version": "PRO_QUALITY_1.1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "profile": plan.get("profile", os.getenv("SAP_CHANNEL_PROFILE", "default")),
        "score": total,
        "threshold": threshold,
        "status": status,
        "components": components,
        "weights": weights,
        "critical": critical,
        "remediation": remediation,
        "media_notes": media_notes,
        "technical": tech_details,
        "loudness": loudness,
        "caption_report": caption,
        "audio_policy": {"target_lufs": target_lufs, "true_peak_db": target_tp},
        "enforced": os.getenv("SAP_PROFESSIONAL_ENFORCE", "0") == "1",
    }
    atomic_json(OUTPUT, result)

    print("\n================================")
    print("PROFESSIONAL QUALITY GATE 1.1")
    print("================================")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["enforced"] and status != "PASS":
        print("PROFESSIONAL QUALITY GATE: BLOCK")
        return 1
    print("PROFESSIONAL QUALITY GATE: " + ("PASS" if status == "PASS" else "OBSERVATIONAL_" + status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

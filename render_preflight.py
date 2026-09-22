#!/usr/bin/env python3
"""Production-specific pre-render contract for ShortAutoPro.

This is intentionally different from the repository/environment preflight:
it validates the concrete SHORT_ID artifacts immediately before expensive
encoding. It is fail-closed for structural/render blockers and warning-only for
quality states that can still be reviewed by the canonical release gates.
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
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
def expected_scenes() -> int:
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12") or 12)
    except (TypeError, ValueError):
        value = 12
    return max(6, min(20, value))


EXPECTED = expected_scenes()

R = BASE / "roteiros"
MEDIA_DIR = BASE / "imagens" / f"short_{SID}"
AUDIO = BASE / "audios" / f"short_{SID}.mp3"
ASS = BASE / "videos" / f"short_{SID}.ass"
SCENE_MAP = R / f"scene_map_{SID}.json"
PRO_PLAN = R / f"pro_edit_plan_{SID}.json"
MEDIA_QUALITY = R / f"media_quality_{SID}.json"
VISUAL_SCORE = R / f"visual_score_{SID}.json"
CONTINUITY = R / f"visual_continuity_{SID}.json"
CAPTION_LAYOUT = R / f"caption_layout_{SID}.json"
OUT = BASE / "reports" / "preflight" / f"render_preflight_{SID}.json"
POST_OUT = BASE / "reports" / "preflight" / f"post_render_{SID}.json"
FINAL_VIDEO = BASE / "videos" / f"short_v6_{SID}.mp4"
FINAL_AUDIO_REPORT = BASE / "reports" / "evolution" / f"final_audio_{SID}.json"

MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def ffprobe(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_streams", "-show_format",
                "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return {}
    if proc.returncode != 0:
        return {}
    try:
        data = json.loads(proc.stdout)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def duration(info: dict[str, Any]) -> float:
    try:
        value = float((info.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError, AttributeError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def parse_fps(value: Any) -> float:
    raw = str(value or "0/1")
    try:
        if "/" in raw:
            numerator, denominator = raw.split("/", 1)
            den = float(denominator)
            result = float(numerator) / den if den else 0.0
        else:
            result = float(raw)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def scene_number(item: dict[str, Any], fallback: int) -> int:
    for key in ("scene", "scene_id", "id", "number"):
        try:
            value = int(item.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return fallback


def ass_seconds(value: str) -> float | None:
    try:
        hour, minute, rest = value.split(":")
        second, centisecond = rest.split(".")
        return int(hour) * 3600 + int(minute) * 60 + int(second) + int(centisecond) / 100.0
    except Exception:
        return None


def primary_media() -> tuple[dict[int, Path], set[int]]:
    result: dict[int, Path] = {}
    duplicates: set[int] = set()
    if not MEDIA_DIR.is_dir():
        return result, duplicates
    for path in MEDIA_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS:
            continue
        match = re.fullmatch(r"scene_(\d+)", path.stem, flags=re.I)
        if not match:
            continue
        number = int(match.group(1))
        if number in result:
            duplicates.add(number)
        else:
            result[number] = path
    return result, duplicates


def writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".sap_write_test_", dir=str(path))
        os.close(fd)
        os.unlink(name)
        return True
    except Exception:
        return False


def pre_render_main() -> int:
    blockers: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if not SID:
        blockers.append("short_id_empty")

    for binary in ("ffmpeg", "ffprobe"):
        ok = bool(shutil.which(binary))
        checks[binary] = ok
        if not ok:
            blockers.append(f"dependency_missing:{binary}")

    scene_map = load(SCENE_MAP)
    scenes = scene_map.get("scenes", []) if isinstance(scene_map.get("scenes"), list) else []
    scene_ids = [
        scene_number(item, index)
        for index, item in enumerate(scenes, 1)
        if isinstance(item, dict)
    ]
    checks["scene_map"] = {
        "count": len(scenes),
        "ids": scene_ids,
    }
    if len(scenes) != EXPECTED:
        blockers.append(f"scene_count:{len(scenes)}/{EXPECTED}")
    if scene_ids != list(range(1, EXPECTED + 1)):
        blockers.append("scene_ids_not_sequential")

    pro = load(PRO_PLAN)
    pro_scenes = pro.get("scenes", []) if isinstance(pro.get("scenes"), list) else []
    checks["professional_edit_plan"] = len(pro_scenes)
    if len(pro_scenes) != EXPECTED:
        blockers.append(f"professional_edit_plan_count:{len(pro_scenes)}/{EXPECTED}")

    media, duplicate_media = primary_media()
    checks["media"] = {
        "count": len(media),
        "scenes": sorted(media),
        "duplicates": sorted(duplicate_media),
    }
    for number in range(1, EXPECTED + 1):
        path = media.get(number)
        if path is None:
            blockers.append(f"asset_missing:scene_{number:02d}")
            continue
        if number in duplicate_media:
            blockers.append(f"asset_ambiguous:scene_{number:02d}")
            continue
        try:
            if path.stat().st_size <= 1000:
                blockers.append(f"asset_too_small:scene_{number:02d}")
                continue
        except OSError:
            blockers.append(f"asset_unreadable:scene_{number:02d}")
            continue
        info = ffprobe(path)
        streams = info.get("streams", []) if isinstance(info.get("streams"), list) else []
        if not any(isinstance(row, dict) and row.get("codec_type") == "video" for row in streams):
            blockers.append(f"asset_probe_failed:scene_{number:02d}")

    media_gate = load(MEDIA_QUALITY)
    checks["media_gate"] = media_gate.get("status")
    if str(media_gate.get("status", "")).upper() != "PASS":
        blockers.append("media_master_gate_not_pass")

    vscore = load(VISUAL_SCORE)
    checks["visual_score"] = {
        "status": vscore.get("status"),
        "score": vscore.get("visual_score"),
        "weak_scenes": vscore.get("weak_scenes", []),
    }
    if not vscore:
        blockers.append("visual_score_missing")
    elif str(vscore.get("status", "")).upper() == "REVIEW":
        warnings.append("visual_score_review")

    continuity = load(CONTINUITY)
    checks["continuity"] = {
        "mode": continuity.get("mode"),
        "status": continuity.get("status"),
        "score": continuity.get("visual_continuity_score"),
        "repair_scenes": continuity.get("repair_scenes", []),
    }
    if continuity.get("mode") != "SELECTED_MEDIA":
        blockers.append("selected_media_continuity_missing")
    continuity_status = str(continuity.get("status", "")).upper()
    if continuity_status == "FAIL":
        blockers.append("visual_continuity_fail")
    elif continuity_status == "REVIEW":
        warnings.append("visual_continuity_review")

    audio_info = ffprobe(AUDIO) if AUDIO.is_file() else {}
    audio_streams = audio_info.get("streams", []) if isinstance(audio_info.get("streams"), list) else []
    audio_duration = duration(audio_info)
    audio_ok = (
        AUDIO.is_file()
        and AUDIO.stat().st_size > 1000
        and any(
            isinstance(row, dict) and row.get("codec_type") == "audio"
            for row in audio_streams
        )
        and audio_duration > 0
    )
    checks["audio"] = {
        "ok": audio_ok,
        "duration": round(audio_duration, 3),
    }
    if not audio_ok:
        blockers.append("audio_invalid")

    dialogue_count = 0
    subtitle_last = 0.0
    subtitle_invalid = 0
    if ASS.is_file():
        try:
            for line in ASS.read_text(encoding="utf-8", errors="strict").splitlines():
                if not line.startswith("Dialogue:"):
                    continue
                parts = line.split(",", 9)
                if len(parts) != 10:
                    subtitle_invalid += 1
                    continue
                start = ass_seconds(parts[1].strip())
                end = ass_seconds(parts[2].strip())
                if start is None or end is None or end <= start:
                    subtitle_invalid += 1
                    continue
                dialogue_count += 1
                subtitle_last = max(subtitle_last, end)
        except Exception:
            subtitle_invalid += 1
    checks["subtitles"] = {
        "dialogues": dialogue_count,
        "invalid": subtitle_invalid,
        "last_end": round(subtitle_last, 3),
    }
    if not ASS.is_file() or dialogue_count == 0 or subtitle_invalid:
        blockers.append("subtitles_invalid")
    elif audio_duration > 0 and subtitle_last > audio_duration + 0.75:
        blockers.append(
            f"subtitles_exceed_audio:{subtitle_last:.2f}>{audio_duration:.2f}"
        )

    caption = load(CAPTION_LAYOUT)
    checks["caption_layout"] = caption.get("status")
    caption_status = str(caption.get("status", "")).upper()
    if not caption:
        blockers.append("caption_layout_missing")
    elif caption_status == "BLOCK":
        blockers.append("caption_layout_block")
    elif caption_status == "REVIEW":
        warnings.append("caption_layout_review")

    temp_dir = BASE / "temp" / SID
    video_dir = BASE / "videos"
    temp_ok = writable_directory(temp_dir)
    output_ok = writable_directory(video_dir)
    checks["directories"] = {"temp": temp_ok, "output": output_ok}
    if not temp_ok:
        blockers.append("temp_directory_not_writable")
    if not output_ok:
        blockers.append("output_directory_not_writable")

    try:
        media_bytes = sum(
            path.stat().st_size
            for path in media.values()
            if path.is_file()
        )
    except OSError:
        media_bytes = 0
    try:
        free_bytes = shutil.disk_usage(BASE).free
    except OSError:
        free_bytes = 0

    minimum_mb = max(256, int(os.getenv("SAP_RENDER_MIN_FREE_MB", "384") or 384))
    estimated_work_bytes = max(
        minimum_mb * 1024 * 1024,
        media_bytes * 4 + max(0, int(AUDIO.stat().st_size) if AUDIO.is_file() else 0) * 3,
    )
    checks["disk"] = {
        "free_mb": round(free_bytes / 1024 / 1024, 1),
        "required_mb": round(estimated_work_bytes / 1024 / 1024, 1),
    }
    if free_bytes <= 0 or free_bytes < estimated_work_bytes:
        blockers.append("insufficient_disk_space")
    elif free_bytes < estimated_work_bytes * 1.5:
        warnings.append("disk_space_low_margin")

    status = "READY" if not blockers else "BLOCK"
    payload = {
        "short_id": SID,
        "version": "RENDER_PREFLIGHT_1.0",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "expected_scenes": EXPECTED,
        "checks": checks,
        "warnings": warnings,
        "blockers": blockers,
    }
    atomic(OUT, payload)

    print()
    print("================================")
    print("STAGE 6 / RENDER PRE-FLIGHT CHECK")
    print("================================")
    print(f"Scene map ............... {'OK' if len(scenes) == EXPECTED else 'FAIL'}")
    print(f"Images/videos ........... {len(media)}/{EXPECTED}")
    print(f"Media gate .............. {checks['media_gate'] or 'MISSING'}")
    print(f"Selected continuity ..... {checks['continuity']['status'] or 'MISSING'}")
    print(f"Audio ................... {'OK' if audio_ok else 'FAIL'}")
    print(f"Subtitles ............... {'OK' if dialogue_count and not subtitle_invalid else 'FAIL'}")
    print(f"Disk free ............... {checks['disk']['free_mb']} MB")
    print(f"Temporary directory ..... {'OK' if temp_ok else 'FAIL'}")
    print(f"Output directory ........ {'OK' if output_ok else 'FAIL'}")
    if warnings:
        print("Warnings ................ " + ",".join(warnings))
    if blockers:
        print("Blockers ................ " + ",".join(blockers))
    print()
    print(f"PRE-FLIGHT: {status}")
    return 0 if status == "READY" else 1


def post_render_main() -> int:
    blockers: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    info = ffprobe(FINAL_VIDEO) if FINAL_VIDEO.is_file() else {}
    streams = info.get("streams", []) if isinstance(info.get("streams"), list) else []
    video_stream = next(
        (row for row in streams if isinstance(row, dict) and row.get("codec_type") == "video"),
        {},
    )
    audio_stream = next(
        (row for row in streams if isinstance(row, dict) and row.get("codec_type") == "audio"),
        {},
    )
    video_duration = duration(info)
    narration_info = ffprobe(AUDIO) if AUDIO.is_file() else {}
    narration_duration = duration(narration_info)
    fps = parse_fps(video_stream.get("avg_frame_rate"))
    try:
        final_size = FINAL_VIDEO.stat().st_size
    except OSError:
        final_size = 0

    checks["file"] = {
        "path": str(FINAL_VIDEO),
        "exists": FINAL_VIDEO.is_file(),
        "size_bytes": final_size,
    }
    checks["video_stream"] = {
        "codec": video_stream.get("codec_name"),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": round(fps, 3),
    }
    checks["audio_stream"] = {
        "codec": audio_stream.get("codec_name"),
        "sample_rate": audio_stream.get("sample_rate"),
    }

    if not FINAL_VIDEO.is_file() or final_size < 500_000:
        blockers.append("final_video_missing_or_too_small")
    if not video_stream:
        blockers.append("final_video_stream_missing")
    else:
        if str(video_stream.get("codec_name", "")).lower() != "h264":
            blockers.append("final_video_codec_not_h264")
        if int(video_stream.get("width", 0) or 0) != 1080 or int(video_stream.get("height", 0) or 0) != 1920:
            blockers.append("final_resolution_not_1080x1920")
        if not 29.0 <= fps <= 31.0:
            blockers.append(f"final_fps_invalid:{fps:.3f}")
    if not audio_stream:
        blockers.append("final_audio_stream_missing")
    elif str(audio_stream.get("codec_name", "")).lower() != "aac":
        blockers.append("final_audio_codec_not_aac")

    try:
        tolerance = float(os.getenv("SAP_AV_SYNC_TOLERANCE_SECONDS", "0.75") or 0.75)
    except (TypeError, ValueError):
        tolerance = 0.75
    tolerance = max(0.10, min(tolerance, 2.0))
    delta = abs(video_duration - narration_duration) if video_duration > 0 and narration_duration > 0 else 9999.0
    checks["timing"] = {
        "video_duration": round(video_duration, 3),
        "narration_duration": round(narration_duration, 3),
        "difference": round(delta, 3),
        "tolerance": tolerance,
    }
    if video_duration <= 0:
        blockers.append("final_video_duration_invalid")
    if narration_duration <= 0:
        blockers.append("narration_duration_invalid")
    if delta > tolerance:
        blockers.append(
            f"audio_video_duration_mismatch:{delta:.3f}>{tolerance:.3f}"
        )

    dialogue_count = 0
    subtitle_last = 0.0
    subtitle_invalid = 0
    if ASS.is_file():
        try:
            for line in ASS.read_text(encoding="utf-8", errors="strict").splitlines():
                if not line.startswith("Dialogue:"):
                    continue
                parts = line.split(",", 9)
                if len(parts) != 10:
                    subtitle_invalid += 1
                    continue
                start = ass_seconds(parts[1].strip())
                end = ass_seconds(parts[2].strip())
                if start is None or end is None or start < 0 or end <= start:
                    subtitle_invalid += 1
                    continue
                dialogue_count += 1
                subtitle_last = max(subtitle_last, end)
        except Exception:
            subtitle_invalid += 1
    checks["subtitles"] = {
        "exists": ASS.is_file(),
        "dialogues": dialogue_count,
        "invalid": subtitle_invalid,
        "last_end": round(subtitle_last, 3),
    }
    if not ASS.is_file() or dialogue_count <= 0 or subtitle_invalid:
        blockers.append("final_subtitle_source_invalid")
    elif narration_duration > 0 and subtitle_last > narration_duration + tolerance:
        blockers.append("final_subtitle_timing_exceeds_narration")

    audio_report = load(FINAL_AUDIO_REPORT)
    checks["audio_master"] = {
        "status": audio_report.get("status"),
        "report": str(FINAL_AUDIO_REPORT),
    }
    if audio_report and str(audio_report.get("status", "")).upper() == "BLOCK":
        blockers.append("audio_master_block")

    decode_ok = False
    decode_error = ""
    if FINAL_VIDEO.is_file() and final_size >= 500_000:
        decode_timeout = max(60, min(600, int(max(video_duration, 1.0) * 4 + 60)))
        try:
            proc = subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-v", "error",
                    "-i", str(FINAL_VIDEO),
                    "-map", "0:v:0", "-map", "0:a:0?",
                    "-f", "null", "-",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=decode_timeout,
                check=False,
            )
            decode_ok = proc.returncode == 0
            decode_error = (proc.stderr or "")[-1800:]
        except subprocess.TimeoutExpired as exc:
            decode_error = f"decode_timeout:{decode_timeout}s:{str(exc.stderr or '')[-800:]}"
        except Exception as exc:
            decode_error = f"{type(exc).__name__}:{str(exc)[:800]}"
    checks["decode"] = {
        "ok": decode_ok,
        "error": decode_error or None,
    }
    if not decode_ok:
        blockers.append("final_video_decode_failed")

    status = "PASS" if not blockers else "BLOCK"
    payload = {
        "short_id": SID,
        "version": "POST_RENDER_QA_1.0",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "blockers": blockers,
    }
    atomic(POST_OUT, payload)

    print()
    print("================================")
    print("POST RENDER QA")
    print("================================")
    print(f"File .................... {'OK' if FINAL_VIDEO.is_file() and final_size >= 500_000 else 'FAIL'}")
    print(f"Video stream ............ {'OK' if video_stream else 'FAIL'}")
    print(f"Audio stream ............ {'OK' if audio_stream else 'FAIL'}")
    print(f"Resolution .............. {video_stream.get('width', '?')}x{video_stream.get('height', '?')}")
    print(f"FPS ..................... {fps:.3f}")
    print(f"Duration delta .......... {delta:.3f}s")
    print(f"Subtitle source ......... {'OK' if dialogue_count and not subtitle_invalid else 'FAIL'}")
    print(f"Decode verification ..... {'OK' if decode_ok else 'FAIL'}")
    if blockers:
        print("Blockers ................ " + ",".join(blockers))
    print(f"RESULT: {status}")
    return 0 if status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro render contract")
    parser.add_argument(
        "--post-render",
        action="store_true",
        help="validate the encoded final artifact instead of pre-render inputs",
    )
    args = parser.parse_args()
    return post_render_main() if args.post_render else pre_render_main()


if __name__ == "__main__":
    raise SystemExit(main())

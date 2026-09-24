#!/usr/bin/env python3

import hashlib
import json
import math
import os
import re
import subprocess
from subprocess_guard import run_group
import tempfile
from datetime import date, datetime
from pathlib import Path


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except (TypeError, ValueError):
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = BASE / "roteiros"
MANIFEST_DIR = BASE / "manifests"
SAIDA = MANIFEST_DIR / f"{SHORT_ID}.json"

TOPIC = R / f"used_topic_{SHORT_ID}.txt"
TOPIC_FALLBACK = R / f"topic_{SHORT_ID}.txt"
HOOK = R / f"hook_{SHORT_ID}.txt"
ROTEIRO = R / f"short_{SHORT_ID}.txt"
FONTE = R / f"fonte_{SHORT_ID}.txt"
SCENE_MAP = R / f"scene_map_{SHORT_ID}.json"
PUBLISH = R / f"publish_{SHORT_ID}.json"
PUBLISH_INTEGRITY = R / f"publish_integrity_{SHORT_ID}.json"
LEDGER = BASE / "credits" / f"ledger_{SHORT_ID}.json"
VIDEO = BASE / "videos" / f"short_v6_{SHORT_ID}.mp4"
LOG = BASE / "logs" / "producao" / f"short_{SHORT_ID}.log"
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
INTELLIGENCE_DIR = BASE / "reports" / "intelligence"
RENDER_IDENTITY = MANIFEST_DIR / f"{SHORT_ID}_render_identity.json"
MEDIA_QUALITY = R / f"media_quality_{SHORT_ID}.json"
VISUAL_QA = BASE / "reports" / "evolution" / f"visual_qa_{SHORT_ID}.json"
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def read_json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def safe_float(value) -> float:
    try:
        result = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def parse_fps(value) -> float:
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


def ffprobe(path: Path):
    if not path.is_file():
        return {}
    try:
        result = run_group(
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
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def text_sha256(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", str(text), flags=re.UNICODE))


def scene_numbers(scenes):
    if not isinstance(scenes, list):
        return []
    numbers = []
    for item in scenes:
        if not isinstance(item, dict):
            return []
        try:
            numbers.append(int(item.get("scene")))
        except (TypeError, ValueError, OverflowError):
            return []
    return numbers


def media_inventory(media_dir: Path):
    if not media_dir.is_dir():
        return []
    return sorted(
        item for item in media_dir.glob("scene_*")
        if item.is_file() and item.suffix.lower() in MEDIA_EXTENSIONS
    )


def inspect_video(info):
    fmt = info.get("format", {}) if isinstance(info, dict) else {}
    streams = info.get("streams", []) if isinstance(info, dict) else []
    if not isinstance(fmt, dict):
        fmt = {}
    if not isinstance(streams, list):
        streams = []

    duration = safe_float(fmt.get("duration"))
    width = height = 0
    fps = 0.0
    video_codec = ""
    audio_codec = ""

    for stream in streams:
        if not isinstance(stream, dict):
            continue
        kind = stream.get("codec_type")
        if kind == "video" and not video_codec:
            video_codec = str(stream.get("codec_name", "") or "")
            width = safe_int(stream.get("width"))
            height = safe_int(stream.get("height"))
            fps = parse_fps(stream.get("avg_frame_rate"))
        elif kind == "audio" and not audio_codec:
            audio_codec = str(stream.get("codec_name", "") or "")

    return duration, width, height, fps, video_codec, audio_codec


def build_manifest(probe_data=None):
    topic = read_text(TOPIC) or read_text(TOPIC_FALLBACK)
    hook = read_text(HOOK)
    script = read_text(ROTEIRO)
    source = read_text(FONTE)
    publish = read_json(PUBLISH)
    publish_integrity = read_json(PUBLISH_INTEGRITY)
    render_identity = read_json(RENDER_IDENTITY)
    ledger = read_json(LEDGER)
    scene_map = read_json(SCENE_MAP)
    media_quality = read_json(MEDIA_QUALITY)
    visual_qa = read_json(VISUAL_QA)
    intelligence = {
        phase: read_json(INTELLIGENCE_DIR / f"{phase}_{SHORT_ID}.json")
        for phase in ("pre", "scene", "media", "final")
    }

    scenes = scene_map.get("scenes", []) if isinstance(scene_map, dict) else []
    if not isinstance(scenes, list):
        scenes = []
    expected_numbers = list(range(1, QTD_CENAS + 1))
    map_numbers = scene_numbers(scenes)

    info = probe_data if isinstance(probe_data, dict) else ffprobe(VIDEO)
    duration, width, height, fps, video_codec, audio_codec = inspect_video(info)
    video_codec_normalized = video_codec.strip().lower()
    audio_codec_normalized = audio_codec.strip().lower()

    media_files = media_inventory(MEDIA_DIR)
    media_numbers = []
    media_names_ok = True
    for path in media_files:
        match = re.fullmatch(r"scene_(\d+)", path.stem, flags=re.IGNORECASE)
        if not match:
            media_names_ok = False
            continue
        media_numbers.append(int(match.group(1)))

    media_numbering_ok = (
        media_names_ok
        and len(media_numbers) == QTD_CENAS
        and sorted(media_numbers) == expected_numbers
        and len(set(media_numbers)) == len(media_numbers)
    )
    scene_map_numbering_ok = map_numbers == expected_numbers

    hashtags = publish.get("hashtags", []) if isinstance(publish, dict) else []
    if not isinstance(hashtags, list):
        hashtags = []

    topic_sha = text_sha256(topic) if topic else ""
    render_topic_sha = str(render_identity.get("topic_sha256", "") or "")
    render_identity_match = bool(
        render_identity
        and str(render_identity.get("short_id", "") or "") == SHORT_ID
        and topic_sha
        and render_topic_sha == topic_sha
    )

    video_exists = False
    video_size = 0
    video_mtime_ns = 0
    try:
        video_stat = VIDEO.stat()
        video_size = int(video_stat.st_size)
        video_mtime_ns = int(video_stat.st_mtime_ns)
        video_exists = VIDEO.is_file() and video_size > 500_000
    except OSError:
        video_exists = False

    media_critical = (
        media_quality.get("critical", [])
        if isinstance(media_quality.get("critical"), list)
        else []
    )
    neutral_editorial = (
        media_quality.get("neutral_editorial_scenes", [])
        if isinstance(media_quality.get("neutral_editorial_scenes"), list)
        else []
    )
    media_gate_pass = (
        bool(media_quality)
        and str(media_quality.get("status", "")).upper() == "PASS"
        and not media_critical
        and not neutral_editorial
    )
    vqa_status = str(visual_qa.get("status", "") or "").upper()
    rendered_content = (
        visual_qa.get("measurements", {}).get("rendered_content", {})
        if isinstance(visual_qa.get("measurements"), dict)
        else {}
    )
    rendered_content_verified = (
        bool(rendered_content)
        and bool(rendered_content.get("available"))
        and bool(rendered_content.get("scene_timeline_available"))
        and not bool(rendered_content.get("opening_blank"))
        and not (
            rendered_content.get("blank_scenes", [])
            if isinstance(rendered_content.get("blank_scenes"), list)
            else []
        )
    )

    quality = {
        "video_exists": video_exists,
        "v6_only": True,
        "expected_scene_count": QTD_CENAS,
        "scene_map_count": len(scenes),
        "scene_map_numbering_ok": scene_map_numbering_ok,
        "physical_scene_count": len(media_files),
        "media_numbering_ok": media_numbering_ok,
        "media_gate_pass": media_gate_pass,
        "neutral_editorial_absent": not neutral_editorial,
        "visual_qa_present": bool(visual_qa),
        "visual_qa_not_blocked": vqa_status in {"PASS", "REVIEW"},
        "rendered_content_verified": rendered_content_verified,
        "resolution_ok": width == 1080 and height == 1920,
        "fps_ok": 29.0 <= fps <= 31.0,
        "video_codec_ok": video_codec_normalized == "h264",
        "audio_exists": bool(audio_codec),
        "audio_codec_ok": audio_codec_normalized == "aac",
        "duration_ok": 15.0 <= duration <= 180.0,
        "topic_exists": bool(topic),
        "hook_exists": bool(hook),
        "script_exists": bool(script) and 105 <= count_words(script) <= 125,
        "source_exists": bool(source),
        "publish_exists": bool(publish),
        "publish_title_exists": bool(str(publish.get("chosen_title", "") or "").strip()),
        "publish_description_exists": bool(str(publish.get("description", "") or "").strip()),
        "publish_hashtags_ok": len(hashtags) == 5,
        "publish_integrity_pass": publish_integrity.get("status") == "PASS",
        "source_ledger_exists": bool(ledger) and ledger.get("short_id") == SHORT_ID,
        "render_identity_match": render_identity_match,
    }

    quality_pass = all(quality.values())
    topic_path = TOPIC if TOPIC.is_file() else TOPIC_FALLBACK
    input_artifacts = {
        "topic_path": str(topic_path),
        "topic_sha256": file_sha256(topic_path),
        "hook_sha256": file_sha256(HOOK),
        "script_sha256": file_sha256(ROTEIRO),
        "source_sha256": file_sha256(FONTE),
        "publish_sha256": file_sha256(PUBLISH),
        "publish_integrity_sha256": file_sha256(PUBLISH_INTEGRITY),
        "source_ledger_sha256": file_sha256(LEDGER),
    }

    manifest = {
        "short_id": SHORT_ID,
        "created_at": datetime.now().isoformat(),
        "status": "QUALITY_PASS" if quality_pass else "INCOMPLETE",
        "topic": topic,
        "hook": hook,
        "script": {"path": str(ROTEIRO), "text": script},
        "source": {"path": str(FONTE)},
        "publish": {
            "path": str(PUBLISH),
            "chosen_title": publish.get("chosen_title", ""),
            "titles": publish.get("titles", []),
            "description": publish.get("description", ""),
            "hashtags": hashtags,
            "pinned_comment": publish.get("pinned_comment", ""),
            "integrity_report": str(PUBLISH_INTEGRITY),
        },
        "source_ledger": str(LEDGER),
        "artifact_identity": {
            "canonical_topic_sha256": topic_sha,
            "input_artifacts": input_artifacts,
            "render_identity_path": str(RENDER_IDENTITY),
            "render_identity": render_identity,
            "match": render_identity_match,
        },
        "scenes": {
            "map_path": str(SCENE_MAP),
            "expected_count": QTD_CENAS,
            "count": len(scenes),
            "physical_count": len(media_files),
            "items": scenes,
        },
        "visual_integrity": {
            "media_quality_path": str(MEDIA_QUALITY),
            "media_quality_status": media_quality.get("status"),
            "neutral_editorial_scenes": neutral_editorial,
            "visual_qa_path": str(VISUAL_QA),
            "visual_qa_status": visual_qa.get("status"),
            "rendered_content": rendered_content,
        },
        "video": {
            "path": str(VIDEO),
            "version": "V6",
            "duration_seconds": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "size_bytes": video_size,
            "mtime_ns": video_mtime_ns,
        },
        "quality": quality,
        "intelligence": {
            "version": "INTELLIGENCE_1.0",
            "reports": {
                phase: str(INTELLIGENCE_DIR / f"{phase}_{SHORT_ID}.json")
                for phase in ("pre", "scene", "media", "final")
            },
            "status": {
                phase: (intelligence.get(phase, {}) or {}).get("status", "MISSING")
                for phase in ("pre", "scene", "media", "final")
            },
            "module_versions": (intelligence.get("final", {}) or {}).get("module_versions", {}),
            "explainable_qa": (intelligence.get("final", {}) or {}).get("explainable_qa", {}),
            "confidence_automation": (intelligence.get("final", {}) or {}).get("confidence_automation", {}),
        },
        "log": str(LOG),
    }
    return manifest, quality_pass


def main() -> int:
    if not SHORT_ID:
        print("ERRO: SHORT_ID vazio")
        return 1

    manifest, quality_pass = build_manifest()
    try:
        atomic_json(SAIDA, manifest)
    except Exception as exc:
        print(f"ERRO: falha gravando manifest: {exc}")
        return 1

    print()
    print("================================")
    print("PRODUCTION MANIFEST - 2.2")
    print("================================")
    print(f"ID: {SHORT_ID}")
    print(f"Status: {manifest['status']}")
    print(f"Assunto: {manifest['topic'] or 'AUSENTE'}")
    print(f"Cenas: {manifest['scenes']['physical_count']}/{QTD_CENAS}")
    video = manifest["video"]
    print(
        f"Vídeo: {video['width']}x{video['height']} "
        f"{video['fps']:.2f}fps {video['duration_seconds']:.2f}s "
        f"{video['video_codec'] or '?'}+{video['audio_codec'] or '?'}"
    )
    print(f"Manifest: {SAIDA}")
    print()

    if not quality_pass:
        print("PRODUCTION MANIFEST: INCOMPLETE")
        for key, ok in manifest["quality"].items():
            if not ok:
                print(f"ERRO: {key}")
        return 1

    print("PRODUCTION MANIFEST: OK")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

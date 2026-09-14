#!/usr/bin/env python3

import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

from source_identity import validar_identidade


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except (TypeError, ValueError):
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

ROTEIROS = BASE / "roteiros"
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}

PATHS = {
    "topic_real": ROTEIROS / f"used_topic_{SHORT_ID}.txt",
    "topic": ROTEIROS / f"topic_{SHORT_ID}.txt",
    "script": ROTEIROS / f"short_{SHORT_ID}.txt",
    "source": ROTEIROS / f"fonte_{SHORT_ID}.txt",
    "scene_map": ROTEIROS / f"scene_map_{SHORT_ID}.json",
    "motion": ROTEIROS / f"motion_plan_{SHORT_ID}.json",
    "report": ROTEIROS / f"supervisor_{SHORT_ID}.json",
}


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


def words(text):
    return re.findall(r"\b[\wÀ-ÿ'-]+\b", str(text), flags=re.UNICODE)


def word_count(text):
    return len(words(text))


def tokens(text):
    stop = {
        "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em",
        "um", "uma", "the", "of", "and", "in", "on", "cinematic", "dramatic",
        "dark", "vintage", "historic",
    }
    return {
        item
        for item in re.findall(r"[a-z0-9à-ÿ]+", str(text).lower())
        if item not in stop and len(item) >= 3
    }


def similarity(a, b):
    ta = tokens(a)
    tb = tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def first_sentence(text):
    parts = re.split(r"(?<=[.!?])\s+", str(text).strip())
    return parts[0] if parts else ""


def validate_numbered_scenes(data, label):
    if not isinstance(data, dict):
        return [], [f"{label}_invalid"]
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        return [], [f"{label}_scenes_not_list"]
    if len(scenes) != QTD_CENAS:
        return scenes, [f"{label}_count_{len(scenes)}"]

    numbers = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            return scenes, [f"{label}_scene_{index}_invalid"]
        try:
            numbers.append(int(scene.get("scene")))
        except (TypeError, ValueError, OverflowError):
            return scenes, [f"{label}_scene_{index}_number_invalid"]

    expected = list(range(1, QTD_CENAS + 1))
    if numbers != expected:
        return scenes, [f"{label}_numbering_invalid"]
    return scenes, []


def media_inventory():
    if not MEDIA_DIR.is_dir():
        return [], ["physical_media_dir_missing"]

    by_number = {}
    errors = []
    for path in sorted(MEDIA_DIR.glob("scene_*")):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        match = re.fullmatch(r"scene_(\d+)", path.stem, flags=re.IGNORECASE)
        if not match:
            errors.append(f"media_name_invalid:{path.name}")
            continue
        number = int(match.group(1))
        if not 1 <= number <= QTD_CENAS:
            errors.append(f"media_scene_out_of_range:{number}")
            continue
        if number in by_number:
            errors.append(f"media_duplicate_scene:{number}")
            continue
        by_number[number] = path

    missing = [n for n in range(1, QTD_CENAS + 1) if n not in by_number]
    if missing:
        errors.append("media_missing_scenes:" + ",".join(map(str, missing)))

    return [by_number[n] for n in sorted(by_number)], errors


def evaluate(topic, script, source_text, scene_map, motion):
    score = 100
    critical = []
    warnings = []
    strengths = []

    if not topic:
        critical.append("topic_missing")
        score -= 40
    if not script:
        critical.append("script_missing")
        score -= 40
    if not source_text:
        critical.append("source_missing")
        score -= 40

    wiki_title = ""
    match = re.search(r"Wikipedia\s*[—-]\s*(.+)", source_text, flags=re.IGNORECASE)
    if match:
        wiki_title = match.group(1).splitlines()[0].strip()

    if topic and wiki_title:
        try:
            identity = validar_identidade(topic, wiki_title, source_text)
            identity_ok = isinstance(identity, dict) and bool(identity.get("valid"))
        except Exception:
            identity_ok = False
        if not identity_ok:
            critical.append("source_identity_mismatch")
            score -= 50
        else:
            strengths.append("source_identity_pass")
    elif topic or source_text:
        critical.append("source_identity_not_measurable")
        score -= 25

    wc = word_count(script)
    if not 105 <= wc <= 125:
        critical.append(f"script_words_{wc}")
        score -= 25
    else:
        strengths.append("script_length")

    hook = first_sentence(script)
    hook_wc = word_count(hook)
    if 6 <= hook_wc <= 16:
        strengths.append("hook_length")
    else:
        warnings.append(f"hook_words_{hook_wc}")
        score -= 5

    sentences = [item.strip() for item in re.split(r"[.!?]+", script) if item.strip()]
    long_sentences = [item for item in sentences if word_count(item) > 24]
    if len(long_sentences) > 2:
        warnings.append(f"long_sentences_{len(long_sentences)}")
        score -= 5

    scenes, scene_errors = validate_numbered_scenes(scene_map, "scene_map")
    if scene_errors:
        critical.extend(scene_errors)
        score -= 35
    else:
        strengths.append(f"scene_count_{QTD_CENAS}")

    empty_query = 0
    empty_must = 0
    repetitions = 0
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        query = str(scene.get("query", "") or "").strip()
        must = scene.get("must_have", [])
        if not query:
            empty_query += 1
        if not isinstance(must, list) or not must:
            empty_must += 1
        if index > 0 and isinstance(scenes[index - 1], dict):
            previous = str(scenes[index - 1].get("query", "") or "")
            if similarity(previous, query) >= 0.55:
                repetitions += 1

    if empty_query:
        critical.append(f"empty_queries_{empty_query}")
        score -= empty_query * 5
    if empty_must:
        warnings.append(f"empty_must_{empty_must}")
        score -= min(empty_must * 2, 10)
    if repetitions:
        warnings.append(f"visual_repetition_{repetitions}")
        score -= min(repetitions * 3, 12)
    elif scenes:
        strengths.append("visual_variety")

    modes = [
        str(item.get("visual_mode", "") or "")
        for item in scenes if isinstance(item, dict)
    ]
    unique_modes = len({item for item in modes if item})
    if unique_modes >= 4:
        strengths.append("visual_mode_variety")
    else:
        warnings.append(f"visual_modes_only_{unique_modes}")
        score -= 6

    media, media_errors = media_inventory()
    if media_errors:
        critical.extend(media_errors)
        score -= 25
    elif len(media) == QTD_CENAS:
        strengths.append(f"physical_media_{QTD_CENAS}")

    videos = sum(1 for path in media if path.suffix.lower() == ".mp4")
    photos = len(media) - videos
    if videos >= 3:
        strengths.append(f"video_mix_{videos}")
    else:
        warnings.append(f"low_video_mix_{videos}")
        score -= 5

    motion_scenes, motion_errors = validate_numbered_scenes(motion, "motion_plan")
    if motion_errors:
        critical.extend(motion_errors)
        score -= 10
    else:
        strengths.append("motion_plan")

    movements = [
        str(item.get("motion_profile", "") or "")
        for item in motion_scenes if isinstance(item, dict)
    ]
    movement_unique = len({item for item in movements if item})
    if motion_scenes:
        if movement_unique >= 4:
            strengths.append("motion_variety")
        else:
            warnings.append(f"motion_variety_{movement_unique}")
            score -= 4

    final_text = " ".join(words(script)[-20:]).lower()
    cta_comment = any(
        item in final_text
        for item in {"comente", "opinião", "acha", "teoria", "aconteceu"}
    )
    if cta_comment:
        strengths.append("comment_cta")
    else:
        warnings.append("weak_comment_cta")
        score -= 3

    score = max(0, min(score, 100))
    if critical:
        status = "BLOCK"
    elif score >= 85:
        status = "EXCELLENT"
    elif score >= 75:
        status = "PASS"
    else:
        status = "WARNING"

    return {
        "short_id": SHORT_ID,
        "version": "5.2",
        "topic": topic,
        "wiki_title": wiki_title,
        "score": score,
        "status": status,
        "critical": critical,
        "warnings": warnings,
        "strengths": strengths,
        "metrics": {
            "expected_scenes": QTD_CENAS,
            "script_words": wc,
            "hook_words": hook_wc,
            "scenes": len(scenes),
            "visual_modes": unique_modes,
            "visual_repetitions": repetitions,
            "media_files": len(media),
            "videos": videos,
            "photos": photos,
            "motion_scenes": len(motion_scenes),
        },
    }


def main():
    if not SHORT_ID:
        print("ERRO: SHORT_ID vazio")
        return 1

    topic = read_text(PATHS["topic_real"]) or read_text(PATHS["topic"])
    script = read_text(PATHS["script"])
    source_text = read_text(PATHS["source"])
    scene_map = read_json(PATHS["scene_map"])
    motion = read_json(PATHS["motion"])
    report = evaluate(topic, script, source_text, scene_map, motion)

    try:
        atomic_json(PATHS["report"], report)
    except Exception as exc:
        print(f"ERRO PRODUCTION SUPERVISOR: falha gravando relatório: {exc}")
        return 1

    print()
    print("================================")
    print("PRODUCTION SUPERVISOR 5.2")
    print("================================")
    print()
    print(f"Assunto: {report['topic']}")
    print(f"Score global: {report['score']}/100")
    print(f"Status: {report['status']}")
    print()

    if report["strengths"]:
        print("PONTOS FORTES:")
        for item in report["strengths"]:
            print(f"  + {item}")
        print()
    if report["warnings"]:
        print("AVISOS:")
        for item in report["warnings"]:
            print(f"  - {item}")
        print()
    if report["critical"]:
        print("BLOQUEIOS:")
        for item in report["critical"]:
            print(f"  ! {item}")
        print()

    print(f"Relatório:\n{PATHS['report']}")
    print()
    if report["status"] == "BLOCK":
        print("PRODUCTION SUPERVISOR: BLOCK")
        return 1
    print("PRODUCTION SUPERVISOR: PASS")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

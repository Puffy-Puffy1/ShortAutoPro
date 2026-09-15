#!/usr/bin/env python3
"""Professional scene assembler for ShortAutoPro.

Consumes pro_edit_plan_<SHORT_ID>.json and renders a restrained vertical edit
with caption-aware pacing, smooth motion easing and variable short transitions.
The output contract remains temp/<SHORT_ID>/video_sem_audio.mp4.
"""

from __future__ import annotations

import glob
import json
import math
import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()


def expected_scenes() -> int:
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except (TypeError, ValueError):
        value = 12
    return max(6, min(20, value))


EXPECTED = expected_scenes()
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
AUDIO = BASE / "audios" / f"short_{SHORT_ID}.mp3"
ASS = BASE / "videos" / f"short_{SHORT_ID}.ass"
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
PRO_PLAN = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"
TEMP = BASE / "temp" / SHORT_ID
OUTPUT = TEMP / "video_sem_audio.mp4"
RUNTIME_REPORT = BASE / "roteiros" / f"pro_edit_runtime_{SHORT_ID}.json"

FPS = 30
PRESET = os.getenv("SHORT_PRESET_CENAS", "veryfast")
CRF = os.getenv("SHORT_CRF_CENAS", "22")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS


def timeout_value(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


SCENE_TIMEOUT = timeout_value("SHORT_SCENE_RENDER_TIMEOUT", 300, 60, 1200)
ASSEMBLY_TIMEOUT = timeout_value("SHORT_ASSEMBLY_TIMEOUT", 900, 120, 2400)


def fail(message: str) -> None:
    raise SystemExit(f"ERRO PROFESSIONAL VIDEO: {message}")


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{label} inválido: {exc}")
    if not isinstance(data, dict):
        fail(f"{label} precisa ser objeto JSON")
    return data


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def duration(path: Path) -> float:
    try:
        raw = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ], text=True, stderr=subprocess.DEVNULL, timeout=45).strip()
        value = float(raw)
    except Exception as exc:
        fail(f"não foi possível ler duração de {path}: {exc}")
    if not math.isfinite(value) or value <= 0:
        fail(f"duração inválida: {path}")
    return value


def scene_number(path: Path) -> int | None:
    match = re.match(r"^scene_(\d+)", path.name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def collect_media() -> list[Path]:
    if not MEDIA_DIR.is_dir():
        fail(f"pasta de mídia ausente: {MEDIA_DIR}")
    by_scene: dict[int, Path] = {}
    for raw in glob.glob(str(MEDIA_DIR / "scene_*")):
        path = Path(raw)
        if path.suffix.lower() not in MEDIA_EXTS:
            continue
        number = scene_number(path)
        if number is None or not 1 <= number <= EXPECTED:
            fail(f"número de cena inválido: {path.name}")
        if number in by_scene:
            fail(f"mídia ambígua para cena {number:02d}")
        by_scene[number] = path
    missing = [n for n in range(1, EXPECTED + 1) if n not in by_scene]
    if missing:
        fail("mídia ausente: " + ", ".join(f"{x:02d}" for x in missing))
    return [by_scene[x] for x in range(1, EXPECTED + 1)]


def valid_scene_list(data: dict[str, Any], label: str) -> list[dict[str, Any]]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != EXPECTED:
        fail(f"{label} precisa ter {EXPECTED} cenas")
    result: list[dict[str, Any]] = []
    for idx, item in enumerate(scenes, start=1):
        if not isinstance(item, dict) or int(item.get("scene", 0) or 0) != idx:
            fail(f"{label} cena {idx} inválida")
        result.append(item)
    return result


def ass_time(value: str) -> float | None:
    try:
        h, m, rest = value.split(":")
        sec, cent = rest.split(".")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(cent) / 100.0
    except Exception:
        return None


def caption_starts() -> list[float]:
    if not ASS.is_file():
        return []
    starts: list[float] = []
    try:
        for line in ASS.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.startswith("Dialogue:"):
                continue
            parts = line.split(",", 9)
            if len(parts) != 10:
                continue
            start = ass_time(parts[1].strip())
            end = ass_time(parts[2].strip())
            if start is not None and end is not None and end > start:
                starts.append(start)
    except Exception:
        return []
    return sorted(set(starts))


def words(text: Any) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", str(text or ""), flags=re.UNICODE))


def normalize_durations(raw: list[float], total: float, minimum: float = 1.0) -> list[float]:
    n = len(raw)
    if n == 0:
        return []
    if total < minimum * n:
        return [total / n] * n
    values = [max(0.01, float(x)) for x in raw]
    result = [0.0] * n
    remaining = set(range(n))
    remaining_total = total
    while remaining:
        weight_sum = sum(values[i] for i in remaining)
        provisional = {i: remaining_total * values[i] / weight_sum for i in remaining}
        below = [i for i, value in provisional.items() if value < minimum]
        if not below:
            for i, value in provisional.items():
                result[i] = value
            break
        for i in below:
            result[i] = minimum
            remaining_total -= minimum
            remaining.remove(i)
    if result:
        result[-1] += total - sum(result)
    return result


def allocate_durations(scene_map: list[dict[str, Any]], pro_scenes: list[dict[str, Any]], total: float) -> tuple[list[float], str]:
    weights: list[float] = []
    for scene, pro in zip(scene_map, pro_scenes):
        try:
            base_words = int(scene.get("words", 0) or 0)
        except (TypeError, ValueError):
            base_words = 0
        base_words = base_words or words(scene.get("segment")) or 1
        try:
            pace = float(pro.get("pace_multiplier", 1.0))
        except (TypeError, ValueError):
            pace = 1.0
        weights.append(max(0.2, base_words * max(0.78, min(1.14, pace))))

    starts = caption_starts()
    if len(starts) >= EXPECTED:
        boundaries = [0.0]
        total_weight = sum(weights)
        cumulative = 0.0
        for i in range(EXPECTED - 1):
            cumulative += weights[i]
            ratio = cumulative / total_weight
            index = round(ratio * (len(starts) - 1))
            index = max(1, min(index, len(starts) - 1))
            point = max(boundaries[-1] + 0.05, min(starts[index], total))
            boundaries.append(min(point, total))
        boundaries.append(total)
        raw = [max(0.01, boundaries[i + 1] - boundaries[i]) for i in range(EXPECTED)]
        return normalize_durations(raw, total), "PRO_CAPTION_SEMANTIC"

    return normalize_durations(weights, total), "PRO_SCRIPT_WEIGHT"


def safe_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = default
    if not math.isfinite(number):
        number = default
    return max(low, min(high, number))


def render_scene(path: Path, number: int, logical: float, pro: dict[str, Any], transition_after: float) -> Path:
    TEMP.mkdir(parents=True, exist_ok=True)
    output = TEMP / f"pro_scene_{number:02d}.mp4"
    try:
        output.unlink(missing_ok=True)
    except OSError as exc:
        fail(f"não foi possível limpar cena {number}: {exc}")

    render_duration = logical + (transition_after if number < EXPECTED else 0.0)
    frames = max(1, round(render_duration * FPS))
    ext = path.suffix.lower()

    if ext in IMAGE_EXTS:
        start = safe_float(pro.get("zoom_start"), 1.0, 1.0, 1.08)
        end = safe_float(pro.get("zoom_end"), start, start, 1.10)
        delta = max(0.0, end - start)
        denom = max(frames - 1, 1)
        p = f"(on/{denom})"
        smooth = f"(3*pow({p},2)-2*pow({p},3))"
        zoom = f"{start:.6f}+{delta:.6f}*{smooth}"
        pan = str(pro.get("pan", "center")).strip().lower()
        travel = f"(iw-iw/zoom)"
        if pan == "right":
            x = f"{travel}*{smooth}"
        elif pan == "left":
            x = f"{travel}*(1-{smooth})"
        else:
            x = f"{travel}/2"
        y = "(ih-ih/zoom)/2"
        vf = (
            "scale=1200:2133:force_original_aspect_ratio=increase,"
            "crop=1200:2133,"
            f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps={FPS},"
            "setsar=1,format=yuv420p"
        )
        command = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(path),
            "-vf", vf, "-frames:v", str(frames), "-an",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", "yuv420p", str(output),
        ]
    elif ext in VIDEO_EXTS:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p"
        command = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(path),
            "-t", f"{render_duration:.6f}", "-vf", vf, "-an",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", "yuv420p", str(output),
        ]
    else:
        fail(f"extensão não suportada: {ext}")

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=SCENE_TIMEOUT)
    except subprocess.TimeoutExpired:
        fail(f"render da cena {number:02d} excedeu {SCENE_TIMEOUT}s")
    except subprocess.CalledProcessError as exc:
        fail(f"FFmpeg falhou na cena {number:02d}: {exc.returncode}")
    if not output.is_file() or output.stat().st_size <= 0:
        fail(f"render vazio na cena {number:02d}")
    return output


def assemble(scene_files: list[Path], logical_durations: list[float], pro_scenes: list[dict[str, Any]], total: float) -> None:
    try:
        OUTPUT.unlink(missing_ok=True)
    except OSError as exc:
        fail(f"não foi possível limpar montagem anterior: {exc}")

    command = ["ffmpeg", "-y"]
    for scene in scene_files:
        command.extend(["-i", str(scene)])

    filters: list[str] = []
    accumulated = logical_durations[0]
    first_transition = max(2 / FPS, safe_float(pro_scenes[0].get("transition_duration"), 0.075, 0.0, 0.18))
    filters.append(
        f"[0:v][1:v]xfade=transition=fade:duration={first_transition:.6f}:offset={accumulated:.6f}[v1]"
    )
    for i in range(2, len(scene_files)):
        accumulated += logical_durations[i - 1]
        trans = max(2 / FPS, safe_float(pro_scenes[i - 1].get("transition_duration"), 0.075, 0.0, 0.18))
        filters.append(
            f"[v{i-1}][{i}:v]xfade=transition=fade:duration={trans:.6f}:offset={accumulated:.6f}[v{i}]"
        )

    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", f"[v{len(scene_files)-1}]",
        "-t", f"{total:.6f}", "-an",
        "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
    ])
    try:
        subprocess.run(command, check=True, timeout=ASSEMBLY_TIMEOUT)
    except subprocess.TimeoutExpired:
        fail(f"montagem excedeu {ASSEMBLY_TIMEOUT}s")
    except subprocess.CalledProcessError as exc:
        fail(f"FFmpeg falhou na montagem: {exc.returncode}")


def main() -> int:
    if not AUDIO.is_file():
        fail("áudio ausente")
    if not PRO_PLAN.is_file():
        fail("professional edit plan ausente")
    media = collect_media()
    map_scenes = valid_scene_list(read_json(SCENE_MAP, "scene_map"), "scene_map")
    pro_data = read_json(PRO_PLAN, "pro_edit_plan")
    pro_scenes = valid_scene_list(pro_data, "pro_edit_plan")
    total = duration(AUDIO)
    durations, sync_mode = allocate_durations(map_scenes, pro_scenes, total)
    if abs(sum(durations) - total) > 0.05:
        fail("durações não fecham com o áudio")

    transitions = [
        0.0 if i == EXPECTED - 1 else max(2 / FPS, safe_float(scene.get("transition_duration"), 0.075, 0.0, 0.18))
        for i, scene in enumerate(pro_scenes)
    ]

    print("\n================================")
    print("PROFESSIONAL SCENE ASSEMBLER 1.0")
    print("================================")
    print(f"ID: {SHORT_ID}")
    print(f"Cenas: {len(media)}/{EXPECTED}")
    print(f"Duração: {total:.2f}s | sync={sync_mode}")
    print(f"Perfil: {pro_data.get('profile', 'default')} | plan-score={pro_data.get('professional_score')}")
    print()

    rendered: list[Path] = []
    for index, (path, logical, pro, trans) in enumerate(zip(media, durations, pro_scenes, transitions), start=1):
        print(
            f"{index:02d}/{EXPECTED} {path.name} {logical:.2f}s "
            f"pace={pro.get('pace_multiplier')} cut={pro.get('cut_style')} "
            f"motion={pro.get('motion_curve')}"
        )
        rendered.append(render_scene(path, index, logical, pro, trans))

    print("\nMontando ritmo profissional...")
    assemble(rendered, durations, pro_scenes, total)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 100_000:
        fail("video_sem_audio não foi criado")
    final_duration = duration(OUTPUT)
    if abs(final_duration - total) > max(0.75, 2 / FPS):
        fail(f"duração divergente: vídeo={final_duration:.2f}s áudio={total:.2f}s")

    runtime = {
        "short_id": SHORT_ID,
        "version": "PRO_ASSEMBLER_1.0",
        "sync_mode": sync_mode,
        "total_duration": round(total, 3),
        "final_duration": round(final_duration, 3),
        "durations": [round(x, 3) for x in durations],
        "transitions": [round(x, 3) for x in transitions],
        "output": str(OUTPUT),
        "status": "PASS",
    }
    atomic_json(RUNTIME_REPORT, runtime)
    print(f"\nPROFESSIONAL SCENE ASSEMBLER: PASS\nArquivo: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Professional multi-beat scene assembler for ShortAutoPro 3.0.2.

Builds per-scene motion clips, normalizes every clip to a deterministic CFR/time
base before transitions, validates scene timing, and automatically falls back to
safe hard cuts if the cinematic xfade chain cannot preserve the audio duration.
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
MULTI_PLAN = BASE / "roteiros" / f"multi_asset_{SHORT_ID}.json"
TEMP = BASE / "temp" / SHORT_ID
OUTPUT = TEMP / "video_sem_audio.mp4"
RUNTIME_REPORT = BASE / "roteiros" / f"pro_edit_runtime_{SHORT_ID}.json"

FPS = 30
TIME_BASE = "1/90000"
PRESET = os.getenv("SHORT_PRESET_CENAS", "veryfast")
CRF = os.getenv("SHORT_CRF_CENAS", "22")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS
_DURATION_CACHE: dict[tuple[str, int, int], float] = {}


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


def read_json(path: Path, label: str, optional: bool = False) -> dict[str, Any]:
    if optional and not path.is_file():
        return {}
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
        stat = path.stat()
        key = (str(path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    except OSError as exc:
        fail(f"não foi possível acessar {path}: {exc}")

    cached = _DURATION_CACHE.get(key)
    if cached is not None:
        return cached

    try:
        raw = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=45,
        ).strip()
        value = float(raw)
    except Exception as exc:
        fail(f"não foi possível ler duração de {path}: {exc}")
    if not math.isfinite(value) or value <= 0:
        fail(f"duração inválida: {path}")

    # Keep only the current identity for this path; a changed file gets a new
    # mtime/size key and therefore forces a real ffprobe.
    stale = [item for item in _DURATION_CACHE if item[0] == key[0] and item != key]
    for item in stale:
        _DURATION_CACHE.pop(item, None)
    _DURATION_CACHE[key] = value
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


def secondary_media() -> dict[int, Path]:
    data = read_json(MULTI_PLAN, "multi_asset", optional=True)
    assets = data.get("secondary_assets", []) if isinstance(data.get("secondary_assets"), list) else []
    result: dict[int, Path] = {}
    for item in assets:
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("scene"))
        except (TypeError, ValueError):
            continue
        path = Path(str(item.get("asset", ""))).expanduser()
        if path.is_file() and path.suffix.lower() in MEDIA_EXTS and 1 <= number <= EXPECTED:
            result[number] = path
    return result


def valid_scene_list(data: dict[str, Any], label: str) -> list[dict[str, Any]]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != EXPECTED:
        fail(f"{label} precisa ter {EXPECTED} cenas")
    result: list[dict[str, Any]] = []
    for idx, item in enumerate(scenes, 1):
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


def allocate_durations(
    scene_map: list[dict[str, Any]],
    pro_scenes: list[dict[str, Any]],
    total: float,
) -> tuple[list[float], str]:
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
            index = max(1, min(round(ratio * (len(starts) - 1)), len(starts) - 1))
            boundaries.append(min(max(boundaries[-1] + 0.05, starts[index]), total))
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


def render_beat(
    path: Path,
    output: Path,
    beat_duration: float,
    pro: dict[str, Any],
    beat_index: int,
    total_beats: int,
) -> None:
    del total_beats
    frames = max(1, round(beat_duration * FPS))
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        start = safe_float(pro.get("zoom_start"), 1.0, 1.0, 1.08)
        end = safe_float(pro.get("zoom_end"), start, start, 1.10)
        if beat_index > 0:
            start = min(1.075, max(start + 0.010, end))
            end = min(1.095, start + 0.012)
        delta = max(0.0, end - start)
        denom = max(frames - 1, 1)
        p = f"(on/{denom})"
        smooth = f"(3*pow({p},2)-2*pow({p},3))"
        zoom = f"{start:.6f}+{delta:.6f}*{smooth}"
        pan = str(pro.get("pan", "center")).strip().lower()
        if beat_index > 0 and pan in {"left", "right"}:
            pan = "right" if pan == "left" else "left"
        travel = "(iw-iw/zoom)"
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
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(path),
            "-vf", vf,
            "-frames:v", str(frames),
            "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", "yuv420p", str(output),
        ]
    elif ext in VIDEO_EXTS:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,fps=30,setsar=1,format=yuv420p"
        )
        command = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-stream_loop", "-1", "-i", str(path),
            "-t", f"{beat_duration:.6f}", "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", "yuv420p", str(output),
        ]
    else:
        fail(f"extensão não suportada: {ext}")

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SCENE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        fail(f"render do beat excedeu {SCENE_TIMEOUT}s")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "")[-1200:]
        fail(f"FFmpeg falhou em beat: {exc.returncode} {detail}")
    if not output.is_file() or output.stat().st_size <= 0:
        fail(f"beat vazio: {output.name}")


def join_two_beats(
    first: Path,
    second: Path,
    output: Path,
    first_duration: float,
    transition: float,
    total: float,
) -> None:
    offset = max(0.01, first_duration - transition)
    graph = (
        f"[0:v]fps={FPS},settb={TIME_BASE},setpts=N/({FPS}*TB),format=yuv420p[a];"
        f"[1:v]fps={FPS},settb={TIME_BASE},setpts=N/({FPS}*TB),format=yuv420p[b];"
        f"[a][b]xfade=transition=fade:duration={transition:.6f}:offset={offset:.6f},"
        f"fps={FPS},settb={TIME_BASE},setpts=N/({FPS}*TB)[v]"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(first), "-i", str(second),
        "-filter_complex", graph,
        "-map", "[v]", "-t", f"{total:.6f}",
        "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-pix_fmt", "yuv420p", str(output),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=SCENE_TIMEOUT)
    except subprocess.TimeoutExpired:
        fail(f"montagem multi-beat excedeu {SCENE_TIMEOUT}s")
    if proc.returncode != 0:
        fail(f"montagem multi-beat falhou: {(proc.stderr or '')[-1200:]}")


def render_scene(
    path: Path,
    number: int,
    logical: float,
    pro: dict[str, Any],
    transition_after: float,
    secondary: Path | None,
) -> tuple[Path, dict[str, Any]]:
    TEMP.mkdir(parents=True, exist_ok=True)
    output = TEMP / f"pro_scene_{number:02d}.mp4"
    output.unlink(missing_ok=True)
    render_duration = logical + (transition_after if number < EXPECTED else 0.0)
    role = str(pro.get("narrative_role", "")).lower()
    allow_detail = os.getenv("SAP_MULTI_BEAT_FALLBACK", "1") == "1"
    fallback_detail = (
        secondary is None
        and allow_detail
        and path.suffix.lower() in IMAGE_EXTS
        and render_duration >= 3.6
        and role in {
            "hook", "evidence", "development", "escalation", "reveal",
            "turn", "turning_point", "climax", "payoff",
        }
    )
    second = secondary if secondary is not None else path if fallback_detail else None
    if second is None:
        render_beat(path, output, render_duration, pro, 0, 1)
        return output, {
            "scene": number,
            "visual_beats": 1,
            "source_asset_count": 1,
            "secondary_asset": None,
            "fallback_detail_crop": False,
            "expected_render_duration": round(render_duration, 3),
        }

    internal_transition = max(1 / FPS, min(0.075, render_duration * 0.03))
    first_duration = render_duration * 0.58 + internal_transition / 2
    second_duration = render_duration * 0.42 + internal_transition / 2
    beat1 = TEMP / f"pro_scene_{number:02d}_beat_a.mp4"
    beat2 = TEMP / f"pro_scene_{number:02d}_beat_b.mp4"
    render_beat(path, beat1, first_duration, pro, 0, 2)
    render_beat(second, beat2, second_duration, pro, 1, 2)
    join_two_beats(beat1, beat2, output, first_duration, internal_transition, render_duration)
    return output, {
        "scene": number,
        "visual_beats": 2,
        "source_asset_count": 2 if secondary is not None else 1,
        "secondary_asset": str(secondary) if secondary is not None else None,
        "fallback_detail_crop": fallback_detail,
        "internal_transition": round(internal_transition, 3),
        "expected_render_duration": round(render_duration, 3),
    }


def transition_duration(pro: dict[str, Any]) -> float:
    cut_style = str(pro.get("cut_style", "editorial_cut"))
    configured = safe_float(pro.get("transition_duration"), 0.075, 0.0, 0.18)
    if cut_style == "near_cut":
        return max(1 / FPS, min(configured, 0.045))
    if cut_style in {"soft_fade", "closing_hold"}:
        return max(0.09, configured)
    return max(2 / FPS, min(configured, 0.095))


def validate_rendered_scenes(
    scene_files: list[Path],
    logical_durations: list[float],
    transitions: list[float],
) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for index, path in enumerate(scene_files):
        actual = duration(path)
        expected = logical_durations[index] + transitions[index]
        delta = actual - expected
        tolerance = max(0.20, 3 / FPS)
        status = "PASS" if abs(delta) <= tolerance else "WARN"
        report.append({
            "scene": index + 1,
            "expected": round(expected, 3),
            "actual": round(actual, 3),
            "delta": round(delta, 3),
            "status": status,
        })
        if status != "PASS":
            print(
                f"AVISO timing cena {index + 1:02d}: "
                f"esperado={expected:.3f}s real={actual:.3f}s"
            )
    return report


def run_ffmpeg(command: list[str], label: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=ASSEMBLY_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"{label} excedeu {ASSEMBLY_TIMEOUT}s"
    if proc.returncode != 0:
        return False, f"{label} rc={proc.returncode}: {(proc.stderr or '')[-1800:]}"
    return True, (proc.stderr or "")[-800:]


def assemble_xfade(
    scene_files: list[Path],
    logical_durations: list[float],
    transitions: list[float],
    total: float,
) -> tuple[bool, str]:
    OUTPUT.unlink(missing_ok=True)
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for scene in scene_files:
        command.extend(["-i", str(scene)])

    filters: list[str] = []
    for i, _scene in enumerate(scene_files):
        expected_input = logical_durations[i] + transitions[i]
        filters.append(
            f"[{i}:v]fps={FPS},trim=duration={expected_input:.6f},"
            f"settb={TIME_BASE},setpts=N/({FPS}*TB),format=yuv420p[s{i}]"
        )

    accumulated = logical_durations[0]
    first_transition = transitions[0]
    filters.append(
        f"[s0][s1]xfade=transition=fade:duration={first_transition:.6f}:"
        f"offset={accumulated:.6f},fps={FPS},settb={TIME_BASE},"
        f"setpts=N/({FPS}*TB)[v1]"
    )
    for i in range(2, len(scene_files)):
        accumulated += logical_durations[i - 1]
        trans = transitions[i - 1]
        filters.append(
            f"[v{i-1}][s{i}]xfade=transition=fade:duration={trans:.6f}:"
            f"offset={accumulated:.6f},fps={FPS},settb={TIME_BASE},"
            f"setpts=N/({FPS}*TB)[v{i}]"
        )

    final_label = f"v{len(scene_files) - 1}"
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", f"[{final_label}]",
        "-t", f"{total:.6f}",
        "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
    ])
    return run_ffmpeg(command, "xfade assembly")


def assemble_hard_cut(
    scene_files: list[Path],
    logical_durations: list[float],
    total: float,
) -> tuple[bool, str]:
    OUTPUT.unlink(missing_ok=True)
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for scene in scene_files:
        command.extend(["-i", str(scene)])

    filters: list[str] = []
    labels: list[str] = []
    for i, logical in enumerate(logical_durations):
        label = f"c{i}"
        labels.append(f"[{label}]")
        filters.append(
            f"[{i}:v]fps={FPS},trim=duration={logical:.6f},"
            f"settb={TIME_BASE},setpts=N/({FPS}*TB),format=yuv420p[{label}]"
        )
    filters.append(
        "".join(labels)
        + f"concat=n={len(scene_files)}:v=1:a=0,fps={FPS},"
        f"settb={TIME_BASE},setpts=N/({FPS}*TB)[vout]"
    )
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-t", f"{total:.6f}",
        "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT),
    ])
    return run_ffmpeg(command, "hard-cut fallback")


def assemble(
    scene_files: list[Path],
    logical_durations: list[float],
    pro_scenes: list[dict[str, Any]],
    total: float,
) -> tuple[list[float], str, list[dict[str, Any]]]:
    transitions = [
        0.0 if i == EXPECTED - 1 else transition_duration(scene)
        for i, scene in enumerate(pro_scenes)
    ]
    timing_report = validate_rendered_scenes(scene_files, logical_durations, transitions)

    ok, detail = assemble_xfade(scene_files, logical_durations, transitions, total)
    if ok and OUTPUT.is_file() and OUTPUT.stat().st_size >= 100_000:
        produced = duration(OUTPUT)
        if abs(produced - total) <= max(0.35, 3 / FPS):
            print(f"ASSEMBLY MODE: NORMALIZED_XFADE ({produced:.2f}s)")
            return transitions, "NORMALIZED_XFADE", timing_report
        print(
            f"AVISO xfade com duração divergente: vídeo={produced:.2f}s "
            f"áudio={total:.2f}s. Ativando fallback seguro."
        )
    else:
        print(f"AVISO xfade falhou. Ativando fallback seguro. {detail}")

    ok, fallback_detail = assemble_hard_cut(scene_files, logical_durations, total)
    if not ok:
        fail(f"fallback de montagem também falhou: {fallback_detail}")
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 100_000:
        fail("fallback não criou video_sem_audio válido")
    produced = duration(OUTPUT)
    if abs(produced - total) > max(0.35, 3 / FPS):
        fail(f"fallback com duração divergente: vídeo={produced:.2f}s áudio={total:.2f}s")
    print(f"ASSEMBLY MODE: SAFE_HARD_CUT ({produced:.2f}s)")
    return [0.0] * len(transitions), "SAFE_HARD_CUT", timing_report


def main() -> int:
    if not AUDIO.is_file():
        fail("áudio ausente")
    if not PRO_PLAN.is_file():
        fail("professional edit plan ausente")

    media = collect_media()
    secondary = secondary_media()
    map_scenes = valid_scene_list(read_json(SCENE_MAP, "scene_map"), "scene_map")
    pro_data = read_json(PRO_PLAN, "pro_edit_plan")
    pro_scenes = valid_scene_list(pro_data, "pro_edit_plan")
    total = duration(AUDIO)
    durations, sync_mode = allocate_durations(map_scenes, pro_scenes, total)
    if abs(sum(durations) - total) > 0.05:
        fail("durações não fecham com o áudio")

    print("\n================================")
    print("PROFESSIONAL MULTI-BEAT ASSEMBLER 2.1")
    print("================================")
    print(
        f"ID: {SHORT_ID} | Cenas: {len(media)}/{EXPECTED} | "
        f"Duração: {total:.2f}s | sync={sync_mode}"
    )

    rendered: list[Path] = []
    beat_report: list[dict[str, Any]] = []
    for index, (path, logical, pro) in enumerate(zip(media, durations, pro_scenes), 1):
        trans = 0.0 if index == EXPECTED else transition_duration(pro)
        sec = secondary.get(index)
        print(
            f"{index:02d}/{EXPECTED} {path.name} {logical:.2f}s "
            f"pace={pro.get('pace_multiplier')} cut={pro.get('cut_style')} "
            f"secondary={'YES' if sec else 'NO'}"
        )
        scene_file, beat_info = render_scene(path, index, logical, pro, trans, sec)
        rendered.append(scene_file)
        beat_report.append(beat_info)

    print("\nMontando ritmo profissional...")
    transitions, assembly_mode, scene_timing = assemble(rendered, durations, pro_scenes, total)

    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 100_000:
        fail("video_sem_audio não foi criado")
    final_duration = duration(OUTPUT)
    if abs(final_duration - total) > max(0.75, 2 / FPS):
        fail(f"duração divergente: vídeo={final_duration:.2f}s áudio={total:.2f}s")

    runtime = {
        "short_id": SHORT_ID,
        "version": "PRO_ASSEMBLER_2.1",
        "sync_mode": sync_mode,
        "assembly_mode": assembly_mode,
        "total_duration": round(total, 3),
        "final_duration": round(final_duration, 3),
        "durations": [round(x, 3) for x in durations],
        "transitions": [round(x, 3) for x in transitions],
        "transition_policy": "normalized_pts_with_safe_fallback",
        "scene_timing": scene_timing,
        "multi_asset": {
            "real_secondary_scenes": sum(1 for x in beat_report if x["source_asset_count"] == 2),
            "detail_fallback_scenes": sum(1 for x in beat_report if x["fallback_detail_crop"]),
            "beats": beat_report,
        },
        "output": str(OUTPUT),
        "status": "PASS",
    }
    atomic_json(RUNTIME_REPORT, runtime)
    print("\nPROFESSIONAL MULTI-BEAT ASSEMBLER: PASS")
    print(f"Arquivo: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

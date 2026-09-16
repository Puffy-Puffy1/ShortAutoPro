#!/usr/bin/env python3
"""Professional multi-beat scene assembler for ShortAutoPro 3.0.

Consumes the professional edit plan plus the bounded multi-asset plan. Important
long scenes can use a real secondary documentary asset; otherwise a conservative
detail beat can be made from the same photo. The report distinguishes those two
cases so a crop is never presented as an independent source.
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
    try: value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except (TypeError, ValueError): value = 12
    return max(6, min(20, value))


EXPECTED = expected_scenes()
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
SECONDARY_DIR = BASE / "imagens" / f"short_{SHORT_ID}_secondary"
AUDIO = BASE / "audios" / f"short_{SHORT_ID}.mp3"
ASS = BASE / "videos" / f"short_{SHORT_ID}.ass"
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
PRO_PLAN = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"
MULTI_PLAN = BASE / "roteiros" / f"multi_asset_{SHORT_ID}.json"
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
    try: value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError): value = default
    return max(low, min(high, value))


SCENE_TIMEOUT = timeout_value("SHORT_SCENE_RENDER_TIMEOUT", 300, 60, 1200)
ASSEMBLY_TIMEOUT = timeout_value("SHORT_ASSEMBLY_TIMEOUT", 900, 120, 2400)


def fail(message: str) -> None:
    raise SystemExit(f"ERRO PROFESSIONAL VIDEO: {message}")


def read_json(path: Path, label: str, optional: bool = False) -> dict[str, Any]:
    if optional and not path.is_file(): return {}
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: fail(f"{label} inválido: {exc}")
    if not isinstance(data, dict): fail(f"{label} precisa ser objeto JSON")
    return data


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise


def duration(path: Path) -> float:
    try:
        raw = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True, stderr=subprocess.DEVNULL, timeout=45).strip()
        value = float(raw)
    except Exception as exc: fail(f"não foi possível ler duração de {path}: {exc}")
    if not math.isfinite(value) or value <= 0: fail(f"duração inválida: {path}")
    return value


def scene_number(path: Path) -> int | None:
    match = re.match(r"^scene_(\d+)", path.name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def collect_media() -> list[Path]:
    if not MEDIA_DIR.is_dir(): fail(f"pasta de mídia ausente: {MEDIA_DIR}")
    by_scene: dict[int, Path] = {}
    for raw in glob.glob(str(MEDIA_DIR / "scene_*")):
        path = Path(raw)
        if path.suffix.lower() not in MEDIA_EXTS: continue
        number = scene_number(path)
        if number is None or not 1 <= number <= EXPECTED: fail(f"número de cena inválido: {path.name}")
        if number in by_scene: fail(f"mídia ambígua para cena {number:02d}")
        by_scene[number] = path
    missing = [n for n in range(1, EXPECTED + 1) if n not in by_scene]
    if missing: fail("mídia ausente: " + ", ".join(f"{x:02d}" for x in missing))
    return [by_scene[x] for x in range(1, EXPECTED + 1)]


def secondary_media() -> dict[int, Path]:
    data = read_json(MULTI_PLAN, "multi_asset", optional=True)
    assets = data.get("secondary_assets", []) if isinstance(data.get("secondary_assets"), list) else []
    result: dict[int, Path] = {}
    for item in assets:
        if not isinstance(item, dict): continue
        try: number = int(item.get("scene"))
        except (TypeError, ValueError): continue
        path = Path(str(item.get("asset", ""))).expanduser()
        if path.is_file() and path.suffix.lower() in MEDIA_EXTS and 1 <= number <= EXPECTED:
            result[number] = path
    return result


def valid_scene_list(data: dict[str, Any], label: str) -> list[dict[str, Any]]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != EXPECTED: fail(f"{label} precisa ter {EXPECTED} cenas")
    result = []
    for idx, item in enumerate(scenes, 1):
        if not isinstance(item, dict) or int(item.get("scene", 0) or 0) != idx: fail(f"{label} cena {idx} inválida")
        result.append(item)
    return result


def ass_time(value: str) -> float | None:
    try:
        h, m, rest = value.split(":"); sec, cent = rest.split(".")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(cent) / 100.0
    except Exception: return None


def caption_starts() -> list[float]:
    if not ASS.is_file(): return []
    starts = []
    try:
        for line in ASS.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.startswith("Dialogue:"): continue
            parts = line.split(",", 9)
            if len(parts) != 10: continue
            start, end = ass_time(parts[1].strip()), ass_time(parts[2].strip())
            if start is not None and end is not None and end > start: starts.append(start)
    except Exception: return []
    return sorted(set(starts))


def words(text: Any) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", str(text or ""), flags=re.UNICODE))


def normalize_durations(raw: list[float], total: float, minimum: float = 1.0) -> list[float]:
    n = len(raw)
    if n == 0: return []
    if total < minimum * n: return [total / n] * n
    values = [max(0.01, float(x)) for x in raw]; result = [0.0] * n; remaining = set(range(n)); remaining_total = total
    while remaining:
        weight_sum = sum(values[i] for i in remaining); provisional = {i: remaining_total * values[i] / weight_sum for i in remaining}; below = [i for i, value in provisional.items() if value < minimum]
        if not below:
            for i, value in provisional.items(): result[i] = value
            break
        for i in below:
            result[i] = minimum; remaining_total -= minimum; remaining.remove(i)
    if result: result[-1] += total - sum(result)
    return result


def allocate_durations(scene_map: list[dict[str, Any]], pro_scenes: list[dict[str, Any]], total: float) -> tuple[list[float], str]:
    weights = []
    for scene, pro in zip(scene_map, pro_scenes):
        try: base_words = int(scene.get("words", 0) or 0)
        except (TypeError, ValueError): base_words = 0
        base_words = base_words or words(scene.get("segment")) or 1
        try: pace = float(pro.get("pace_multiplier", 1.0))
        except (TypeError, ValueError): pace = 1.0
        weights.append(max(0.2, base_words * max(0.78, min(1.14, pace))))
    starts = caption_starts()
    if len(starts) >= EXPECTED:
        boundaries = [0.0]; total_weight = sum(weights); cumulative = 0.0
        for i in range(EXPECTED - 1):
            cumulative += weights[i]; ratio = cumulative / total_weight; index = max(1, min(round(ratio * (len(starts) - 1)), len(starts) - 1)); boundaries.append(min(max(boundaries[-1] + 0.05, starts[index]), total))
        boundaries.append(total); raw = [max(0.01, boundaries[i + 1] - boundaries[i]) for i in range(EXPECTED)]
        return normalize_durations(raw, total), "PRO_CAPTION_SEMANTIC"
    return normalize_durations(weights, total), "PRO_SCRIPT_WEIGHT"


def safe_float(value: Any, default: float, low: float, high: float) -> float:
    try: number = float(value)
    except (TypeError, ValueError, OverflowError): number = default
    if not math.isfinite(number): number = default
    return max(low, min(high, number))


def render_beat(path: Path, output: Path, beat_duration: float, pro: dict[str, Any], beat_index: int, total_beats: int) -> None:
    frames = max(1, round(beat_duration * FPS)); ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        start = safe_float(pro.get("zoom_start"), 1.0, 1.0, 1.08); end = safe_float(pro.get("zoom_end"), start, start, 1.10)
        if beat_index > 0:
            # Detail/parallax-like second beat: subtle extra crop, opposite drift.
            start = min(1.075, max(start + 0.010, end)); end = min(1.095, start + 0.012)
        delta = max(0.0, end - start); denom = max(frames - 1, 1); p = f"(on/{denom})"; smooth = f"(3*pow({p},2)-2*pow({p},3))"; zoom = f"{start:.6f}+{delta:.6f}*{smooth}"
        pan = str(pro.get("pan", "center")).strip().lower()
        if beat_index > 0 and pan in {"left", "right"}: pan = "right" if pan == "left" else "left"
        travel = "(iw-iw/zoom)"; x = f"{travel}*{smooth}" if pan == "right" else f"{travel}*(1-{smooth})" if pan == "left" else f"{travel}/2"; y = "(ih-ih/zoom)/2"
        vf = "scale=1200:2133:force_original_aspect_ratio=increase,crop=1200:2133," + f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps={FPS},setsar=1,format=yuv420p"
        command = ["ffmpeg", "-y", "-loop", "1", "-i", str(path), "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p", str(output)]
    elif ext in VIDEO_EXTS:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p"
        command = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(path), "-t", f"{beat_duration:.6f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p", str(output)]
    else: fail(f"extensão não suportada: {ext}")
    try: subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=SCENE_TIMEOUT)
    except subprocess.TimeoutExpired: fail(f"render do beat excedeu {SCENE_TIMEOUT}s")
    except subprocess.CalledProcessError as exc: fail(f"FFmpeg falhou em beat: {exc.returncode}")
    if not output.is_file() or output.stat().st_size <= 0: fail(f"beat vazio: {output.name}")


def join_two_beats(first: Path, second: Path, output: Path, first_duration: float, transition: float, total: float) -> None:
    offset = max(0.01, first_duration - transition)
    cmd = ["ffmpeg", "-y", "-i", str(first), "-i", str(second), "-filter_complex", f"[0:v][1:v]xfade=transition=fade:duration={transition:.6f}:offset={offset:.6f}[v]", "-map", "[v]", "-t", f"{total:.6f}", "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p", str(output)]
    try: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=SCENE_TIMEOUT)
    except Exception as exc: fail(f"montagem multi-beat falhou: {exc}")


def render_scene(path: Path, number: int, logical: float, pro: dict[str, Any], transition_after: float, secondary: Path | None) -> tuple[Path, dict[str, Any]]:
    TEMP.mkdir(parents=True, exist_ok=True); output = TEMP / f"pro_scene_{number:02d}.mp4"; output.unlink(missing_ok=True)
    render_duration = logical + (transition_after if number < EXPECTED else 0.0)
    role = str(pro.get("narrative_role", "")).lower(); allow_detail = os.getenv("SAP_MULTI_BEAT_FALLBACK", "1") == "1"
    fallback_detail = secondary is None and allow_detail and path.suffix.lower() in IMAGE_EXTS and render_duration >= 3.6 and role in {"hook", "evidence", "development", "escalation", "reveal", "turn", "turning_point", "climax", "payoff"}
    second = secondary if secondary is not None else path if fallback_detail else None
    if second is None:
        render_beat(path, output, render_duration, pro, 0, 1)
        return output, {"scene": number, "visual_beats": 1, "source_asset_count": 1, "secondary_asset": None, "fallback_detail_crop": False}

    internal_transition = max(1 / FPS, min(0.075, render_duration * 0.03)); first_duration = render_duration * 0.58 + internal_transition / 2; second_duration = render_duration * 0.42 + internal_transition / 2
    beat1, beat2 = TEMP / f"pro_scene_{number:02d}_beat_a.mp4", TEMP / f"pro_scene_{number:02d}_beat_b.mp4"
    render_beat(path, beat1, first_duration, pro, 0, 2); render_beat(second, beat2, second_duration, pro, 1, 2); join_two_beats(beat1, beat2, output, first_duration, internal_transition, render_duration)
    return output, {"scene": number, "visual_beats": 2, "source_asset_count": 2 if secondary is not None else 1, "secondary_asset": str(secondary) if secondary is not None else None, "fallback_detail_crop": fallback_detail, "internal_transition": round(internal_transition, 3)}


def transition_duration(pro: dict[str, Any]) -> float:
    cut_style = str(pro.get("cut_style", "editorial_cut"))
    configured = safe_float(pro.get("transition_duration"), 0.075, 0.0, 0.18)
    if cut_style == "near_cut": return max(1 / FPS, min(configured, 0.045))
    if cut_style in {"soft_fade", "closing_hold"}: return max(0.09, configured)
    return max(2 / FPS, min(configured, 0.095))


def assemble(scene_files: list[Path], logical_durations: list[float], pro_scenes: list[dict[str, Any]], total: float) -> list[float]:
    OUTPUT.unlink(missing_ok=True); command = ["ffmpeg", "-y"]
    for scene in scene_files: command.extend(["-i", str(scene)])
    filters = []; accumulated = logical_durations[0]; transitions = [0.0 if i == EXPECTED - 1 else transition_duration(scene) for i, scene in enumerate(pro_scenes)]
    first = transitions[0]; filters.append(f"[0:v][1:v]xfade=transition=fade:duration={first:.6f}:offset={accumulated:.6f}[v1]")
    for i in range(2, len(scene_files)):
        accumulated += logical_durations[i - 1]; trans = transitions[i - 1]; filters.append(f"[v{i-1}][{i}:v]xfade=transition=fade:duration={trans:.6f}:offset={accumulated:.6f}[v{i}]")
    command.extend(["-filter_complex", ";".join(filters), "-map", f"[v{len(scene_files)-1}]", "-t", f"{total:.6f}", "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT)])
    try: subprocess.run(command, check=True, timeout=ASSEMBLY_TIMEOUT)
    except subprocess.TimeoutExpired: fail(f"montagem excedeu {ASSEMBLY_TIMEOUT}s")
    except subprocess.CalledProcessError as exc: fail(f"FFmpeg falhou na montagem: {exc.returncode}")
    return transitions


def main() -> int:
    if not AUDIO.is_file(): fail("áudio ausente")
    if not PRO_PLAN.is_file(): fail("professional edit plan ausente")
    media = collect_media(); secondary = secondary_media(); map_scenes = valid_scene_list(read_json(SCENE_MAP, "scene_map"), "scene_map"); pro_data = read_json(PRO_PLAN, "pro_edit_plan"); pro_scenes = valid_scene_list(pro_data, "pro_edit_plan"); total = duration(AUDIO); durations, sync_mode = allocate_durations(map_scenes, pro_scenes, total)
    if abs(sum(durations) - total) > 0.05: fail("durações não fecham com o áudio")
    print("\n================================\nPROFESSIONAL MULTI-BEAT ASSEMBLER 2.0\n================================")
    print(f"ID: {SHORT_ID} | Cenas: {len(media)}/{EXPECTED} | Duração: {total:.2f}s | sync={sync_mode}")
    rendered=[]; beat_report=[]
    for index, (path, logical, pro) in enumerate(zip(media, durations, pro_scenes), 1):
        trans = 0.0 if index == EXPECTED else transition_duration(pro); sec = secondary.get(index)
        print(f"{index:02d}/{EXPECTED} {path.name} {logical:.2f}s pace={pro.get('pace_multiplier')} cut={pro.get('cut_style')} secondary={'YES' if sec else 'NO'}")
        scene_file, beat_info = render_scene(path, index, logical, pro, trans, sec); rendered.append(scene_file); beat_report.append(beat_info)
    print("\nMontando ritmo profissional..."); transitions = assemble(rendered, durations, pro_scenes, total)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 100_000: fail("video_sem_audio não foi criado")
    final_duration = duration(OUTPUT)
    if abs(final_duration - total) > max(0.75, 2 / FPS): fail(f"duração divergente: vídeo={final_duration:.2f}s áudio={total:.2f}s")
    runtime = {"short_id": SHORT_ID, "version": "PRO_ASSEMBLER_2.0", "sync_mode": sync_mode, "total_duration": round(total, 3), "final_duration": round(final_duration, 3), "durations": [round(x, 3) for x in durations], "transitions": [round(x, 3) for x in transitions], "transition_policy": "narrative_cut_style", "multi_asset": {"real_secondary_scenes": sum(1 for x in beat_report if x["source_asset_count"] == 2), "detail_fallback_scenes": sum(1 for x in beat_report if x["fallback_detail_crop"]), "beats": beat_report}, "output": str(OUTPUT), "status": "PASS"}
    atomic_json(RUNTIME_REPORT, runtime); print(f"\nPROFESSIONAL MULTI-BEAT ASSEMBLER: PASS\nArquivo: {OUTPUT}"); return 0


if __name__ == "__main__": raise SystemExit(main())

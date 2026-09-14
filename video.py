#!/usr/bin/env python3

import glob
import json
import math
import os
import re
import subprocess
import sys
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

MEDIA_DIR = os.path.join(BASE, "imagens", f"short_{SHORT_ID}")
AUDIO = os.path.join(BASE, "audios", f"short_{SHORT_ID}.mp3")
ASS = os.path.join(BASE, "videos", f"short_{SHORT_ID}.ass")
SCENE_MAP = os.path.join(BASE, "roteiros", f"scene_map_{SHORT_ID}.json")
MOTION_PLAN = os.path.join(BASE, "roteiros", f"motion_plan_{SHORT_ID}.json")
TEMP = os.path.join(BASE, "temp", SHORT_ID)
VIDEO_DIR = os.path.join(BASE, "videos")
VIDEO_SEM_AUDIO = os.path.join(TEMP, "video_sem_audio.mp4")

os.makedirs(TEMP, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

FPS = 30
TRANSICAO = 0.25
PRESET = os.getenv("SHORT_PRESET_CENAS", "veryfast")
CRF_CENAS = os.getenv("SHORT_CRF_CENAS", "23")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS


def fail(msg):
    raise SystemExit(f"ERRO: {msg}")


def ffprobe_duration(path):
    try:
        value = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).strip()
        duration = float(value)
    except Exception as exc:
        fail(f"não foi possível ler duração de {path}: {exc}")
    if not math.isfinite(duration) or duration <= 0:
        fail(f"duração inválida para {path}")
    return duration


def load_json(path, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        fail(f"{label} inválido: {exc}")
    if not isinstance(data, dict):
        fail(f"{label} não é objeto JSON")
    return data


def scene_number_from_path(path):
    m = re.match(r"^scene_(\d+)", os.path.basename(path), flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def collect_media():
    if not os.path.isdir(MEDIA_DIR):
        fail("pasta de mídia não encontrada")

    by_scene = {}
    ignored = []
    for path in glob.glob(os.path.join(MEDIA_DIR, "scene_*")):
        ext = os.path.splitext(path)[1].lower()
        if ext not in MEDIA_EXTS:
            ignored.append(os.path.basename(path))
            continue
        number = scene_number_from_path(path)
        if number is None or not 1 <= number <= QTD_CENAS:
            fail(f"mídia com número de cena inválido: {os.path.basename(path)}")
        if number in by_scene:
            fail(
                f"mais de uma mídia para a cena {number:02d}: "
                f"{os.path.basename(by_scene[number])} e {os.path.basename(path)}"
            )
        by_scene[number] = path

    missing = [n for n in range(1, QTD_CENAS + 1) if n not in by_scene]
    if missing:
        fail("mídias ausentes: " + ", ".join(f"{n:02d}" for n in missing))

    if len(by_scene) != QTD_CENAS:
        fail(f"quantidade de mídias inválida: {len(by_scene)}/{QTD_CENAS}")

    return [by_scene[n] for n in range(1, QTD_CENAS + 1)], ignored


def ass_para_segundos(value):
    try:
        h, m, rest = value.split(":")
        sec, cent = rest.split(".")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(cent) / 100.0
    except Exception:
        return None


def ass_event_starts():
    if not os.path.isfile(ASS):
        return []
    starts = []
    try:
        with open(ASS, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("Dialogue:"):
                    continue
                parts = line.split(",", 9)
                if len(parts) != 10:
                    continue
                start = ass_para_segundos(parts[1].strip())
                end = ass_para_segundos(parts[2].strip())
                if start is None or end is None or end <= start:
                    continue
                starts.append(start)
    except Exception:
        return []
    return sorted(set(starts))


def load_scene_map():
    if not os.path.isfile(SCENE_MAP):
        fail("scene_map não encontrado")
    data = load_json(SCENE_MAP, "scene_map")
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != QTD_CENAS:
        fail(f"scene_map precisa ter {QTD_CENAS} cenas")
    if not all(isinstance(x, dict) for x in scenes):
        fail("scene_map contém cena inválida")
    for expected, scene in enumerate(scenes, start=1):
        try:
            number = int(scene.get("scene"))
        except (TypeError, ValueError):
            fail(f"cena {expected} sem numeração válida")
        if number != expected:
            fail(f"numeração de cenas inválida: esperado {expected}, recebido {number}")
    return scenes


def scene_weights(scenes):
    weights = []
    for scene in scenes:
        try:
            weight = int(scene.get("words", 0) or 0)
        except (TypeError, ValueError):
            weight = 0
        if weight <= 0:
            segment = str(scene.get("segment", ""))
            weight = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", segment, flags=re.UNICODE))
        weights.append(max(1, weight))
    return weights


def normalize_durations(values, total, minimum=0.65):
    n = len(values)
    if n == 0:
        return []
    if total <= 0:
        fail("duração total inválida")

    # Se o áudio for curto demais para o piso, distribui uniformemente.
    if total < minimum * n:
        return [total / n] * n

    values = [max(0.0, float(x)) for x in values]
    if sum(values) <= 0:
        values = [1.0] * n

    result = [0.0] * n
    remaining_total = total
    remaining = set(range(n))
    raw = values[:]

    # Water-filling: fixa itens abaixo do piso e redistribui o restante.
    while remaining:
        raw_sum = sum(raw[i] for i in remaining)
        if raw_sum <= 0:
            each = remaining_total / len(remaining)
            for i in remaining:
                result[i] = each
            break

        provisional = {
            i: remaining_total * raw[i] / raw_sum
            for i in remaining
        }
        below = [i for i, value in provisional.items() if value < minimum]
        if not below:
            for i, value in provisional.items():
                result[i] = value
            break

        for i in below:
            result[i] = minimum
            remaining_total -= minimum
            remaining.remove(i)

    # Corrige apenas arredondamento acumulado.
    diff = total - sum(result)
    if result:
        result[-1] += diff
    return result


def calculate_durations(scenes, total):
    weights = scene_weights(scenes)
    starts = ass_event_starts()

    if len(starts) >= QTD_CENAS:
        boundaries = [0.0]
        total_weight = sum(weights)
        cumulative = 0
        for i in range(QTD_CENAS - 1):
            cumulative += weights[i]
            ratio = cumulative / total_weight
            index = round(ratio * (len(starts) - 1))
            index = max(1, min(index, len(starts) - 1))
            t = max(0.0, min(starts[index], total))
            if t <= boundaries[-1]:
                t = boundaries[-1] + 0.05
            boundaries.append(min(t, total))
        boundaries.append(total)
        raw = [max(0.0, boundaries[i + 1] - boundaries[i]) for i in range(QTD_CENAS)]
        return normalize_durations(raw, total), "SEMANTICA V6.4"

    raw = [total * w / sum(weights) for w in weights]
    return normalize_durations(raw, total), "PESO DO ROTEIRO V6.4"


def safe_float(value, default, low, high):
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    if not math.isfinite(result):
        result = default
    return max(low, min(result, high))


def load_motion_plan():
    if not os.path.isfile(MOTION_PLAN):
        return {}
    try:
        data = load_json(MOTION_PLAN, "motion_plan")
    except SystemExit:
        return {}
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list):
        return {}
    result = {}
    for item in scenes:
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("scene"))
        except (TypeError, ValueError):
            continue
        if 1 <= number <= QTD_CENAS and number not in result:
            result[number] = item
    return result


def motion_for_scene(motion, number):
    cfg = motion.get(number, {})
    if not isinstance(cfg, dict):
        cfg = {}
    start = safe_float(cfg.get("zoom_start", 1.0), 1.0, 1.0, 1.15)
    end = safe_float(cfg.get("zoom_end", 1.08), 1.08, start, 1.20)
    pan = str(cfg.get("pan", "center")).strip().lower()
    if pan not in {"left", "right", "center", "none"}:
        pan = "center"
    if pan == "none":
        pan = "center"
    return {
        "motion_profile": str(cfg.get("motion_profile", "legacy")),
        "zoom_start": start,
        "zoom_end": end,
        "pan": pan,
    }


def execute_scene_command(command, scene_number):
    # Mantém as pontes VI6/VI7 existentes, sem torná-las obrigatórias.
    try:
        from vi6_47_renderer_switch import adapt_scene_command
        command = adapt_scene_command(
            command,
            {"source": "video.py", "stage": "SCENE_RENDER_PRIMARY"},
        )
    except Exception as bridge_exc:
        try:
            from vi6_48_emergency_rollback import trip
            trip("scene_command_bridge:" + type(bridge_exc).__name__)
        except Exception:
            pass

    try:
        if os.getenv("VI700_CANARY_MODE", "OFF").upper() == "ON":
            try:
                from vi6_95_scene_executor import execute
                execute(
                    command,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except ImportError:
                pass

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"FFmpeg falhou renderizando cena {scene_number:02d} (código {exc.returncode})")


def render_scene(path, number, logical_duration, motion_cfg):
    ext = os.path.splitext(path)[1].lower()
    render_duration = logical_duration + TRANSICAO
    frames = max(1, round(render_duration * FPS))
    output = os.path.join(TEMP, f"v64_cena_{number:02d}.mp4")

    if ext in IMAGE_EXTS:
        start = motion_cfg["zoom_start"]
        end = motion_cfg["zoom_end"]
        delta = max(0.0, end - start)
        step = delta / max(frames - 1, 1)
        zoom = f"if(eq(on,0),{start:.6f},min(zoom+{step:.8f},{end:.6f}))"

        pan = motion_cfg["pan"]
        if pan == "left":
            x = f"(iw-iw/zoom)*(1-on/{max(frames - 1, 1)})"
        elif pan == "right":
            x = f"(iw-iw/zoom)*(on/{max(frames - 1, 1)})"
        else:
            x = "(iw-iw/zoom)/2"
        y = "(ih-ih/zoom)/2"

        vf = (
            "scale=1200:2133:force_original_aspect_ratio=increase,"
            "crop=1200:2133,"
            f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s=1080x1920:fps={FPS},"
            "setsar=1,format=yuv420p"
        )
        command = [
            "ffmpeg", "-y", "-loop", "1", "-i", path,
            "-vf", vf, "-frames:v", str(frames), "-an",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF_CENAS,
            "-pix_fmt", "yuv420p", output,
        ]
    elif ext in VIDEO_EXTS:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,fps={FPS},setsar=1,format=yuv420p"
        )
        command = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", path,
            "-t", f"{render_duration:.6f}", "-vf", vf, "-an",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF_CENAS,
            "-pix_fmt", "yuv420p", output,
        ]
    else:
        fail(f"extensão de mídia não suportada: {ext}")

    execute_scene_command(command, number)
    if not os.path.isfile(output) or os.path.getsize(output) <= 0:
        fail(f"render da cena {number:02d} não foi criado")
    return output


def assemble_crossfade(scene_files, durations, total):
    if len(scene_files) != QTD_CENAS:
        fail("quantidade de cenas renderizadas diferente do esperado")

    if len(scene_files) == 1:
        command = [
            "ffmpeg", "-y", "-i", scene_files[0], "-t", f"{total:.6f}",
            "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", CRF_CENAS,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", VIDEO_SEM_AUDIO,
        ]
    else:
        command = ["ffmpeg", "-y"]
        for scene in scene_files:
            command.extend(["-i", scene])

        filters = []
        accumulated = durations[0]
        filters.append(
            f"[0:v][1:v]xfade=transition=fade:duration={TRANSICAO}:"
            f"offset={accumulated:.6f}[v1]"
        )
        for i in range(2, len(scene_files)):
            accumulated += durations[i - 1]
            filters.append(
                f"[v{i-1}][{i}:v]xfade=transition=fade:duration={TRANSICAO}:"
                f"offset={accumulated:.6f}[v{i}]"
            )

        command.extend([
            "-filter_complex", ";".join(filters),
            "-map", f"[v{len(scene_files)-1}]",
            "-t", f"{total:.6f}", "-an",
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF_CENAS,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", VIDEO_SEM_AUDIO,
        ])

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        fail(f"FFmpeg falhou ao montar crossfade (código {exc.returncode})")


if not os.path.isfile(AUDIO):
    fail("áudio não encontrado")

arquivos, ignorados = collect_media()
scenes = load_scene_map()
duracao_total = ffprobe_duration(AUDIO)
duracoes_cena, modo_sync = calculate_durations(scenes, duracao_total)

if len(duracoes_cena) != QTD_CENAS or abs(sum(duracoes_cena) - duracao_total) > 0.05:
    fail("distribuição de duração das cenas ficou inconsistente")

motion = load_motion_plan()

print()
print("================================")
print("VIDEO V6.4 - SCENE ASSEMBLER")
print("================================")
print(f"Mídias: {len(arquivos)}/{QTD_CENAS}")
print(f"Duração total: {duracao_total:.2f}s")
print(f"Sincronização: {modo_sync}")
print(f"Motion Plan: {len(motion)}/{QTD_CENAS}")
if ignorados:
    print("Arquivos ignorados por extensão: " + ", ".join(sorted(ignorados)))
print()

rendered = []
for index, (path, duration) in enumerate(zip(arquivos, duracoes_cena), start=1):
    cfg = motion_for_scene(motion, index)
    print(
        f"Render {index}/{QTD_CENAS}: {os.path.basename(path)} "
        f"{duration:.2f}s | {cfg['motion_profile']}"
    )
    rendered.append(render_scene(path, index, duration, cfg))

print()
print("Aplicando transições semânticas...")
assemble_crossfade(rendered, duracoes_cena, duracao_total)

if not os.path.isfile(VIDEO_SEM_AUDIO) or os.path.getsize(VIDEO_SEM_AUDIO) <= 0:
    fail("vídeo sem áudio não foi criado")

dur_final = ffprobe_duration(VIDEO_SEM_AUDIO)
if abs(dur_final - duracao_total) > max(0.75, 2 / FPS):
    fail(
        f"duração do vídeo sem áudio diverge do áudio: "
        f"vídeo={dur_final:.2f}s áudio={duracao_total:.2f}s"
    )

print()
print("================================")
print("VIDEO V6.4 PRONTO!")
print("================================")
print(f"Sincronização: {modo_sync}")
print(f"Duração: {dur_final:.2f}s")
print(f"Arquivo: {VIDEO_SEM_AUDIO}")
print()

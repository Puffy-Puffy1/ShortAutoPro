#!/usr/bin/env python3

import glob
import json
import os
import subprocess
from datetime import date, datetime

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

MANIFEST_DIR = os.path.join(BASE, "manifests")
os.makedirs(MANIFEST_DIR, exist_ok=True)
SAIDA = os.path.join(MANIFEST_DIR, f"{SHORT_ID}.json")

TOPIC = os.path.join(BASE, "roteiros", f"used_topic_{SHORT_ID}.txt")
TOPIC_FALLBACK = os.path.join(BASE, "roteiros", f"topic_{SHORT_ID}.txt")
HOOK = os.path.join(BASE, "roteiros", f"hook_{SHORT_ID}.txt")
ROTEIRO = os.path.join(BASE, "roteiros", f"short_{SHORT_ID}.txt")
FONTE = os.path.join(BASE, "roteiros", f"fonte_{SHORT_ID}.txt")
SCENE_MAP = os.path.join(BASE, "roteiros", f"scene_map_{SHORT_ID}.json")
PUBLISH = os.path.join(BASE, "roteiros", f"publish_{SHORT_ID}.json")
VIDEO_V6 = os.path.join(BASE, "videos", f"short_v6_{SHORT_ID}.mp4")
VIDEO_V5 = os.path.join(BASE, "videos", f"short_v5_{SHORT_ID}.mp4")
LOG = os.path.join(BASE, "logs", "producao", f"short_{SHORT_ID}.log")


def ler_txt(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def ler_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def ffprobe(path):
    if not path or not os.path.exists(path):
        return {}
    try:
        saida = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", path,
            ],
            text=True,
            timeout=60,
        )
        dados = json.loads(saida)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


assunto = ler_txt(TOPIC) or ler_txt(TOPIC_FALLBACK)
publish = ler_json(PUBLISH)
scene_map = ler_json(SCENE_MAP)
scenes = scene_map.get("scenes", [])
if not isinstance(scenes, list):
    scenes = []
scenes = [x for x in scenes if isinstance(x, dict)]

if os.path.exists(VIDEO_V6):
    video = VIDEO_V6
    video_version = "V6"
elif os.path.exists(VIDEO_V5):
    video = VIDEO_V5
    video_version = "V5"
else:
    video = ""
    video_version = ""

video_info = ffprobe(video)
formato = video_info.get("format", {})
streams = video_info.get("streams", [])
if not isinstance(formato, dict):
    formato = {}
if not isinstance(streams, list):
    streams = []

try:
    duracao = float(formato.get("duration", 0) or 0)
except Exception:
    duracao = None

width = None
height = None
fps = None
codec_video = None
codec_audio = None

for stream in streams:
    if not isinstance(stream, dict):
        continue
    tipo = stream.get("codec_type")
    if tipo == "video" and codec_video is None:
        codec_video = stream.get("codec_name")
        width = stream.get("width")
        height = stream.get("height")
        fps_raw = str(stream.get("avg_frame_rate", "0/1"))
        try:
            num, den = fps_raw.split("/", 1)
            den_float = float(den)
            fps = float(num) / den_float if den_float else 0.0
        except Exception:
            fps = None
    elif tipo == "audio" and codec_audio is None:
        codec_audio = stream.get("codec_name")

MEDIA_DIR = os.path.join(BASE, "imagens", f"short_{SHORT_ID}")
permitidas = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
cenas_fisicas = []
if os.path.isdir(MEDIA_DIR):
    cenas_fisicas = [
        x
        for x in glob.glob(os.path.join(MEDIA_DIR, "scene_*"))
        if os.path.splitext(x)[1].lower() in permitidas
    ]
cenas_fisicas.sort()

quality = {
    "video_exists": bool(video and os.path.isfile(video)),
    "expected_scene_count": QTD_CENAS,
    "scene_map_count": len(scenes),
    "physical_scene_count": len(cenas_fisicas),
    "resolution_ok": width == 1080 and height == 1920,
    "fps_ok": fps is not None and 29 <= fps <= 31,
    "audio_exists": codec_audio is not None,
}

quality_pass = all([
    quality["video_exists"],
    quality["resolution_ok"],
    quality["fps_ok"],
    quality["audio_exists"],
    quality["scene_map_count"] == QTD_CENAS,
    quality["physical_scene_count"] == QTD_CENAS,
])

manifest = {
    "short_id": SHORT_ID,
    "created_at": datetime.now().isoformat(),
    "status": "QUALITY_PASS" if quality_pass else "INCOMPLETE",
    "topic": assunto,
    "hook": ler_txt(HOOK),
    "script": {
        "path": ROTEIRO,
        "text": ler_txt(ROTEIRO),
    },
    "source": {"path": FONTE},
    "publish": {
        "path": PUBLISH,
        "chosen_title": publish.get("chosen_title", ""),
        "titles": publish.get("titles", []),
        "description": publish.get("description", ""),
        "hashtags": publish.get("hashtags", []),
        "pinned_comment": publish.get("pinned_comment", ""),
    },
    "scenes": {
        "map_path": SCENE_MAP,
        "expected_count": QTD_CENAS,
        "count": len(scenes),
        "physical_count": len(cenas_fisicas),
        "items": scenes,
    },
    "video": {
        "path": video,
        "version": video_version,
        "duration_seconds": duracao,
        "width": width,
        "height": height,
        "fps": fps,
        "video_codec": codec_video,
        "audio_codec": codec_audio,
    },
    "quality": quality,
    "log": LOG,
}

temporario = SAIDA + ".tmp"
try:
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporario, SAIDA)
finally:
    if os.path.exists(temporario):
        try:
            os.remove(temporario)
        except OSError:
            pass

print()
print("================================")
print("PRODUCTION MANIFEST - 1.9")
print("================================")
print()
print(f"ID: {SHORT_ID}")
print(f"Status: {manifest['status']}")
print(f"Assunto: {assunto}")
print(f"Cenas: {len(cenas_fisicas)}/{QTD_CENAS}")
if video:
    if fps is not None:
        print(f"Vídeo: {width}x{height} {fps:.2f}fps")
    else:
        print("Vídeo encontrado, mas metadados incompletos")
print()
print(f"Manifest:\n{SAIDA}")
print()
print("PRODUCTION MANIFEST: OK")
print()

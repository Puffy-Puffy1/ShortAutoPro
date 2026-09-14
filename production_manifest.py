#!/usr/bin/env python3

import glob
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
MANIFEST_DIR = os.path.join(BASE, "manifests")
os.makedirs(MANIFEST_DIR, exist_ok=True)
SAIDA = os.path.join(MANIFEST_DIR, f"{SHORT_ID}.json")

TOPIC = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC_FALLBACK = os.path.join(R, f"topic_{SHORT_ID}.txt")
HOOK = os.path.join(R, f"hook_{SHORT_ID}.txt")
ROTEIRO = os.path.join(R, f"short_{SHORT_ID}.txt")
FONTE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
PUBLISH = os.path.join(R, f"publish_{SHORT_ID}.json")
PUBLISH_INTEGRITY = os.path.join(R, f"publish_integrity_{SHORT_ID}.json")
LEDGER = os.path.join(BASE, "credits", f"ledger_{SHORT_ID}.json")
VIDEO = os.path.join(BASE, "videos", f"short_v6_{SHORT_ID}.mp4")
LOG = os.path.join(BASE, "logs", "producao", f"short_{SHORT_ID}.log")


def ler_txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def ler_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def atomic_json(path, data):
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def ffprobe(path):
    if not os.path.isfile(path):
        return {}
    try:
        saida = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", path,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        dados = json.loads(saida)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def contar_palavras(texto):
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", str(texto), flags=re.UNICODE))


assunto = ler_txt(TOPIC) or ler_txt(TOPIC_FALLBACK)
hook = ler_txt(HOOK)
roteiro = ler_txt(ROTEIRO)
fonte = ler_txt(FONTE)
publish = ler_json(PUBLISH)
publish_integrity = ler_json(PUBLISH_INTEGRITY)
ledger = ler_json(LEDGER)
scene_map = ler_json(SCENE_MAP)

scenes = scene_map.get("scenes", [])
if not isinstance(scenes, list):
    scenes = []
scenes = [x for x in scenes if isinstance(x, dict)]

video_info = ffprobe(VIDEO)
formato = video_info.get("format", {})
streams = video_info.get("streams", [])
if not isinstance(formato, dict):
    formato = {}
if not isinstance(streams, list):
    streams = []

try:
    duracao = float(formato.get("duration", 0) or 0)
except (TypeError, ValueError):
    duracao = 0.0

width = 0
height = 0
fps = 0.0
codec_video = ""
codec_audio = ""

for stream in streams:
    if not isinstance(stream, dict):
        continue
    tipo = stream.get("codec_type")
    if tipo == "video" and not codec_video:
        codec_video = str(stream.get("codec_name", ""))
        width = int(stream.get("width", 0) or 0)
        height = int(stream.get("height", 0) or 0)
        fps_raw = str(stream.get("avg_frame_rate", "0/1"))
        try:
            num, den = fps_raw.split("/", 1)
            den_float = float(den)
            fps = float(num) / den_float if den_float else 0.0
        except (TypeError, ValueError, ZeroDivisionError):
            fps = 0.0
    elif tipo == "audio" and not codec_audio:
        codec_audio = str(stream.get("codec_name", ""))

MEDIA_DIR = os.path.join(BASE, "imagens", f"short_{SHORT_ID}")
permitidas = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
cenas_fisicas = []
if os.path.isdir(MEDIA_DIR):
    cenas_fisicas = sorted(
        x
        for x in glob.glob(os.path.join(MEDIA_DIR, "scene_*"))
        if os.path.splitext(x)[1].lower() in permitidas
    )

# Garante exatamente uma mídia por número de cena.
numeros = []
for path in cenas_fisicas:
    m = re.match(r"^scene_(\d+)", os.path.basename(path), flags=re.IGNORECASE)
    if m:
        numeros.append(int(m.group(1)))
esperados = set(range(1, QTD_CENAS + 1))
media_numbering_ok = (
    len(numeros) == QTD_CENAS
    and set(numeros) == esperados
    and len(set(numeros)) == len(numeros)
)

hashtags = publish.get("hashtags", [])
if not isinstance(hashtags, list):
    hashtags = []

quality = {
    "video_exists": os.path.isfile(VIDEO) and os.path.getsize(VIDEO) > 0,
    "v6_only": True,
    "expected_scene_count": QTD_CENAS,
    "scene_map_count": len(scenes),
    "physical_scene_count": len(cenas_fisicas),
    "media_numbering_ok": media_numbering_ok,
    "resolution_ok": width == 1080 and height == 1920,
    "fps_ok": 29.0 <= fps <= 31.0,
    "audio_exists": bool(codec_audio),
    "duration_ok": duracao >= 15.0,
    "topic_exists": bool(assunto),
    "script_exists": bool(roteiro) and 105 <= contar_palavras(roteiro) <= 125,
    "source_exists": bool(fonte),
    "publish_exists": bool(publish),
    "publish_title_exists": bool(str(publish.get("chosen_title", "")).strip()),
    "publish_description_exists": bool(str(publish.get("description", "")).strip()),
    "publish_hashtags_ok": len(hashtags) == 5,
    "publish_integrity_pass": publish_integrity.get("status") == "PASS",
    "source_ledger_exists": bool(ledger) and ledger.get("short_id") == SHORT_ID,
}

quality_pass = all(quality.values())

manifest = {
    "short_id": SHORT_ID,
    "created_at": datetime.now().isoformat(),
    "status": "QUALITY_PASS" if quality_pass else "INCOMPLETE",
    "topic": assunto,
    "hook": hook,
    "script": {"path": ROTEIRO, "text": roteiro},
    "source": {"path": FONTE},
    "publish": {
        "path": PUBLISH,
        "chosen_title": publish.get("chosen_title", ""),
        "titles": publish.get("titles", []),
        "description": publish.get("description", ""),
        "hashtags": hashtags,
        "pinned_comment": publish.get("pinned_comment", ""),
        "integrity_report": PUBLISH_INTEGRITY,
    },
    "source_ledger": LEDGER,
    "scenes": {
        "map_path": SCENE_MAP,
        "expected_count": QTD_CENAS,
        "count": len(scenes),
        "physical_count": len(cenas_fisicas),
        "items": scenes,
    },
    "video": {
        "path": VIDEO,
        "version": "V6",
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

atomic_json(SAIDA, manifest)

print()
print("================================")
print("PRODUCTION MANIFEST - 2.0")
print("================================")
print(f"ID: {SHORT_ID}")
print(f"Status: {manifest['status']}")
print(f"Assunto: {assunto or 'AUSENTE'}")
print(f"Cenas: {len(cenas_fisicas)}/{QTD_CENAS}")
if os.path.isfile(VIDEO):
    print(f"Vídeo: {width}x{height} {fps:.2f}fps {duracao:.2f}s")
print(f"Manifest: {SAIDA}")
print()

if not quality_pass:
    print("PRODUCTION MANIFEST: INCOMPLETE")
    for chave, ok in quality.items():
        if not ok:
            print(f"ERRO: {chave}")
    raise SystemExit(1)

print("PRODUCTION MANIFEST: OK")
print()

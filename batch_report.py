#!/usr/bin/env python3

import glob
import json
import math
import os
import sys
from datetime import datetime

BASE = os.path.expanduser("~/ShortAutoPro")
MANIFEST_DIR = os.path.join(BASE, "manifests")
REPORT_DIR = os.path.join(BASE, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

try:
    QTD = int(sys.argv[1] if len(sys.argv) > 1 else os.getenv("SHORT_LOTE", "3"))
except ValueError:
    QTD = 3
QTD = max(1, min(QTD, 10))

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))


def dict_seguro(value):
    return value if isinstance(value, dict) else {}


def numero_seguro(value):
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def atomic_write(path, text):
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


all_files = glob.glob(os.path.join(MANIFEST_DIR, "*.json"))
files = [
    path for path in all_files
    if not os.path.basename(path).endswith("_quality.json")
]
files = sorted(files, key=os.path.getmtime, reverse=True)[:QTD]

if not files:
    sys.exit("ERRO: nenhum manifest de produção encontrado.")

productions = []
invalid = []

for path in reversed(files):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        invalid.append(f"{os.path.basename(path)}: {exc}")
        continue

    if not isinstance(data, dict) or not str(data.get("short_id", "")).strip():
        invalid.append(f"{os.path.basename(path)}: estrutura inválida")
        continue

    publish = dict_seguro(data.get("publish"))
    video = dict_seguro(data.get("video"))
    quality = dict_seguro(data.get("quality"))
    duration = numero_seguro(video.get("duration_seconds"))

    productions.append({
        "short_id": str(data.get("short_id", "")),
        "status": str(data.get("status", "")),
        "topic": str(data.get("topic", "")),
        "hook": str(data.get("hook", "")),
        "title": str(publish.get("chosen_title", "")),
        "duration": duration,
        "video": str(video.get("path", "")),
        "resolution_ok": bool(quality.get("resolution_ok", False)),
        "fps_ok": bool(quality.get("fps_ok", False)),
        "audio_ok": bool(quality.get("audio_exists", False)),
        "scenes": int(quality.get("physical_scene_count", 0) or 0),
        "expected_scenes": int(quality.get("expected_scene_count", QTD_CENAS) or QTD_CENAS),
    })

if not productions:
    sys.exit("ERRO: nenhum dos manifests selecionados é válido.")

passes = sum(1 for p in productions if p["status"] == "QUALITY_PASS")
failures = len(productions) - passes + len(invalid)
durations = [p["duration"] for p in productions if p["duration"] is not None]
average_duration = sum(durations) / len(durations) if durations else 0.0

timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
json_path = os.path.join(REPORT_DIR, f"batch_report_{timestamp}.json")
txt_path = os.path.join(REPORT_DIR, f"batch_report_{timestamp}.txt")

report = {
    "created_at": datetime.now().isoformat(),
    "requested": QTD,
    "selected_manifest_files": len(files),
    "valid_productions": len(productions),
    "invalid_manifests": invalid,
    "quality_pass": passes,
    "failures": failures,
    "average_duration": round(average_duration, 2),
    "productions": productions,
}

atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2))

lines = [
    "SHORTAUTO PRO - BATCH REPORT",
    "=" * 32,
    "",
    f"Manifests selecionados: {len(files)}",
    f"Produções válidas: {len(productions)}",
    f"Quality Pass: {passes}",
    f"Falhas/incompletos/inválidos: {failures}",
    f"Duração média: {average_duration:.2f}s",
    "",
]

for number, p in enumerate(productions, start=1):
    lines.extend([
        f"{number}. {p['topic'] or '?'}",
        f"   ID: {p['short_id']}",
        f"   Status: {p['status'] or '?'}",
        f"   Título: {p['title'] or '?'}",
        f"   Duração: {p['duration']:.2f}s" if p["duration"] is not None else "   Duração: ?",
        f"   Cenas: {p['scenes']}/{p['expected_scenes']}",
        f"   Vídeo: {p['video'] or '?'}",
        "",
    ])

if invalid:
    lines.append("MANIFESTS INVÁLIDOS:")
    lines.extend(f"- {item}" for item in invalid)
    lines.append("")

atomic_write(txt_path, "\n".join(lines))

print()
print("================================")
print("BATCH REPORT - STABLE 2.3")
print("================================")
print(f"Produções válidas: {len(productions)}")
print(f"Quality Pass: {passes}")
print(f"Falhas/incompletos/inválidos: {failures}")
print(f"Duração média: {average_duration:.2f}s")
print(f"TXT: {txt_path}")
print(f"JSON: {json_path}")
print()

# O relatório continua sendo gerado, mas retorna falha se os manifests
# selecionados contiverem corrupção estrutural. Assim automações detectam o problema.
if invalid:
    print("BATCH REPORT: WARNING/BLOCK")
    raise SystemExit(1)

print("BATCH REPORT: OK")
print()

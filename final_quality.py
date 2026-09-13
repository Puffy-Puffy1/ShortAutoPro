#!/usr/bin/env python3

import json
import math
import os
import re
import sys
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

MANIFEST = os.path.join(BASE, "manifests", f"{SHORT_ID}.json")
PUBLISH = os.path.join(BASE, "roteiros", f"publish_{SHORT_ID}.json")
ROTEIRO = os.path.join(BASE, "roteiros", f"short_{SHORT_ID}.txt")
HOOK = os.path.join(BASE, "roteiros", f"hook_{SHORT_ID}.txt")
SAIDA = os.path.join(BASE, "manifests", f"{SHORT_ID}_quality.json")


def ler_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def ler_txt(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def dict_seguro(valor):
    return valor if isinstance(valor, dict) else {}


def contar_palavras(texto):
    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            str(texto),
            flags=re.UNICODE,
        )
    )


manifest = ler_json(MANIFEST)
publish = ler_json(PUBLISH)
roteiro = ler_txt(ROTEIRO)
hook = ler_txt(HOOK)

script_score = 25.0
qtd_palavras = contar_palavras(roteiro)
if not 105 <= qtd_palavras <= 125:
    script_score -= 12

frases = [x.strip() for x in re.split(r"[.!?]+", roteiro) if x.strip()]
frases_longas = sum(1 for frase in frases if contar_palavras(frase) > 24)
script_score -= min(6, frases_longas * 2)

abertura = " ".join(roteiro.split()[:15]).lower()
fracas = [
    "hoje vamos",
    "neste vídeo",
    "nesse vídeo",
    "você sabia",
    "voce sabia",
    "vamos falar",
]
if any(abertura.startswith(x) for x in fracas):
    script_score -= 6
script_score = max(0, script_score)

hook_score = 0.0
if hook:
    palavras_hook = contar_palavras(hook)
    hook_score = 14.0
    if 7 <= palavras_hook <= 16:
        hook_score += 5
    elif palavras_hook > 22:
        hook_score -= 4

    termos_hook = [
        "nunca", "ninguém", "ninguem", "desapareceu", "morte", "corpo",
        "mistério", "misterio", "prova", "verdade", "como", "por que", "o que",
    ]
    lower = hook.lower()
    hits = sum(1 for x in termos_hook if x in lower)
    hook_score += min(hits * 2, 6)
hook_score = max(0, min(hook_score, 25))

quality = dict_seguro(manifest.get("quality", {}))
video = dict_seguro(manifest.get("video", {}))
scenes = dict_seguro(manifest.get("scenes", {}))

visual_score = 0.0
if quality.get("resolution_ok"):
    visual_score += 7
if quality.get("fps_ok"):
    visual_score += 5
if quality.get("audio_exists"):
    visual_score += 5

scene_count = scenes.get("count", 0)
physical_count = scenes.get("physical_count", 0)
if scene_count == QTD_CENAS:
    visual_score += 6
if physical_count == QTD_CENAS:
    visual_score += 7
visual_score = min(visual_score, 30)

publish_score_raw = publish.get("publish_score")
publish_score = 0.0

if (
    isinstance(publish_score_raw, (int, float))
    and not isinstance(publish_score_raw, bool)
    and math.isfinite(float(publish_score_raw))
):
    publish_score = max(0, min(float(publish_score_raw), 100)) / 100 * 20
else:
    titulo = str(publish.get("chosen_title", "")).strip()
    descricao = str(publish.get("description", "")).strip()
    hashtags = publish.get("hashtags", [])
    if titulo:
        publish_score += 8
    if 35 <= len(titulo) <= 70:
        publish_score += 4
    if descricao:
        publish_score += 4
    if isinstance(hashtags, list) and len(hashtags) == 5:
        publish_score += 4

publish_score = min(publish_score, 20)
total = round(script_score + hook_score + visual_score + publish_score, 1)

if total >= 85:
    nivel = "EXCELLENT"
elif total >= 75:
    nivel = "GOOD"
elif total >= 65:
    nivel = "ACCEPTABLE"
else:
    nivel = "WEAK"

aprovado = total >= 65
resultado = {
    "short_id": SHORT_ID,
    "total_score": total,
    "level": nivel,
    "approved": aprovado,
    "components": {
        "script": round(script_score, 1),
        "hook": round(hook_score, 1),
        "visual_technical": round(visual_score, 1),
        "publish": round(publish_score, 1),
    },
    "details": {
        "script_words": qtd_palavras,
        "long_sentences": frases_longas,
        "expected_scene_count": QTD_CENAS,
        "scene_count": scene_count,
        "physical_scene_count": physical_count,
        "duration_seconds": video.get("duration_seconds"),
    },
}

os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
temporario = SAIDA + ".tmp"
try:
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
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
print("FINAL QUALITY SCORE - 2.4.0")
print("================================")
print()
print(f"Roteiro: {script_score:.1f}/25")
print(f"Hook: {hook_score:.1f}/25")
print(f"Visual/Técnico: {visual_score:.1f}/30")
print(f"Publish: {publish_score:.1f}/20")
print()
print(f"NOTA FINAL: {total:.1f}/100")
print(f"NÍVEL: {nivel}")
print()
print(f"Arquivo:\n{SAIDA}")
print()

if not aprovado:
    print("FINAL QUALITY SCORE: BLOCK")
    print()
    sys.exit(1)

print("FINAL QUALITY SCORE: PASS")
print()

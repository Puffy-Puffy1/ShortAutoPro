#!/usr/bin/env python3

import json
import os
import re
from datetime import date

from source_identity import (
    detectar_alias,
    extrair_ids_numericos,
    normalizar,
    validar_identidade,
)

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
TOPIC_REAL = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC = os.path.join(R, f"topic_{SHORT_ID}.txt")
SOURCE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
SCRIPT = os.path.join(R, f"short_{SHORT_ID}.txt")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
REPORT = os.path.join(R, f"post_script_truth_{SHORT_ID}.json")


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def extrair_titulo_fonte(texto):
    for linha in str(texto).splitlines():
        m = re.match(r"(?i)^FONTE\s*:\s*(.+)$", linha.strip())
        if not m:
            continue
        valor = m.group(1).strip()
        return re.sub(
            r"(?i)^Wikipedia\s*[—–\-:]\s*",
            "",
            valor,
        ).strip()
    return ""


def flight_ids(texto):
    n = normalizar(texto)
    ids = set()
    patterns = [
        r"\bvoo\s+(?:[a-z]{2,15}\s+)?(\d{1,5})\b",
        r"\bflight\s+(?:[a-z]{2,15}\s+)?(\d{1,5})\b",
    ]
    for pattern in patterns:
        ids.update(re.findall(pattern, n))
    return ids


def alias_canonico(texto):
    return detectar_alias(texto)


def cenas_validas(mapa):
    if not isinstance(mapa, dict):
        return []
    cenas = mapa.get("scenes", [])
    if not isinstance(cenas, list):
        return []
    return [cena for cena in cenas if isinstance(cena, dict)]


def texto_cenas(cenas):
    partes = []
    for cena in cenas:
        partes.append(str(cena.get("segment", "")))
        partes.append(str(cena.get("query", "")))
        must = cena.get("must_have", [])
        if isinstance(must, list):
            partes.extend(str(x) for x in must)
    return "\n".join(partes)


topic = read(TOPIC_REAL) or read(TOPIC)
source = read(SOURCE)
script = read(SCRIPT)
scene_map = read_json(SCENE_MAP)
scenes = cenas_validas(scene_map)
source_title = extrair_titulo_fonte(source)

critical = []
warnings = []
strengths = []

print()
print("======================================")
print(" POST-SCRIPT TRUTH LOCK 6.3")
print("======================================")
print()
print("SHORT_ID:", SHORT_ID)
print("TOPIC:", topic or "AUSENTE")
print("SOURCE:", source_title or "AUSENTE")
print()

if not topic:
    critical.append("topic_missing")
if not source:
    critical.append("source_missing")
if not source_title:
    critical.append("source_title_missing")
if not script:
    critical.append("script_missing")
if not scenes:
    critical.append("scene_map_missing_or_invalid")

source_identity = None
if topic and source_title:
    source_identity = validar_identidade(topic, source_title, source)
    print("SOURCE IDENTITY:", "PASS" if source_identity.get("valid") else "BLOCK")
    print("SOURCE REASON:", source_identity.get("reason"))
    if not source_identity.get("valid"):
        critical.append(
            "topic_source_identity_mismatch:"
            + str(source_identity.get("reason"))
        )
    else:
        strengths.append("topic_source_identity_pass")

topic_ids = extrair_ids_numericos(topic)
source_ids = extrair_ids_numericos(source_title)
scene_text = texto_cenas(scenes)

topic_flights = flight_ids(topic)
source_flights = flight_ids(source_title)
script_flights = flight_ids(script)
scene_flights = flight_ids(scene_text)

print()
print("FLIGHT IDS TOPIC:", sorted(topic_flights))
print("FLIGHT IDS SOURCE:", sorted(source_flights))
print("FLIGHT IDS SCRIPT:", sorted(script_flights))
print("FLIGHT IDS SCENES:", sorted(scene_flights))

if topic_flights and source_flights and not (topic_flights & source_flights):
    critical.append(
        f"flight_identity_conflict:topic={sorted(topic_flights)},source={sorted(source_flights)}"
    )
if topic_flights and script_flights and not (topic_flights & script_flights):
    critical.append(
        f"script_flight_identity_conflict:topic={sorted(topic_flights)},script={sorted(script_flights)}"
    )
if topic_flights and scene_flights and not (topic_flights & scene_flights):
    critical.append(
        f"scene_flight_identity_conflict:topic={sorted(topic_flights)},scenes={sorted(scene_flights)}"
    )
if topic_flights and not script_flights:
    warnings.append("topic_flight_id_not_explicit_in_script")
if topic_flights and not scene_flights:
    warnings.append("topic_flight_id_not_explicit_in_scenes")

topic_alias = alias_canonico(topic)
source_alias = alias_canonico(source_title + " " + source[:3000])
script_alias = alias_canonico(script)
scene_alias = alias_canonico(scene_text)

print()
print("TOPIC ALIAS:", topic_alias)
print("SOURCE ALIAS:", source_alias)
print("SCRIPT ALIAS:", script_alias)
print("SCENE ALIAS:", scene_alias)

if topic_alias:
    if source_alias and source_alias != topic_alias:
        critical.append(f"source_known_alias_conflict:{topic_alias}!={source_alias}")
    if script_alias and script_alias != topic_alias:
        critical.append(f"script_known_alias_conflict:{topic_alias}!={script_alias}")
    if scene_alias and scene_alias != topic_alias:
        critical.append(f"scene_known_alias_conflict:{topic_alias}!={scene_alias}")
    if script_alias == topic_alias:
        strengths.append("script_known_alias_pass")
    if scene_alias == topic_alias:
        strengths.append("scene_known_alias_pass")

print()
print("NUMERIC TOPIC:", sorted(topic_ids))
print("NUMERIC SOURCE TITLE:", sorted(source_ids))

scene_count = len(scenes)
if scene_count == QTD_CENAS:
    strengths.append(f"scene_count_{QTD_CENAS}")
else:
    critical.append(f"scene_count={scene_count}")

status = "BLOCK" if critical else ("WARNING" if warnings else "PASS")
report = {
    "short_id": SHORT_ID,
    "version": "6.3",
    "topic": topic,
    "source_title": source_title,
    "status": status,
    "critical": critical,
    "warnings": warnings,
    "strengths": strengths,
    "source_identity": source_identity,
    "topic_ids": sorted(topic_ids),
    "source_ids": sorted(source_ids),
    "expected_scene_count": QTD_CENAS,
    "scene_count": scene_count,
    "flight_ids": {
        "topic": sorted(topic_flights),
        "source": sorted(source_flights),
        "script": sorted(script_flights),
        "scenes": sorted(scene_flights),
    },
    "aliases": {
        "topic": topic_alias,
        "source": source_alias,
        "script": script_alias,
        "scenes": scene_alias,
    },
}

os.makedirs(R, exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print()
print("CRITICAL:", len(critical))
print("WARNINGS:", len(warnings))
print("STATUS:", status)
print()
print("REPORT:", REPORT)

if critical:
    print()
    for item in critical:
        print("ERRO:", item)
    print()
    print("POST-SCRIPT TRUTH LOCK: BLOCK")
    raise SystemExit(1)

if warnings:
    for item in warnings:
        print("AVISO:", item)

print()
print("POST-SCRIPT TRUTH LOCK:", status)

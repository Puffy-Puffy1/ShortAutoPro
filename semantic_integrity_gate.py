#!/usr/bin/env python3

import json
import os
import re
from collections import Counter
from datetime import date

from source_identity import validar_identidade

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
SCRIPT = os.path.join(R, f"short_{SHORT_ID}.txt")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
SOURCE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
TOPIC_REAL = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC = os.path.join(R, f"topic_{SHORT_ID}.txt")
REPORT = os.path.join(R, f"semantic_integrity_{SHORT_ID}.json")
LOSSLESS_REPORT = os.path.join(R, f"scene_lossless_{SHORT_ID}.json")


def read_text(path):
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


def words(text):
    return re.findall(
        r"[a-z0-9à-ÿ'-]+",
        str(text).lower(),
        flags=re.UNICODE,
    )


def similarity(a, b):
    aa = set(words(a))
    bb = set(words(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


script = read_text(SCRIPT)
source = read_text(SOURCE)
topic = read_text(TOPIC_REAL) or read_text(TOPIC)
data = read_json(SCENE_MAP)
scenes = data.get("scenes", [])
if not isinstance(scenes, list):
    scenes = []
scenes = [scene for scene in scenes if isinstance(scene, dict)]

critical = []
warnings = []
strengths = []

script_words = words(script)
if not 105 <= len(script_words) <= 125:
    critical.append(f"script_words={len(script_words)}")
else:
    strengths.append("script_length_ok")

wiki_title = ""
match = re.search(
    r"Wikipedia\s*[—-]\s*([^\n]+)",
    source,
    flags=re.IGNORECASE,
)
if match:
    wiki_title = match.group(1).strip()

if topic and wiki_title:
    identity = validar_identidade(topic, wiki_title, source)
    if identity.get("valid"):
        strengths.append("source_identity_ok")
    else:
        critical.append("source_identity_mismatch")
else:
    warnings.append("source_identity_not_measurable")

if len(scenes) != QTD_CENAS:
    critical.append(f"scene_count={len(scenes)}")
else:
    strengths.append(f"scene_count_{QTD_CENAS}")

segments = []
missing_query = 0
missing_segment = 0
missing_must = 0

for scene in scenes:
    segment = str(scene.get("segment", "")).strip()
    query = str(scene.get("query", "")).strip()
    must = scene.get("must_have", [])

    if not segment:
        missing_segment += 1
    else:
        segments.append(segment)
    if not query:
        missing_query += 1
    if not isinstance(must, list) or not must:
        missing_must += 1

if missing_segment:
    critical.append(f"missing_segments={missing_segment}")
if missing_query:
    critical.append(f"missing_queries={missing_query}")
if missing_must:
    warnings.append(f"missing_must={missing_must}")

mapped_words = words(" ".join(segments))
script_counter = Counter(script_words)
mapped_counter = Counter(mapped_words)

matched = sum(
    min(count, mapped_counter.get(word, 0))
    for word, count in script_counter.items()
)
coverage = matched / len(script_words) if script_words else 0.0

extra_occurrence_overflow = max(0, len(mapped_words) - matched)
extra_occurrence_ratio = (
    extra_occurrence_overflow / max(len(script_words), 1)
)

script_vocabulary = set(script_words)
novel_mapped_words = [
    word for word in mapped_words if word not in script_vocabulary
]
novel_extra = len(novel_mapped_words)
novel_extra_ratio = novel_extra / max(len(script_words), 1)

verified_lossless_overlap = False
lossless_report = read_json(LOSSLESS_REPORT)

if lossless_report:
    lossless_status = lossless_report.get("status")
    missing_after = lossless_report.get("missing_after") or []
    coverage_after = lossless_report.get("coverage_after")
    changed = lossless_report.get("changed_scenes") or []
    if not isinstance(changed, list):
        changed = []

    normalized_script = " ".join(words(script))
    repair_sources_valid = True

    for item in changed:
        if not isinstance(item, dict):
            repair_sources_valid = False
            break
        source_text = item.get("source_text") or ""
        normalized_source = " ".join(words(source_text))
        if not normalized_source or normalized_source not in normalized_script:
            repair_sources_valid = False
            break

    try:
        coverage_after_ok = float(coverage_after) >= 0.999999
    except (TypeError, ValueError):
        coverage_after_ok = False

    verified_lossless_overlap = (
        lossless_status == "PASS"
        and not missing_after
        and coverage_after_ok
        and repair_sources_valid
        and novel_extra == 0
    )

if verified_lossless_overlap:
    extra = novel_extra
    extra_ratio = novel_extra_ratio
else:
    extra = extra_occurrence_overflow
    extra_ratio = extra_occurrence_ratio

if coverage < 0.96:
    critical.append(f"script_scene_coverage={coverage:.3f}")
else:
    strengths.append(f"script_scene_coverage={coverage:.3f}")

if extra_ratio > 0.08:
    critical.append(f"scene_extra_content={extra_ratio:.3f}")

script_norm = " ".join(script_words)
for scene in scenes:
    segment = str(scene.get("segment", "")).strip()
    segment_norm = " ".join(words(segment))
    if (
        segment_norm
        and segment_norm not in script_norm
        and len(words(segment)) >= 3
        and similarity(segment, script) < 0.08
    ):
        warnings.append(
            f"scene_{scene.get('scene')}_possibly_invented"
        )

for i in range(1, len(scenes)):
    a = scenes[i - 1].get("query", "")
    b = scenes[i].get("query", "")
    sim = similarity(a, b)
    if sim >= 0.70:
        warnings.append(f"visual_repeat_{i}_{i + 1}={sim:.2f}")

status = "BLOCK" if critical else "PASS"
report = {
    "short_id": SHORT_ID,
    "version": "5.2.1",
    "status": status,
    "topic": topic,
    "wiki_title": wiki_title,
    "script_words": len(script_words),
    "expected_scene_count": QTD_CENAS,
    "scene_count": len(scenes),
    "coverage": round(coverage, 4),
    "extra_ratio": round(extra_ratio, 4),
    "raw_overflow_ratio": round(extra_occurrence_ratio, 4),
    "novel_extra_ratio": round(novel_extra_ratio, 4),
    "verified_lossless_overlap": verified_lossless_overlap,
    "critical": critical,
    "warnings": warnings,
    "strengths": strengths,
}

os.makedirs(R, exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print()
print("================================")
print("SEMANTIC INTEGRITY GATE 5.2.1")
print("================================")
print()
print(f"Roteiro: {len(script_words)} palavras")
print(f"Cenas: {len(scenes)}/{QTD_CENAS}")
print(f"Cobertura roteiro->cenas: {coverage * 100:.1f}%")
print(f"Conteúdo extra: {extra_ratio * 100:.1f}%")
print(f"Overflow bruto cenas->roteiro: {extra_occurrence_ratio * 100:.1f}%")
print(f"Conteúdo lexical realmente novo: {novel_extra_ratio * 100:.1f}%")
print("Lossless overlap verificado:", verified_lossless_overlap)
print()

for item in warnings:
    print(f"AVISO: {item}")

if critical:
    print()
    for item in critical:
        print(f"ERRO: {item}")
    print()
    print("SEMANTIC INTEGRITY: BLOCK")
    raise SystemExit(1)

print()
print("SEMANTIC INTEGRITY: PASS")
print()

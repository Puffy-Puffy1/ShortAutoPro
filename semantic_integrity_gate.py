#!/usr/bin/env python3
"""Semantic integrity gate for ShortAutoPro 3.0.2.

The gate verifies that scene narration preserves the script and does not add
unsupported factual content. Descriptive repetition/expansion is diagnostic,
not by itself evidence of invention. New scene vocabulary is accepted when it
is already supported by either the final script or the factual source.
"""

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

# Stop words are ignored only for the unsupported-content metric. Coverage keeps
# the original complete token stream so regressions remain visible.
STOP = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "da", "do",
    "das", "dos", "e", "ou", "em", "no", "na", "nos", "nas", "por", "para",
    "com", "sem", "que", "se", "ao", "aos", "à", "às", "foi", "era", "ser",
    "são", "como", "mais", "mas", "já", "também", "ainda", "seu", "sua",
    "seus", "suas", "ele", "ela", "eles", "elas", "the", "of", "and", "in",
    "on", "at", "to", "for", "from", "with", "a", "an",
}


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def atomic_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def words(text):
    return re.findall(
        r"[a-z0-9à-ÿ'-]+",
        str(text).lower(),
        flags=re.UNICODE,
    )


def content_words(text):
    return [w for w in words(text) if w not in STOP and (len(w) >= 2 or w.isdigit())]


def similarity(a, b):
    aa = set(content_words(a))
    bb = set(content_words(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def parse_wiki_title(source):
    match = re.search(
        r"Wikipedia\s*[—-]\s*([^\n]+)",
        source,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def numeric_tokens(text):
    return set(re.findall(r"\b\d+(?:[.,]\d+)?\b", str(text)))


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

wiki_title = parse_wiki_title(source)
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

mapped_text = " ".join(segments)
mapped_words = words(mapped_text)
script_counter = Counter(script_words)
mapped_counter = Counter(mapped_words)

matched = sum(
    min(count, mapped_counter.get(word, 0))
    for word, count in script_counter.items()
)
coverage = matched / len(script_words) if script_words else 0.0

# Raw occurrence overflow is useful for diagnostics, but repetition is not a
# factual hallucination. It must never block by itself.
extra_occurrence_overflow = max(0, len(mapped_words) - matched)
extra_occurrence_ratio = extra_occurrence_overflow / max(len(script_words), 1)

script_vocabulary = set(script_words)
source_vocabulary = set(words(source))
supported_vocabulary = script_vocabulary | source_vocabulary

novel_mapped_words = [w for w in mapped_words if w not in script_vocabulary]
novel_extra_ratio = len(novel_mapped_words) / max(len(script_words), 1)

mapped_content = content_words(mapped_text)
unsupported_content_words = [
    w for w in mapped_content
    if w not in supported_vocabulary
]
unsupported_counter = Counter(unsupported_content_words)
unsupported_content_ratio = (
    len(unsupported_content_words) / max(len(content_words(script)), 1)
)
unsupported_unique = sorted(unsupported_counter)

# Numbers are high-risk semantic additions. A number is safe if it appears in
# either the final script or the factual source.
supported_numbers = numeric_tokens(script) | numeric_tokens(source)
scene_numbers = numeric_tokens(mapped_text)
unsupported_numbers = sorted(scene_numbers - supported_numbers)
if unsupported_numbers:
    critical.append("unsupported_numbers=" + ",".join(unsupported_numbers))

lossless_report = read_json(LOSSLESS_REPORT)
verified_lossless_overlap = False
lossless_status = ""
if lossless_report:
    lossless_status = str(lossless_report.get("status") or "")
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
        coverage_after_ok = float(coverage_after) >= 0.965
    except (TypeError, ValueError):
        coverage_after_ok = False

    # NO_REPAIR_NEEDED is a successful lossless result, not a failure. Older
    # reports use that status, so keep this backward-compatible.
    verified_lossless_overlap = (
        lossless_status in {"PASS", "NO_REPAIR_NEEDED"}
        and not missing_after
        and coverage_after_ok
        and repair_sources_valid
    )

if coverage < 0.96:
    critical.append(f"script_scene_coverage={coverage:.3f}")
else:
    strengths.append(f"script_scene_coverage={coverage:.3f}")

# Block only on unsupported semantic additions. Vocabulary that is absent from
# the script but present in the factual source is explicitly source-supported.
UNSUPPORTED_LIMIT = 0.12
if unsupported_content_ratio > UNSUPPORTED_LIMIT:
    critical.append(f"unsupported_scene_content={unsupported_content_ratio:.3f}")
elif unsupported_content_words:
    warnings.append(f"unsupported_scene_content={unsupported_content_ratio:.3f}")
else:
    strengths.append("scene_content_source_supported")

if extra_occurrence_ratio > 0.35:
    warnings.append(f"raw_scene_expansion={extra_occurrence_ratio:.3f}")

# Per-scene suspicion uses BOTH script and source. This catches truly unrelated
# narration while avoiding false positives from documentary details supported by
# the factual source.
semantic_reference = f"{script} {source}"
for scene in scenes:
    segment = str(scene.get("segment", "")).strip()
    if not segment or len(content_words(segment)) < 3:
        continue
    unsupported = [
        w for w in content_words(segment)
        if w not in supported_vocabulary
    ]
    local_ratio = len(unsupported) / max(len(content_words(segment)), 1)
    if local_ratio > 0.35 and similarity(segment, semantic_reference) < 0.05:
        warnings.append(f"scene_{scene.get('scene')}_possibly_invented")

for i in range(1, len(scenes)):
    a = scenes[i - 1].get("query", "")
    b = scenes[i].get("query", "")
    sim = similarity(a, b)
    if sim >= 0.70:
        warnings.append(f"visual_repeat_{i}_{i + 1}={sim:.2f}")

status = "BLOCK" if critical else "PASS"
report = {
    "short_id": SHORT_ID,
    "version": "5.3.0",
    "status": status,
    "topic": topic,
    "wiki_title": wiki_title,
    "script_words": len(script_words),
    "expected_scene_count": QTD_CENAS,
    "scene_count": len(scenes),
    "coverage": round(coverage, 4),
    "raw_overflow_ratio": round(extra_occurrence_ratio, 4),
    "novel_extra_ratio": round(novel_extra_ratio, 4),
    "unsupported_content_ratio": round(unsupported_content_ratio, 4),
    "unsupported_unique_words": unsupported_unique[:40],
    "unsupported_numbers": unsupported_numbers,
    "lossless_status": lossless_status,
    "verified_lossless_overlap": verified_lossless_overlap,
    "critical": critical,
    "warnings": warnings,
    "strengths": strengths,
}
atomic_json(REPORT, report)

print()
print("================================")
print("SEMANTIC INTEGRITY GATE 5.3.0")
print("================================")
print()
print(f"Roteiro: {len(script_words)} palavras")
print(f"Cenas: {len(scenes)}/{QTD_CENAS}")
print(f"Cobertura roteiro->cenas: {coverage * 100:.1f}%")
print(f"Expansão bruta cenas->roteiro: {extra_occurrence_ratio * 100:.1f}%")
print(f"Vocabulário novo vs roteiro: {novel_extra_ratio * 100:.1f}%")
print(f"Conteúdo não sustentado por roteiro/fonte: {unsupported_content_ratio * 100:.1f}%")
print("Lossless status:", lossless_status or "ausente")
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

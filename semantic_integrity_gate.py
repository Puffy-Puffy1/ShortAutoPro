#!/usr/bin/env python3

import os
import re
import json
from collections import Counter
from datetime import date

from source_identity import validar_identidade


BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

R = os.path.join(BASE, "roteiros")

SCRIPT = os.path.join(R, f"short_{SHORT_ID}.txt")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
SOURCE = os.path.join(R, f"fonte_{SHORT_ID}.txt")
TOPIC_REAL = os.path.join(R, f"used_topic_{SHORT_ID}.txt")
TOPIC = os.path.join(R, f"topic_{SHORT_ID}.txt")
REPORT = os.path.join(R, f"semantic_integrity_{SHORT_ID}.json")


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def words(text):
    return re.findall(
        r"[a-z0-9à-ÿ'-]+",
        str(text).lower(),
        flags=re.UNICODE
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

critical = []
warnings = []
strengths = []


# =====================================================
# SCRIPT
# =====================================================

script_words = words(script)

if not 105 <= len(script_words) <= 125:
    critical.append(
        f"script_words={len(script_words)}"
    )
else:
    strengths.append("script_length_ok")


# =====================================================
# SOURCE IDENTITY
# =====================================================

wiki_title = ""

match = re.search(
    r"Wikipedia\s*[—-]\s*([^\n]+)",
    source,
    flags=re.IGNORECASE
)

if match:
    wiki_title = match.group(1).strip()


if topic and wiki_title:

    identity = validar_identidade(
        topic,
        wiki_title,
        source
    )

    if identity.get("valid"):
        strengths.append("source_identity_ok")
    else:
        critical.append(
            "source_identity_mismatch"
        )
else:
    warnings.append(
        "source_identity_not_measurable"
    )


# =====================================================
# SCENES
# =====================================================

if len(scenes) != 12:
    critical.append(
        f"scene_count={len(scenes)}"
    )
else:
    strengths.append("scene_count_12")


segments = []

missing_query = 0
missing_segment = 0
missing_must = 0


for scene in scenes:

    segment = str(
        scene.get("segment", "")
    ).strip()

    query = str(
        scene.get("query", "")
    ).strip()

    must = scene.get(
        "must_have",
        []
    )

    if not segment:
        missing_segment += 1
    else:
        segments.append(segment)

    if not query:
        missing_query += 1

    if not isinstance(must, list) or not must:
        missing_must += 1


if missing_segment:
    critical.append(
        f"missing_segments={missing_segment}"
    )

if missing_query:
    critical.append(
        f"missing_queries={missing_query}"
    )

if missing_must:
    warnings.append(
        f"missing_must={missing_must}"
    )


# =====================================================
# SCRIPT ↔ SCENE COVERAGE
# =====================================================

mapped_words = words(
    " ".join(segments)
)

script_counter = Counter(script_words)
mapped_counter = Counter(mapped_words)

matched = sum(
    min(
        count,
        mapped_counter.get(word, 0)
    )
    for word, count
    in script_counter.items()
)

coverage = (
    matched / len(script_words)
    if script_words
    else 0.0
)

# SEMANTIC 5.1 LOSSLESS VERIFIED OVERLAP FIX
#
# Historical metric:
#   len(mapped_words) - matched
#
# That metric mixes two different phenomena:
#
# 1. genuinely new lexical content;
# 2. repeated/overlapping words that already exist
#    in the source script.
#
# The second case can legitimately happen after
# Lossless Scene Coverage Repair and must not be
# mislabeled as invented scene content.
#
# We therefore preserve the historical overflow
# metric for diagnostics while independently
# measuring truly novel lexical occurrences.

extra_occurrence_overflow = max(
    0,
    len(mapped_words) - matched
)

extra_occurrence_ratio = (
    extra_occurrence_overflow
    / max(len(script_words), 1)
)


# -----------------------------------------------------
# TRUE NOVEL CONTENT
# -----------------------------------------------------

script_vocabulary = set(
    script_words
)

novel_mapped_words = [
    word
    for word in mapped_words
    if word not in script_vocabulary
]

novel_extra = len(
    novel_mapped_words
)

novel_extra_ratio = (
    novel_extra
    / max(len(script_words), 1)
)


# -----------------------------------------------------
# VERIFIED LOSSLESS REPAIR
# -----------------------------------------------------

verified_lossless_overlap = False

lossless_report = None

try:
    import json as _semantic_json
    from pathlib import Path as _SemanticPath

    _semantic_base = _SemanticPath.home() / "ShortAutoPro"

    _lossless_path = (
        _semantic_base
        / "roteiros"
        / f"scene_lossless_{short_id}.json"
    )

    if _lossless_path.exists():

        lossless_report = _semantic_json.loads(
            _lossless_path.read_text(
                encoding="utf-8"
            )
        )

        _lossless_status = (
            lossless_report.get("status")
        )

        _missing_after = (
            lossless_report.get(
                "missing_after"
            )
            or []
        )

        _coverage_after = (
            lossless_report.get(
                "coverage_after"
            )
        )

        _changed = (
            lossless_report.get(
                "changed_scenes"
            )
            or []
        )


        # Every repaired source_text must itself
        # originate from the final script.
        _normalized_script = " ".join(
            words(
                script
            )
        )

        _repair_sources_valid = True

        for _item in _changed:

            _source_text = (
                _item.get(
                    "source_text"
                )
                or ""
            )

            _normalized_source = " ".join(
                words(
                    _source_text
                )
            )

            if (
                not _normalized_source
                or _normalized_source
                not in _normalized_script
            ):
                _repair_sources_valid = False
                break


        verified_lossless_overlap = (
            _lossless_status == "PASS"
            and not _missing_after
            and _coverage_after == 1.0
            and _repair_sources_valid
            and novel_extra == 0
        )

except Exception:
    verified_lossless_overlap = False


# -----------------------------------------------------
# FINAL SEMANTIC EXTRA METRIC
# -----------------------------------------------------
#
# If Lossless Repair is cryptographically/logically
# verified as being sourced from the actual script
# and introduced zero new vocabulary, repeated
# occurrences are classified as overlap rather than
# fabricated content.
#
# Otherwise the historical conservative metric
# remains active.

if verified_lossless_overlap:

    extra = novel_extra
    extra_ratio = novel_extra_ratio

else:

    extra = extra_occurrence_overflow
    extra_ratio = extra_occurrence_ratio


if coverage < 0.96:
    critical.append(
        f"script_scene_coverage={coverage:.3f}"
    )
else:
    strengths.append(
        f"script_scene_coverage={coverage:.3f}"
    )


if extra_ratio > 0.08:
    critical.append(
        f"scene_extra_content={extra_ratio:.3f}"
    )


# =====================================================
# FALSA CENA FINAL
# =====================================================

script_norm = " ".join(script_words)

for scene in scenes:

    segment = str(
        scene.get("segment", "")
    ).strip()

    segment_norm = " ".join(
        words(segment)
    )

    if (
        segment_norm
        and segment_norm not in script_norm
        and len(words(segment)) >= 3
    ):
        sim = similarity(
            segment,
            script
        )

        if sim < 0.08:
            warnings.append(
                f"scene_{scene.get('scene')}_possibly_invented"
            )


# =====================================================
# ADJACENT REPETITION
# =====================================================

for i in range(1, len(scenes)):

    a = scenes[i - 1].get(
        "query",
        ""
    )

    b = scenes[i].get(
        "query",
        ""
    )

    sim = similarity(a, b)

    if sim >= 0.70:
        warnings.append(
            f"visual_repeat_{i}_{i + 1}={sim:.2f}"
        )


status = (
    "BLOCK"
    if critical
    else "PASS"
)

report = {
    "short_id": SHORT_ID,
    "version": "5.1",
    "status": status,
    "topic": topic,
    "wiki_title": wiki_title,
    "script_words": len(script_words),
    "scene_count": len(scenes),
    "coverage": round(coverage, 4),
    "extra_ratio": round(extra_ratio, 4),
    "critical": critical,
    "warnings": warnings,
    "strengths": strengths
}


with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        report,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("================================")
print("SEMANTIC INTEGRITY GATE 5.1")
print("================================")
print()

print(
    f"Roteiro: {len(script_words)} palavras"
)

print(
    f"Cenas: {len(scenes)}/12"
)

print(
    f"Cobertura roteiro→cenas: "
    f"{coverage * 100:.1f}%"
)

print(
    f"Conteúdo extra: "
    f"{extra_ratio * 100:.1f}%"
)


# SEMANTIC 5.1 OVERLAP DIAGNOSTICS
print(
    f"Overflow bruto cenas→roteiro: "
    f"{extra_occurrence_ratio * 100:.1f}%"
)

print(
    f"Conteúdo lexical realmente novo: "
    f"{novel_extra_ratio * 100:.1f}%"
)

print(
    "Lossless overlap verificado:",
    verified_lossless_overlap
)

print()


for item in warnings:
    print(
        f"AVISO: {item}"
    )


if critical:

    print()

    for item in critical:
        print(
            f"ERRO: {item}"
        )

    print()
    print("SEMANTIC INTEGRITY: BLOCK")

    raise SystemExit(1)


print()
print("SEMANTIC INTEGRITY: PASS")
print()

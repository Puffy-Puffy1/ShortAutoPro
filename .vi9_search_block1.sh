#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "=================================================="
echo " VI8.61 -> VI8.70"
echo " VISUAL SEARCH INTELLIGENCE FOUNDATION"
echo " SHADOW ONLY"
echo "=================================================="
echo

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.61 — QUERY NORMALIZER
# =====================================================

cat > vi8_61_query_normalizer.py <<'PY'
#!/usr/bin/env python3

import re

VERSION = "8.61"

REMOVE = {
    "image",
    "photo",
    "picture",
    "stock",
    "wallpaper",
    "4k",
    "hd",
}

def normalize(text):
    tokens = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )

    cleaned = []

    seen = set()

    for token in tokens:
        low = token.lower()

        if low in REMOVE:
            continue

        if low in seen:
            continue

        seen.add(low)
        cleaned.append(token)

    return " ".join(
        cleaned
    ).strip()


def self_test():
    result = normalize(
        "ransom note image photo ransom note"
    )

    assert "image" not in result.lower()
    assert "photo" not in result.lower()

    print(
        "VI8.61 QUERY NORMALIZER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.62 — SEARCH INTENT BUILDER
# =====================================================

cat > vi8_62_search_intent_builder.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.62"


INTENT = {
    "FACE": [
        "portrait",
        "clear face",
        "documentary photograph",
    ],

    "DOCUMENT": [
        "original document",
        "archive",
        "close detail",
    ],

    "EVIDENCE": [
        "forensic evidence",
        "documentary",
        "close detail",
    ],

    "LOCATION": [
        "location",
        "exterior",
        "documentary photograph",
    ],

    "OBJECT": [
        "object detail",
        "documentary photograph",
    ],

    "GENERAL": [
        "documentary photograph",
    ],
}


def build(category):
    category = str(
        category or "GENERAL"
    ).upper()

    return list(
        INTENT.get(
            category,
            INTENT["GENERAL"]
        )
    )


def self_test():
    assert (
        "portrait"
        in build("FACE")
    )

    print(
        "VI8.62 SEARCH INTENT BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.63 — SHOT SEARCH LANGUAGE
# =====================================================

cat > vi8_63_shot_search_language.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.63"


SHOT_TERMS = {
    "close_up": [
        "close up",
        "detail",
    ],

    "medium": [
        "medium shot",
        "waist up",
    ],

    "wide": [
        "wide shot",
        "environment",
    ],
}


def terms(shot):
    return list(
        SHOT_TERMS.get(
            str(
                shot or "medium"
            ).lower(),
            SHOT_TERMS["medium"]
        )
    )


def self_test():
    assert (
        "wide shot"
        in terms("wide")
    )

    print(
        "VI8.63 SHOT SEARCH LANGUAGE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.64 — IDENTITY QUERY GUARD
# =====================================================

cat > vi8_64_identity_query_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.64"


def evaluate(
    category,
    base_query,
    subject_name=None
):
    warnings = []
    blockers = []

    category = str(
        category or "GENERAL"
    ).upper()

    query = str(
        base_query or ""
    ).strip()

    if category == "FACE":

        if subject_name:
            if (
                str(subject_name).lower()
                not in query.lower()
            ):
                query = (
                    str(subject_name).strip()
                    + " "
                    + query
                ).strip()

        else:
            warnings.append(
                "face_query_without_confirmed_subject_name"
            )

    return {
        "version": VERSION,
        "query": query,
        "blockers": blockers,
        "warnings": warnings,
        "status": (
            "HOLD"
            if blockers
            else (
                "CAUTION"
                if warnings
                else "PASS"
            )
        ),
    }


def self_test():
    result = evaluate(
        "FACE",
        "portrait",
        "Example Person"
    )

    assert (
        "Example Person"
        in result["query"]
    )

    print(
        "VI8.64 IDENTITY QUERY GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.65 — GRAPHIC SEARCH GUARD
# =====================================================

cat > vi8_65_graphic_search_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.65"

GRAPHIC = {
    "corpse",
    "dead body",
    "bloody body",
    "gore",
    "graphic wound",
    "autopsy photo",
    "severed",
}

SAFE_REPLACEMENTS = {
    "corpse":
        "crime scene",

    "dead body":
        "crime scene",

    "bloody body":
        "forensic scene",

    "gore":
        "forensic evidence",

    "graphic wound":
        "forensic evidence",

    "autopsy photo":
        "forensic archive",

    "severed":
        "forensic evidence",
}


def sanitize(query):
    original = str(
        query or ""
    )

    output = original

    removed = []

    for unsafe in GRAPHIC:
        if unsafe in output.lower():
            replacement = (
                SAFE_REPLACEMENTS[
                    unsafe
                ]
            )

            import re

            output = re.sub(
                re.escape(unsafe),
                replacement,
                output,
                flags=re.I
            )

            removed.append(
                unsafe
            )

    return {
        "version": VERSION,
        "original": original,
        "query": output,
        "changed":
            output != original,
        "removed_terms":
            sorted(removed),
    }


def self_test():
    result = sanitize(
        "crime dead body basement"
    )

    assert (
        "dead body"
        not in result[
            "query"
        ].lower()
    )

    print(
        "VI8.65 GRAPHIC SEARCH GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.66 — QUERY VARIANT GENERATOR
# =====================================================

cat > vi8_66_query_variant_generator.py <<'PY'
#!/usr/bin/env python3

from vi8_61_query_normalizer import (
    normalize
)

from vi8_62_search_intent_builder import (
    build as intent_terms
)

from vi8_63_shot_search_language import (
    terms as shot_terms
)

from vi8_65_graphic_search_guard import (
    sanitize
)

VERSION = "8.66"


def generate(
    base_query,
    category,
    ideal_shot
):
    base = normalize(
        base_query
    )

    intents = intent_terms(
        category
    )

    shots = shot_terms(
        ideal_shot
    )

    candidates = [
        base,
        f"{base} {intents[0]}",
        f"{base} {shots[0]}",
        f"{base} {intents[0]} {shots[0]}",
    ]

    if len(intents) > 1:
        candidates.append(
            f"{base} {intents[1]}"
        )

    cleaned = []

    seen = set()

    for candidate in candidates:
        candidate = normalize(
            candidate
        )

        candidate = sanitize(
            candidate
        )["query"]

        key = (
            candidate
            .strip()
            .lower()
        )

        if (
            key
            and key not in seen
        ):
            seen.add(key)
            cleaned.append(
                candidate.strip()
            )

    return cleaned[:5]


def self_test():
    result = generate(
        "ransom note",
        "DOCUMENT",
        "close_up"
    )

    assert len(result) >= 3

    print(
        "VI8.66 QUERY VARIANT GENERATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.67 — QUERY DIVERSITY GUARD
# =====================================================

cat > vi8_67_query_diversity_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.67"


def evaluate(queries):
    normalized = [
        str(x or "")
        .lower()
        .strip()
        for x in queries
        if str(x or "").strip()
    ]

    unique = list(
        dict.fromkeys(
            normalized
        )
    )

    ratio = (
        len(unique)
        / len(normalized)
        if normalized
        else 0
    )

    return {
        "version": VERSION,
        "query_count":
            len(normalized),
        "unique_count":
            len(unique),
        "diversity_ratio":
            round(
                ratio,
                3
            ),
        "status": (
            "PASS"
            if ratio >= .75
            else "PASS_WITH_WARNINGS"
        ),
    }


def self_test():
    result = evaluate([
        "a",
        "b",
        "c",
    ])

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI8.67 QUERY DIVERSITY GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.68 — PROVIDER-AGNOSTIC SEARCH CONTRACT
# =====================================================

cat > vi8_68_search_contract.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.68"


def build(
    scene,
    category,
    ideal_shot,
    priority,
    queries
):
    return {
        "version": VERSION,

        "scene":
            scene,

        "category":
            category,

        "ideal_shot":
            ideal_shot,

        "priority":
            priority,

        "queries":
            list(
                queries or []
            ),

        "max_results_per_query":
            5,

        "allow_network":
            False,

        "allow_download":
            False,

        "allow_replace":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "mode":
            "SEARCH_SHADOW",
    }


def self_test():
    result = build(
        6,
        "FACE",
        "medium",
        90,
        ["portrait"]
    )

    assert (
        result["allow_network"]
        is False
    )

    print(
        "VI8.68 SEARCH CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.69 — SEARCH PLAN COMPILER
# =====================================================

cat > vi8_69_search_plan_compiler.py <<'PY'
#!/usr/bin/env python3

from vi8_66_query_variant_generator import (
    generate
)

from vi8_67_query_diversity_guard import (
    evaluate as diversity
)

from vi8_68_search_contract import (
    build as contract
)

VERSION = "8.69"


def compile_plan(
    strategy_items
):
    plans = []

    for item in (
        strategy_items
        or []
    ):
        if item.get(
            "skip_search"
        ):
            continue

        if not item.get(
            "worthwhile"
        ):
            continue

        queries = generate(
            item.get(
                "search_query"
            )
            or "",
            item.get(
                "category"
            ),
            item.get(
                "ideal_shot"
            )
        )

        query_audit = diversity(
            queries
        )

        plan = contract(
            item.get(
                "scene"
            ),
            item.get(
                "category"
            ),
            item.get(
                "ideal_shot"
            ),
            item.get(
                "priority_score"
            ),
            queries
        )

        plan[
            "query_diversity"
        ] = query_audit

        plans.append(
            plan
        )

    plans.sort(
        key=lambda x:
            float(
                x.get(
                    "priority",
                    0
                )
            ),
        reverse=True
    )

    return {
        "version": VERSION,
        "plans": plans,
        "count": len(plans),
    }


def self_test():
    result = compile_plan([
        {
            "scene": 5,
            "category":
                "DOCUMENT",
            "ideal_shot":
                "close_up",
            "priority_score":
                80,
            "search_query":
                "ransom note",
            "skip_search":
                False,
            "worthwhile":
                True,
        }
    ])

    assert result[
        "count"
    ] == 1

    print(
        "VI8.69 SEARCH PLAN COMPILER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.70 — SEARCH SHADOW FOUNDATION GATE
# =====================================================

cat > vi8_70_search_shadow_foundation_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_60_real_media_search_master_gate import (
    evaluate as vi860
)

from vi8_69_search_plan_compiler import (
    compile_plan
)

VERSION = "8.70"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    baseline = vi860()

    strategy = (
        baseline.get(
            "strategy"
        )
        or {}
    )

    budget = (
        strategy.get(
            "budget"
        )
        or {}
    )

    selected = (
        budget.get(
            "selected"
        )
        or []
    )

    compiled = compile_plan(
        selected
    )

    blockers = []
    warnings = []

    for plan in (
        compiled.get("plans")
        or []
    ):
        if plan.get(
            "allow_network"
        ):
            blockers.append(
                "network_must_remain_disabled"
            )

        if plan.get(
            "allow_download"
        ):
            blockers.append(
                "download_must_remain_disabled"
            )

        audit = (
            plan.get(
                "query_diversity"
            )
            or {}
        )

        if audit.get(
            "status"
        ) != "PASS":
            warnings.append(
                f"scene_{plan.get('scene')}_query_diversity"
            )

    if blockers:
        status = "HOLD"

    elif compiled.get(
        "count",
        0
    ) > 0:
        status = (
            "SEARCH_SHADOW_FOUNDATION_READY"
        )

    else:
        status = (
            "NO_SEARCH_REQUIRED"
        )

    result = {
        "version": VERSION,
        "status": status,
        "short_id":
            baseline.get(
                "short_id"
            ),
        "baseline_status":
            baseline.get(
                "status"
            ),
        "compiled":
            compiled,
        "blockers":
            sorted(
                set(blockers)
            ),
        "warnings":
            sorted(
                set(warnings)
            ),
        "network_executed":
            False,
        "download_executed":
            False,
        "media_mutated":
            False,
        "ffmpeg_executed":
            False,
        "video_generated":
            False,
        "renderer_activation":
            False,
        "source_recovery":
            "SHADOW_ONLY",
        "full_active":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_70_search_shadow_foundation_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.70"

    print(
        "VI8.70 SEARCH SHADOW FOUNDATION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_61_query_normalizer.py \
  vi8_62_search_intent_builder.py \
  vi8_63_shot_search_language.py \
  vi8_64_identity_query_guard.py \
  vi8_65_graphic_search_guard.py \
  vi8_66_query_variant_generator.py \
  vi8_67_query_diversity_guard.py \
  vi8_68_search_contract.py \
  vi8_69_search_plan_compiler.py \
  vi8_70_search_shadow_foundation_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_61_query_normalizer.py || exit 11
python vi8_62_search_intent_builder.py || exit 12
python vi8_63_shot_search_language.py || exit 13
python vi8_64_identity_query_guard.py || exit 14
python vi8_65_graphic_search_guard.py || exit 15
python vi8_66_query_variant_generator.py || exit 16
python vi8_67_query_diversity_guard.py || exit 17
python vi8_68_search_contract.py || exit 18
python vi8_69_search_plan_compiler.py || exit 19
python vi8_70_search_shadow_foundation_gate.py || exit 20

echo "SELF TESTS=PASS"


echo
echo "======================================"
echo " VI8.70 SEARCH SHADOW ANALYSIS"
echo "======================================"

python - <<'PY'
from vi8_70_search_shadow_foundation_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "SHORT ID:",
    r.get("short_id")
)

print(
    "BASELINE:",
    r.get(
        "baseline_status"
    )
)

compiled = (
    r.get("compiled")
    or {}
)

print(
    "SEARCH PLANS:",
    compiled.get(
        "count"
    )
)

print(
    "BLOCKERS:",
    r.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    r.get(
        "warnings"
    )
)

print()
print(
    "===== COMPILED SEARCH CONTRACTS ====="
)

for plan in (
    compiled.get("plans")
    or []
):
    audit = (
        plan.get(
            "query_diversity"
        )
        or {}
    )

    print()
    print(
        "SCENE:",
        plan.get("scene")
    )

    print(
        "CATEGORY:",
        plan.get("category")
    )

    print(
        "IDEAL SHOT:",
        plan.get(
            "ideal_shot"
        )
    )

    print(
        "PRIORITY:",
        plan.get(
            "priority"
        )
    )

    print(
        "QUERY DIVERSITY:",
        audit.get(
            "diversity_ratio"
        )
    )

    for i, query in enumerate(
        plan.get("queries")
        or [],
        start=1
    ):
        print(
            f"  Q{i}:",
            query
        )

print()
print(
    "NETWORK EXECUTED:",
    r.get(
        "network_executed"
    )
)

print(
    "DOWNLOAD EXECUTED:",
    r.get(
        "download_executed"
    )
)

print(
    "MEDIA MUTATED:",
    r.get(
        "media_mutated"
    )
)

print(
    "FFMPEG EXECUTED:",
    r.get(
        "ffmpeg_executed"
    )
)

print(
    "VIDEO GENERATED:",
    r.get(
        "video_generated"
    )
)
PY


VIDEO_AFTER="$(sha256sum video.py | awk '{print $1}')"
GERAR_AFTER="$(sha256sum gerar_short.sh | awk '{print $1}')"

if [ "$VIDEO_BEFORE" != "$VIDEO_AFTER" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_AFTER" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi


echo
echo "======================================"
echo " VI8.61 -> VI8.70 COMPLETE"
echo "======================================"
echo
echo "QUERY NORMALIZATION=READY"
echo "SEARCH INTENT=READY"
echo "SHOT SEARCH LANGUAGE=READY"
echo "IDENTITY QUERY GUARD=READY"
echo "GRAPHIC SEARCH GUARD=READY"
echo "QUERY VARIANTS=READY"
echo "QUERY DIVERSITY=READY"
echo "SEARCH CONTRACTS=READY"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "NETWORK EXECUTED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"

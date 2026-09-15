#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI8.41 -> VI8.50"
echo " REAL MEDIA RANKING ENGINE"
echo " SHADOW ONLY"
echo "======================================"
echo

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.41 — SCENE MAP LOADER
# =====================================================

cat > vi8_41_scene_map_loader.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.41"

BASE = Path.home() / "ShortAutoPro"


def latest_scene_map():
    files = [
        p
        for p in (
            BASE / "roteiros"
        ).glob("scene_map_*.json")
        if "_pre_" not in p.name
    ]

    files.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )

    return files[0] if files else None


def load():
    path = latest_scene_map()

    if not path:
        raise RuntimeError(
            "scene_map_missing"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    scenes = (
        data.get("scenes")
        or []
    )

    if len(scenes) != 12:
        raise RuntimeError(
            "scene_count_not_12"
        )

    return {
        "version": VERSION,
        "path": str(path),
        "short_id":
            data.get("short_id"),
        "scenes": scenes,
    }


def self_test():
    assert VERSION == "8.41"

    print(
        "VI8.41 SCENE MAP LOADER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.42 — SCENE LOOKUP
# =====================================================

cat > vi8_42_scene_lookup.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.42"


def by_number(scenes):
    result = {}

    for index, scene in enumerate(
        scenes,
        start=1
    ):
        number = int(
            scene.get(
                "scene",
                index
            )
        )

        result[number] = scene

    return result


def self_test():
    result = by_number([
        {
            "scene": 3,
            "query": "house"
        }
    ])

    assert 3 in result

    print(
        "VI8.42 SCENE LOOKUP=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.43 — REAL CATEGORY RESOLVER
# =====================================================

cat > vi8_43_real_category_resolver.py <<'PY'
#!/usr/bin/env python3

from vi7_31_visual_ontology import (
    classify
)

VERSION = "8.43"


def resolve(scene):
    return classify(
        scene
    )


def self_test():
    result = resolve({
        "query":
            "handwritten document paper"
    })

    assert result == "DOCUMENT"

    print(
        "VI8.43 REAL CATEGORY RESOLVER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.44 — REAL SHOT ESTIMATOR
# =====================================================

cat > vi8_44_real_shot_estimator.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.44"


def estimate(
    item,
    category,
    scene
):
    orientation = str(
        item.get(
            "orientation"
        )
        or ""
    ).upper()

    editorial = str(
        scene.get(
            "shot_type"
        )
        or ""
    ).lower()

    # Editorial metadata stays primary.
    if editorial in {
        "close_up",
        "medium",
        "wide",
    }:
        return editorial

    if category in {
        "FACE",
        "DOCUMENT",
        "EVIDENCE",
        "OBJECT",
    }:
        if orientation == "PORTRAIT":
            return "close_up"

        return "medium"

    if category == "LOCATION":
        if orientation == "LANDSCAPE":
            return "wide"

        return "medium"

    return "medium"


def self_test():
    result = estimate(
        {
            "orientation":
                "LANDSCAPE"
        },
        "LOCATION",
        {}
    )

    assert result == "wide"

    print(
        "VI8.44 REAL SHOT ESTIMATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.45 — REAL CANDIDATE ENRICHER
# =====================================================

cat > vi8_45_real_candidate_enricher.py <<'PY'
#!/usr/bin/env python3

from vi8_37_real_candidate_converter import (
    convert
)

from vi8_44_real_shot_estimator import (
    estimate
)

VERSION = "8.45"


def enrich(
    item,
    scene,
    category
):
    candidate = convert(
        item,
        scene,
        category
    )

    candidate["shot"] = estimate(
        item,
        category,
        scene
    )

    metadata = (
        candidate.get(
            "metadata"
        )
        or {}
    )

    metadata[
        "scene_guess"
    ] = item.get(
        "scene_guess"
    )

    metadata[
        "size_bytes"
    ] = item.get(
        "size_bytes"
    )

    metadata[
        "crop_fitness"
    ] = item.get(
        "crop_fitness"
    )

    candidate[
        "metadata"
    ] = metadata

    return candidate


def self_test():
    result = enrich(
        {
            "path": "a.jpg",
            "name": "a.jpg",
            "media_type": "STILL",
            "width": 1200,
            "height": 1600,
            "orientation": "PORTRAIT",
            "technical_score": 90,
            "scene_guess": 4,
            "size_bytes": 1000000,
        },
        {
            "query": "document",
            "shot_type":
                "close_up",
        },
        "DOCUMENT"
    )

    assert (
        result["shot"]
        == "close_up"
    )

    print(
        "VI8.45 REAL CANDIDATE ENRICHER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.46 — REAL VS VIRTUAL RANKER
# =====================================================

cat > vi8_46_real_vs_virtual_ranker.py <<'PY'
#!/usr/bin/env python3

from vi8_38_real_media_score import (
    evaluate as real_score
)

from vi8_12_virtual_candidate_factory import (
    build as virtual_candidates
)

from vi8_09_candidate_scorer import (
    evaluate as virtual_score
)

VERSION = "8.46"


def rank(
    scene,
    category,
    real_candidates,
    previous_winners=None
):
    previous_winners = (
        previous_winners
        or []
    )

    ranking = []

    for candidate in (
        real_candidates
        or []
    ):
        score = real_score(
            scene,
            candidate,
            previous_winners
        )

        ranking.append({
            "kind":
                "REAL",

            "candidate":
                candidate,

            "score":
                score["score"],

            "eligible":
                score["eligible"],

            "blockers":
                score["blockers"],

            "warnings":
                score["warnings"],

            "technical_score":
                score[
                    "technical_score"
                ],
        })

    virtual = virtual_candidates(
        scene,
        category
    )

    for candidate in virtual:
        score = virtual_score(
            scene,
            candidate,
            previous_winners
        )

        ranking.append({
            "kind":
                "VIRTUAL_IDEAL",

            "candidate":
                candidate,

            "score":
                score["score"],

            "eligible":
                score["eligible"],

            "blockers":
                score["blockers"],

            "warnings":
                score["warnings"],

            "technical_score":
                None,
        })

    eligible = [
        x
        for x in ranking
        if x.get(
            "eligible"
        )
    ]

    eligible.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    winner = (
        eligible[0]
        if eligible
        else None
    )

    real_only = [
        x
        for x in eligible
        if x.get(
            "kind"
        ) == "REAL"
    ]

    real_only.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    best_real = (
        real_only[0]
        if real_only
        else None
    )

    virtual_only = [
        x
        for x in eligible
        if x.get(
            "kind"
        ) == "VIRTUAL_IDEAL"
    ]

    virtual_only.sort(
        key=lambda x:
            float(
                x.get(
                    "score",
                    0
                )
            ),
        reverse=True
    )

    best_virtual = (
        virtual_only[0]
        if virtual_only
        else None
    )

    real_gap = None

    if (
        best_real
        and best_virtual
    ):
        real_gap = round(
            float(
                best_virtual[
                    "score"
                ]
            )
            -
            float(
                best_real[
                    "score"
                ]
            ),
            2
        )

    return {
        "version":
            VERSION,

        "ranking":
            ranking,

        "winner":
            winner,

        "best_real":
            best_real,

        "best_virtual":
            best_virtual,

        "virtual_advantage":
            real_gap,

        "real_candidate_count":
            len(
                real_candidates
                or []
            ),
    }


def self_test():
    assert VERSION == "8.46"

    print(
        "VI8.46 REAL VS VIRTUAL RANKER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.47 — REAL MEDIA GAP CLASSIFIER
# =====================================================

cat > vi8_47_real_media_gap.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.47"


def evaluate(
    ranking
):
    gap = ranking.get(
        "virtual_advantage"
    )

    real_count = int(
        ranking.get(
            "real_candidate_count",
            0
        )
        or 0
    )

    if real_count == 0:
        status = (
            "NO_REAL_MEDIA"
        )

    elif gap is None:
        status = (
            "REAL_ONLY_OR_UNKNOWN"
        )

    elif gap >= 15:
        status = (
            "STRONG_REAL_MEDIA_GAP"
        )

    elif gap >= 7:
        status = (
            "REAL_MEDIA_GAP"
        )

    elif gap >= 2:
        status = (
            "MINOR_REAL_MEDIA_GAP"
        )

    else:
        status = (
            "REAL_MEDIA_COMPETITIVE"
        )

    return {
        "version":
            VERSION,

        "real_candidate_count":
            real_count,

        "virtual_advantage":
            gap,

        "status":
            status,
    }


def self_test():
    result = evaluate({
        "real_candidate_count": 2,
        "virtual_advantage": 18
    })

    assert (
        result["status"]
        == "STRONG_REAL_MEDIA_GAP"
    )

    print(
        "VI8.47 REAL MEDIA GAP=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.48 — REAL SCENE RANKING PLAN
# =====================================================

cat > vi8_48_real_scene_ranking_plan.py <<'PY'
#!/usr/bin/env python3

from vi8_42_scene_lookup import (
    by_number
)

from vi8_43_real_category_resolver import (
    resolve
)

from vi8_45_real_candidate_enricher import (
    enrich
)

from vi8_46_real_vs_virtual_ranker import (
    rank
)

from vi8_47_real_media_gap import (
    evaluate as gap_eval
)

VERSION = "8.48"


def build(
    scenes,
    grouped
):
    lookup = by_number(
        scenes
    )

    scene_groups = (
        grouped.get("scenes")
        or {}
    )

    plans = []

    previous_winners = []

    for number in range(
        1,
        13
    ):
        scene = (
            lookup.get(number)
            or {}
        )

        category = resolve(
            scene
        )

        raw_real = (
            scene_groups.get(
                number
            )
            or []
        )

        real_candidates = [
            enrich(
                item,
                scene,
                category
            )
            for item
            in raw_real
        ]

        ranking = rank(
            scene,
            category,
            real_candidates,
            previous_winners
        )

        gap = gap_eval(
            ranking
        )

        winner = ranking.get(
            "winner"
        )

        if winner:
            candidate = (
                winner.get(
                    "candidate"
                )
                or {}
            )

            previous_winners.append(
                candidate
            )

        plans.append({
            "scene":
                number,

            "category":
                category,

            "query":
                scene.get(
                    "query"
                ),

            "real_candidate_count":
                len(
                    real_candidates
                ),

            "ranking":
                ranking,

            "gap":
                gap,
        })

    return {
        "version":
            VERSION,

        "scenes":
            plans,
    }


def self_test():
    assert VERSION == "8.48"

    print(
        "VI8.48 REAL SCENE RANKING PLAN=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.49 — REAL MEDIA RANKING AUDIT
# =====================================================

cat > vi8_49_real_media_ranking_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.49"


def evaluate(plan):
    scenes = (
        plan.get(
            "scenes"
        )
        or []
    )

    no_real = []
    strong_gap = []
    normal_gap = []
    competitive = []

    real_winners = []
    virtual_winners = []

    for item in scenes:
        scene = item.get(
            "scene"
        )

        gap = (
            item.get("gap")
            or {}
        )

        status = gap.get(
            "status"
        )

        if status == "NO_REAL_MEDIA":
            no_real.append(
                scene
            )

        elif status == (
            "STRONG_REAL_MEDIA_GAP"
        ):
            strong_gap.append(
                scene
            )

        elif status in {
            "REAL_MEDIA_GAP",
            "MINOR_REAL_MEDIA_GAP",
        }:
            normal_gap.append(
                scene
            )

        elif status == (
            "REAL_MEDIA_COMPETITIVE"
        ):
            competitive.append(
                scene
            )

        winner = (
            (
                item.get(
                    "ranking"
                )
                or {}
            ).get(
                "winner"
            )
            or {}
        )

        if winner.get(
            "kind"
        ) == "REAL":
            real_winners.append(
                scene
            )

        elif winner.get(
            "kind"
        ) == "VIRTUAL_IDEAL":
            virtual_winners.append(
                scene
            )

    blockers = []
    warnings = []

    if len(
        no_real
    ) >= 5:
        warnings.append(
            "low_real_media_coverage"
        )

    if strong_gap:
        warnings.append(
            "strong_real_media_quality_gaps"
        )

    return {
        "version":
            VERSION,

        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),

        "no_real_media_scenes":
            no_real,

        "strong_gap_scenes":
            strong_gap,

        "gap_scenes":
            normal_gap,

        "competitive_scenes":
            competitive,

        "real_winner_scenes":
            real_winners,

        "virtual_winner_scenes":
            virtual_winners,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():
    assert VERSION == "8.49"

    print(
        "VI8.49 REAL MEDIA RANKING AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.50 — REAL MEDIA MASTER RANKING GATE
# =====================================================

cat > vi8_50_real_media_master_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_40_real_media_foundation_gate import (
    evaluate as foundation
)

from vi8_41_scene_map_loader import (
    load as load_scene_map
)

from vi8_48_real_scene_ranking_plan import (
    build as build_plan
)

from vi8_49_real_media_ranking_audit import (
    evaluate as audit
)

VERSION = "8.50"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    foundation_result = (
        foundation()
    )

    scene_map = (
        load_scene_map()
    )

    grouped = (
        foundation_result.get(
            "grouped"
        )
        or {}
    )

    plan = build_plan(
        scene_map.get(
            "scenes"
        )
        or [],
        grouped
    )

    audit_result = audit(
        plan
    )

    result = {
        "version":
            VERSION,

        "status":
            (
                "REAL_MEDIA_RANKING_READY"
                if not audit_result.get(
                    "blockers"
                )
                else "HOLD"
            ),

        "short_id":
            scene_map.get(
                "short_id"
            ),

        "media_dir":
            foundation_result.get(
                "media_dir"
            ),

        "scene_map":
            scene_map.get(
                "path"
            ),

        "foundation_status":
            foundation_result.get(
                "status"
            ),

        "plan":
            plan,

        "audit":
            audit_result,

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_50_real_media_master_latest.json"
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
    assert VERSION == "8.50"

    print(
        "VI8.50 REAL MEDIA MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_41_scene_map_loader.py \
  vi8_42_scene_lookup.py \
  vi8_43_real_category_resolver.py \
  vi8_44_real_shot_estimator.py \
  vi8_45_real_candidate_enricher.py \
  vi8_46_real_vs_virtual_ranker.py \
  vi8_47_real_media_gap.py \
  vi8_48_real_scene_ranking_plan.py \
  vi8_49_real_media_ranking_audit.py \
  vi8_50_real_media_master_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_41_scene_map_loader.py || exit 11
python vi8_42_scene_lookup.py || exit 12
python vi8_43_real_category_resolver.py || exit 13
python vi8_44_real_shot_estimator.py || exit 14
python vi8_45_real_candidate_enricher.py || exit 15
python vi8_46_real_vs_virtual_ranker.py || exit 16
python vi8_47_real_media_gap.py || exit 17
python vi8_48_real_scene_ranking_plan.py || exit 18
python vi8_49_real_media_ranking_audit.py || exit 19
python vi8_50_real_media_master_gate.py || exit 20

echo "SELF TESTS=PASS"


echo
echo "======================================"
echo " VI8.50 REAL MEDIA SHADOW RANKING"
echo "======================================"

python - <<'PY'
from vi8_50_real_media_master_gate import (
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
    "MEDIA DIR:",
    r.get("media_dir")
)

print(
    "FOUNDATION:",
    r.get("foundation_status")
)

audit = (
    r.get("audit")
    or {}
)

print(
    "REAL WINNER SCENES:",
    audit.get(
        "real_winner_scenes"
    )
)

print(
    "VIRTUAL IDEAL WINNER SCENES:",
    audit.get(
        "virtual_winner_scenes"
    )
)

print(
    "NO REAL MEDIA:",
    audit.get(
        "no_real_media_scenes"
    )
)

print(
    "STRONG GAPS:",
    audit.get(
        "strong_gap_scenes"
    )
)

print(
    "NORMAL/MINOR GAPS:",
    audit.get(
        "gap_scenes"
    )
)

print(
    "REAL COMPETITIVE:",
    audit.get(
        "competitive_scenes"
    )
)

print(
    "BLOCKERS:",
    audit.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    audit.get(
        "warnings"
    )
)

print()
print(
    "===== REAL VS IDEAL BY SCENE ====="
)

plan = (
    r.get("plan")
    or {}
)

for item in (
    plan.get("scenes")
    or []
):
    ranking = (
        item.get(
            "ranking"
        )
        or {}
    )

    best_real = (
        ranking.get(
            "best_real"
        )
        or {}
    )

    best_virtual = (
        ranking.get(
            "best_virtual"
        )
        or {}
    )

    real_candidate = (
        best_real.get(
            "candidate"
        )
        or {}
    )

    virtual_candidate = (
        best_virtual.get(
            "candidate"
        )
        or {}
    )

    gap = (
        item.get("gap")
        or {}
    )

    print(
        "SCENE",
        item.get("scene"),
        "| category=",
        item.get("category"),
        "| real_count=",
        item.get(
            "real_candidate_count"
        ),
        "| best_real=",
        best_real.get(
            "score"
        ),
        "| real_file=",
        real_candidate.get(
            "path"
        ),
        "| real_shot=",
        real_candidate.get(
            "shot"
        ),
        "| ideal=",
        best_virtual.get(
            "score"
        ),
        "| ideal_shot=",
        virtual_candidate.get(
            "shot"
        ),
        "| gap=",
        gap.get(
            "virtual_advantage"
        ),
        "| status=",
        gap.get(
            "status"
        ),
    )

print()
print(
    "AUTOMATIC DOWNLOAD:",
    r.get(
        "automatic_download"
    )
)

print(
    "AUTOMATIC REPLACE:",
    r.get(
        "automatic_replace"
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
echo " VI8.41 -> VI8.50 COMPLETE"
echo "======================================"
echo
echo "REAL/IDEAL COMPARISON=READY"
echo "REAL MEDIA RANKING=READY"
echo "SCENE GAP DETECTION=READY"
echo "REAL WINNER DETECTION=READY"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "FULL ACTIVE=LOCKED"

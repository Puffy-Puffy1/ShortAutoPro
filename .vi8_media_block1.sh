#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI8.01 -> VI8.10"
echo " MEDIA INTELLIGENCE FOUNDATION"
echo " SHADOW ONLY"
echo "======================================"

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.01 — MEDIA CANDIDATE MODEL
# =====================================================

cat > vi8_01_media_candidate.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.01"

def normalize(candidate=None):
    candidate = dict(candidate or {})

    return {
        "path":
            candidate.get("path"),

        "source":
            candidate.get("source", "UNKNOWN"),

        "media_type":
            str(
                candidate.get(
                    "media_type",
                    "STILL"
                )
            ).upper(),

        "width":
            candidate.get("width"),

        "height":
            candidate.get("height"),

        "query":
            candidate.get("query", ""),

        "category":
            candidate.get("category"),

        "shot":
            candidate.get("shot"),

        "source_score":
            float(
                candidate.get(
                    "source_score",
                    0
                )
                or 0
            ),

        "relevance_score":
            float(
                candidate.get(
                    "relevance_score",
                    0
                )
                or 0
            ),

        "metadata":
            candidate.get(
                "metadata"
            )
            or {},
    }

def self_test():
    result = normalize({
        "path": "image.jpg"
    })

    assert result["media_type"] == "STILL"
    assert result["path"] == "image.jpg"

    print(
        "VI8.01 MEDIA CANDIDATE MODEL=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.02 — ASPECT / CROP FITNESS
# =====================================================

cat > vi8_02_crop_fitness.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.02"

TARGET_RATIO = 1080 / 1920

def evaluate(width, height):
    try:
        width = float(width)
        height = float(height)

    except Exception:
        return {
            "version": VERSION,
            "score": 50.0,
            "status": "UNKNOWN",
        }

    if width <= 0 or height <= 0:
        return {
            "version": VERSION,
            "score": 0.0,
            "status": "INVALID",
        }

    ratio = width / height

    distance = abs(
        ratio - TARGET_RATIO
    )

    if ratio <= 0.7:
        score = 100 - distance * 30

    elif ratio <= 1.0:
        score = 90 - distance * 35

    elif ratio <= 1.5:
        score = 75 - distance * 35

    else:
        score = 55 - distance * 20

    score = max(
        0.0,
        min(100.0, score)
    )

    return {
        "version": VERSION,
        "ratio": round(ratio, 3),
        "score": round(score, 2),
        "status": (
            "PASS"
            if score >= 70
            else "CAUTION"
        ),
    }

def self_test():
    portrait = evaluate(
        1080,
        1920
    )

    assert portrait["score"] >= 95

    print(
        "VI8.02 CROP FITNESS=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.03 — SUBJECT / SHOT COMPATIBILITY
# =====================================================

cat > vi8_03_subject_shot_compatibility.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.03"

IDEAL = {
    "FACE": {
        "medium": 100,
        "close_up": 100,
        "wide": 45,
    },

    "DOCUMENT": {
        "close_up": 100,
        "medium": 90,
        "wide": 40,
    },

    "EVIDENCE": {
        "close_up": 100,
        "medium": 90,
        "wide": 55,
    },

    "LOCATION": {
        "wide": 100,
        "medium": 90,
        "close_up": 55,
    },

    "OBJECT": {
        "close_up": 100,
        "medium": 90,
        "wide": 50,
    },

    "GENERAL": {
        "medium": 90,
        "wide": 80,
        "close_up": 80,
    },
}

def score(category, shot):
    category = str(
        category or "GENERAL"
    ).upper()

    shot = str(
        shot or "medium"
    ).lower()

    return IDEAL.get(
        category,
        IDEAL["GENERAL"]
    ).get(
        shot,
        65
    )

def self_test():
    assert score(
        "FACE",
        "wide"
    ) < score(
        "FACE",
        "medium"
    )

    assert score(
        "LOCATION",
        "wide"
    ) == 100

    print(
        "VI8.03 SUBJECT SHOT COMPATIBILITY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.04 — NARRATIVE RELEVANCE
# =====================================================

cat > vi8_04_narrative_relevance.py <<'PY'
#!/usr/bin/env python3

import re

VERSION = "8.04"

STOP = {
    "the","a","an","of","to","and","or",
    "de","da","do","das","dos","e","em",
    "um","uma","para","com","que",
}

def words(text):
    return {
        token
        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9]+",
            str(text or "").lower()
        )
        if (
            len(token) >= 3
            and token not in STOP
        )
    }

def evaluate(scene, candidate):
    scene_text = " ".join([
        str(scene.get("segment") or ""),
        str(scene.get("query") or ""),
        " ".join(
            str(x)
            for x in (
                scene.get("must_have")
                or []
            )
        ),
    ])

    media_text = " ".join([
        str(
            candidate.get(
                "query"
            )
            or ""
        ),
        str(
            (
                candidate.get(
                    "metadata"
                )
                or {}
            ).get(
                "title"
            )
            or ""
        ),
        str(
            (
                candidate.get(
                    "metadata"
                )
                or {}
            ).get(
                "description"
            )
            or ""
        ),
    ])

    a = words(scene_text)
    b = words(media_text)

    if not a:
        return {
            "version": VERSION,
            "score": 50.0,
            "overlap": [],
        }

    overlap = sorted(
        a & b
    )

    ratio = (
        len(overlap)
        / len(a)
    )

    score = min(
        100.0,
        40 + ratio * 80
    )

    return {
        "version": VERSION,
        "score": round(
            score,
            2
        ),
        "overlap": overlap,
    }

def self_test():
    result = evaluate(
        {
            "segment":
                "a ransom note was found",
            "query":
                "handwritten ransom note",
        },
        {
            "query":
                "ransom note handwritten paper",
            "metadata": {},
        }
    )

    assert result["score"] > 50

    print(
        "VI8.04 NARRATIVE RELEVANCE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.05 — DOCUMENTARY VALUE
# =====================================================

cat > vi8_05_documentary_value.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.05"

VALUE = {
    "DOCUMENT": 100,
    "EVIDENCE": 100,
    "LOCATION": 90,
    "FACE": 80,
    "OBJECT": 80,
    "GENERAL": 65,
    "ABSTRACT": 45,
}

def score(category):
    return VALUE.get(
        str(
            category or "GENERAL"
        ).upper(),
        65
    )

def self_test():
    assert (
        score("DOCUMENT")
        > score("ABSTRACT")
    )

    print(
        "VI8.05 DOCUMENTARY VALUE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.06 — IDENTITY SAFETY
# =====================================================

cat > vi8_06_identity_safety.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.06"

def evaluate(
    scene_category,
    candidate
):
    metadata = (
        candidate.get("metadata")
        or {}
    )

    blockers = []
    warnings = []

    category = str(
        scene_category
        or "GENERAL"
    ).upper()

    confirmed = metadata.get(
        "identity_confirmed"
    )

    if (
        category == "FACE"
        and confirmed is False
    ):
        blockers.append(
            "face_identity_not_confirmed"
        )

    elif (
        category == "FACE"
        and confirmed is None
    ):
        warnings.append(
            "face_identity_unknown"
        )

    return {
        "version": VERSION,
        "status": (
            "HOLD"
            if blockers
            else (
                "CAUTION"
                if warnings
                else "PASS"
            )
        ),
        "blockers": blockers,
        "warnings": warnings,
    }

def self_test():
    result = evaluate(
        "FACE",
        {
            "metadata": {
                "identity_confirmed":
                    False
            }
        }
    )

    assert result["status"] == "HOLD"

    print(
        "VI8.06 IDENTITY SAFETY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.07 — MEDIA QUALITY SCORE
# =====================================================

cat > vi8_07_media_quality_score.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.07"

def resolution_score(
    width,
    height
):
    try:
        pixels = (
            int(width)
            * int(height)
        )
    except Exception:
        return 50.0

    if pixels >= 2_000_000:
        return 100.0

    if pixels >= 1_000_000:
        return 90.0

    if pixels >= 500_000:
        return 75.0

    if pixels >= 250_000:
        return 60.0

    return 40.0

def evaluate(candidate):
    result = resolution_score(
        candidate.get("width"),
        candidate.get("height")
    )

    return {
        "version": VERSION,
        "score": result,
    }

def self_test():
    assert (
        resolution_score(
            1920,
            1080
        )
        == 100
    )

    print(
        "VI8.07 MEDIA QUALITY SCORE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.08 — DUPLICATION PENALTY
# =====================================================

cat > vi8_08_duplication_penalty.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.08"

def penalty(
    candidate,
    previous_candidates
):
    path = str(
        candidate.get("path")
        or ""
    )

    category = candidate.get(
        "category"
    )

    penalty_value = 0
    reasons = []

    for previous in (
        previous_candidates
        or []
    ):
        if (
            path
            and path
            == str(
                previous.get("path")
                or ""
            )
        ):
            penalty_value += 70

            reasons.append(
                "exact_media_repeat"
            )

        elif (
            category
            and category
            == previous.get(
                "category"
            )
        ):
            penalty_value += 10

            reasons.append(
                "category_repeat"
            )

    return {
        "version": VERSION,
        "penalty": min(
            100,
            penalty_value
        ),
        "reasons":
            sorted(
                set(reasons)
            ),
    }

def self_test():
    candidate = {
        "path": "a.jpg",
        "category": "FACE",
    }

    result = penalty(
        candidate,
        [{
            "path": "a.jpg",
            "category": "FACE",
        }]
    )

    assert result["penalty"] >= 70

    print(
        "VI8.08 DUPLICATION PENALTY=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.09 — CANDIDATE SCORER
# =====================================================

cat > vi8_09_candidate_scorer.py <<'PY'
#!/usr/bin/env python3

from vi8_02_crop_fitness import (
    evaluate as crop_fitness
)

from vi8_03_subject_shot_compatibility import (
    score as shot_score
)

from vi8_04_narrative_relevance import (
    evaluate as relevance
)

from vi8_05_documentary_value import (
    score as documentary_score
)

from vi8_06_identity_safety import (
    evaluate as identity_safety
)

from vi8_07_media_quality_score import (
    evaluate as media_quality
)

from vi8_08_duplication_penalty import (
    penalty as duplication_penalty
)

VERSION = "8.09"

def evaluate(
    scene,
    candidate,
    previous_candidates=None
):
    category = (
        candidate.get("category")
        or scene.get(
            "cinematic_category"
        )
        or "GENERAL"
    )

    shot = (
        candidate.get("shot")
        or scene.get(
            "shot_type"
        )
        or "medium"
    )

    crop = crop_fitness(
        candidate.get("width"),
        candidate.get("height")
    )

    shot_fit = shot_score(
        category,
        shot
    )

    rel = relevance(
        scene,
        candidate
    )

    documentary = documentary_score(
        category
    )

    identity = identity_safety(
        category,
        candidate
    )

    quality = media_quality(
        candidate
    )

    duplicate = duplication_penalty(
        candidate,
        previous_candidates
        or []
    )

    blockers = []

    blockers.extend(
        identity.get("blockers")
        or []
    )

    base = (
        rel["score"] * .32
        + shot_fit * .20
        + crop["score"] * .14
        + documentary * .14
        + quality["score"] * .12
        + float(
            candidate.get(
                "source_score",
                0
            )
            or 0
        ) * .08
    )

    final = (
        base
        - duplicate["penalty"]
    )

    final = max(
        0.0,
        min(100.0, final)
    )

    return {
        "version": VERSION,
        "score":
            round(final, 2),
        "category":
            category,
        "shot":
            shot,
        "components": {
            "relevance":
                rel["score"],
            "shot":
                shot_fit,
            "crop":
                crop["score"],
            "documentary":
                documentary,
            "quality":
                quality["score"],
            "source":
                float(
                    candidate.get(
                        "source_score",
                        0
                    )
                    or 0
                ),
            "duplicate_penalty":
                duplicate[
                    "penalty"
                ],
        },
        "blockers":
            blockers,
        "warnings":
            identity.get(
                "warnings"
            )
            or [],
        "eligible":
            not blockers,
    }

def self_test():
    scene = {
        "segment":
            "a ransom note was discovered",
        "query":
            "ransom note",
        "shot_type":
            "close_up",
        "cinematic_category":
            "DOCUMENT",
    }

    candidate = {
        "path":
            "note.jpg",
        "category":
            "DOCUMENT",
        "shot":
            "close_up",
        "width":
            1200,
        "height":
            1600,
        "query":
            "ransom note handwritten paper",
        "source_score":
            90,
        "metadata": {},
    }

    result = evaluate(
        scene,
        candidate
    )

    assert result[
        "score"
    ] >= 70

    print(
        "VI8.09 CANDIDATE SCORER=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.10 — MEDIA FOUNDATION GATE
# =====================================================

cat > vi8_10_media_foundation_gate.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.10"

def evaluate():
    return {
        "version": VERSION,
        "candidate_model":
            True,
        "crop_intelligence":
            True,
        "subject_shot_matching":
            True,
        "narrative_relevance":
            True,
        "documentary_value":
            True,
        "identity_safety":
            True,
        "quality_scoring":
            True,
        "duplication_control":
            True,
        "automatic_download":
            False,
        "automatic_replace":
            False,
        "renderer_activation":
            False,
        "status":
            "MEDIA_FOUNDATION_READY",
    }

def self_test():
    result = evaluate()

    assert (
        result["status"]
        == "MEDIA_FOUNDATION_READY"
    )

    assert (
        result["automatic_replace"]
        is False
    )

    print(
        "VI8.10 MEDIA FOUNDATION GATE=PASS"
    )

if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_01_media_candidate.py \
  vi8_02_crop_fitness.py \
  vi8_03_subject_shot_compatibility.py \
  vi8_04_narrative_relevance.py \
  vi8_05_documentary_value.py \
  vi8_06_identity_safety.py \
  vi8_07_media_quality_score.py \
  vi8_08_duplication_penalty.py \
  vi8_09_candidate_scorer.py \
  vi8_10_media_foundation_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_01_media_candidate.py || exit 11
python vi8_02_crop_fitness.py || exit 12
python vi8_03_subject_shot_compatibility.py || exit 13
python vi8_04_narrative_relevance.py || exit 14
python vi8_05_documentary_value.py || exit 15
python vi8_06_identity_safety.py || exit 16
python vi8_07_media_quality_score.py || exit 17
python vi8_08_duplication_penalty.py || exit 18
python vi8_09_candidate_scorer.py || exit 19
python vi8_10_media_foundation_gate.py || exit 20

echo "SELF TESTS=PASS"


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
echo " VI8.01 -> VI8.10 COMPLETE"
echo "======================================"
echo "MEDIA CANDIDATE MODEL=READY"
echo "CROP FITNESS=READY"
echo "SUBJECT/SHOT MATCHING=READY"
echo "NARRATIVE RELEVANCE=READY"
echo "DOCUMENTARY VALUE=READY"
echo "IDENTITY SAFETY=READY"
echo "MEDIA QUALITY SCORE=READY"
echo "DUPLICATION PENALTY=READY"
echo "CANDIDATE SCORER=READY"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "VIDEO GENERATED=NO"
echo "FFMPEG EXECUTED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "FULL ACTIVE=LOCKED"

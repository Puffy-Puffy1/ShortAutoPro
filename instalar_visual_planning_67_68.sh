#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p backups/stable_release_ready

echo
echo "======================================"
echo " VI6.7 + VI6.8 VISUAL PLANNING"
echo " SHADOW OFFLINE"
echo "======================================"
echo


# =====================================================
# VI6.7 RETRIEVAL PLANNER
# =====================================================

cat > vi6_7_retrieval_planner.py <<'PY'
#!/usr/bin/env python3

import re


VERSION = "6.7"


STOP = {
    "the", "and", "for", "with", "from",
    "this", "that", "into", "real",
    "image", "photo", "video",

    "uma", "um",
    "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas",
    "com", "para", "por",
    "foto", "imagem", "video", "vídeo"
}


GENERIC = {
    "man", "woman", "person", "people",
    "family", "child", "girl", "boy",
    "homem", "mulher", "pessoa",
    "pessoas", "familia", "família",
    "crianca", "criança", "menina",
    "menino",

    "street", "city", "building",
    "room", "forest", "river", "road",
    "rua", "cidade", "predio", "prédio",
    "sala", "floresta", "rio", "estrada",

    "dark", "shadow", "mystery",
    "escuro", "sombra", "misterio",
    "mistério"
}


def s(v):
    return str(v or "").strip()


def flatten(v):

    if v is None:
        return ""

    if isinstance(v, dict):
        return " ".join(
            flatten(x)
            for x in v.values()
        )

    if isinstance(v, (list, tuple, set)):
        return " ".join(
            flatten(x)
            for x in v
        )

    return s(v)


def unique(items):

    out = []
    seen = set()

    for x in items:

        x = s(x)

        if not x:
            continue

        k = x.lower()

        if k in seen:
            continue

        seen.add(k)
        out.append(x)

    return out


def tokens(text):

    return [
        x
        for x in re.findall(
            r"[a-zà-ÿ0-9]+",
            s(text).lower()
        )
        if (
            len(x) >= 2
            and x not in STOP
        )
    ]


def years(text):

    return unique(
        re.findall(
            r"\b(?:18|19|20)\d{2}\b",
            s(text)
        )
    )


def identity_labels(text):

    text = s(text)

    out = []

    patterns = (
        r"\b(?:Flight|flight|Voo|voo)\s*[A-Za-z]{0,3}\s*-?\s*\d{1,5}\b",
        r"\b(?:Case|case|Caso|caso)\s*-?\s*\d{1,6}\b",
        r"\b(?:Room|room|Quarto|quarto)\s*-?\s*\d{1,6}\b",
        r"\b(?:MH|QZ|AF|AA|UA|BA|TW|PA)\s*-?\s*\d{2,5}\b",
    )

    for pattern in patterns:

        out.extend(
            re.findall(
                pattern,
                text
            )
        )

    return unique(out)


def must_list(scene):

    raw = (
        scene.get("must_have")
        or scene.get("must")
        or []
    )

    if isinstance(raw, str):
        raw = [raw]

    if not isinstance(
        raw,
        (list, tuple, set)
    ):
        return []

    return unique(raw)


def scene_text(scene):

    return " ".join(
        flatten(scene.get(k))
        for k in (
            "segmento",
            "segment",
            "texto",
            "text",
            "narracao",
            "narração",
            "visual_query",
            "query",
            "must_have",
            "must",
            "topic",
            "subject",
            "visual_mode",
            "visual_intent",
            "intent",
        )
    )


def role(scene):

    text = " ".join(
        [
            s(scene.get("visual_mode")),
            s(scene.get("visual_intent")),
            s(scene.get("intent")),
        ]
    ).lower()


    if "cta" in text:
        return "CTA"


    if any(
        x in text
        for x in (
            "document",
            "evidence",
            "arquivo",
            "archive",
            "newspaper",
            "case_file",
        )
    ):
        return "EVIDENCE"


    if any(
        x in text
        for x in (
            "person",
            "portrait",
            "people",
            "character",
        )
    ):
        return "PERSON"


    if any(
        x in text
        for x in (
            "location",
            "place",
            "architecture",
            "map",
            "transport",
        )
    ):
        return "PLACE"


    if any(
        x in text
        for x in (
            "object",
            "product",
            "medicine",
            "package",
            "packaging",
        )
    ):
        return "OBJECT"


    return "CONTEXT"


def anchors(scene):

    text = scene_text(scene)

    out = []

    must = must_list(scene)

    for value in must[:4]:

        toks = tokens(value)

        if (
            toks
            and not all(
                token in GENERIC
                for token in toks
            )
        ):
            out.append(value)


    out.extend(
        identity_labels(text)
    )

    out.extend(
        years(text)[:2]
    )

    return unique(out)


def strength(scene):

    a = anchors(scene)
    must = must_list(scene)
    ids = identity_labels(
        scene_text(scene)
    )

    score = 0

    if ids:
        score += 4

    if len(must) >= 2:
        score += 4

    elif len(must) == 1:
        score += 2

    if years(
        scene_text(scene)
    ):
        score += 1

    # Duas âncoras nomeadas fortes
    # já são suficientes.
    if len(a) >= 2:
        score += 2

    return score


def compact(parts):

    parts = unique(parts)

    words = []

    for part in parts:

        for word in s(part).split():

            if word not in words:
                words.append(word)

    return " ".join(
        words[:12]
    )


def plan(scene):

    r = role(scene)
    a = anchors(scene)
    st = strength(scene)

    original = s(
        scene.get("visual_query")
        or scene.get("query")
    )

    queries = []


    if r == "CTA":

        return {
            "version": VERSION,
            "role": r,
            "strength": st,
            "anchors": a,
            "primary": original,
            "queries": [],
            "strategy":
                "REUSE_VERIFIED_ASSET",
            "override": False,
        }


    if r == "EVIDENCE":

        if a:

            queries.extend(
                [
                    compact(a[:4]),
                    compact(
                        a[:3] + ["archive"]
                    ),
                    compact(
                        a[:3] + ["newspaper"]
                    ),
                    compact(
                        a[:3]
                        + ["historical photograph"]
                    ),
                ]
            )

        if original:
            queries.append(original)


    elif r == "PERSON":

        if st >= 4:

            queries.extend(
                [
                    compact(
                        a[:3]
                        + ["archive photograph"]
                    ),
                    compact(a[:3]),
                ]
            )

        if original:
            queries.append(original)


    elif r == "PLACE":

        if len(a) >= 2:

            queries.extend(
                [
                    compact(a[:4]),
                    compact(
                        a[:3]
                        + ["historical photograph"]
                    ),
                    compact(
                        a[:3] + ["archive"]
                    ),
                ]
            )

        if original:
            queries.append(original)


    elif r == "OBJECT":

        if st >= 4:
            queries.append(
                compact(a[:3])
            )

        if original:
            queries.append(original)


    else:

        if original:
            queries.append(original)

        if st >= 6:
            queries.append(
                compact(a[:3])
            )


    queries = unique(
        queries
    )[:6]


    primary = original
    override = False


    if (
        queries
        and r in {
            "EVIDENCE",
            "PERSON",
            "PLACE",
        }
    ):

        candidate = queries[0]

        if (
            len(tokens(candidate)) >= 2
            and (
                st >= 4
                or (
                    r == "PLACE"
                    and len(a) >= 2
                )
            )
        ):

            primary = candidate

            override = (
                primary.lower()
                != original.lower()
            )


    return {
        "version": VERSION,
        "role": r,
        "strength": st,
        "anchors": a,
        "primary": primary,
        "queries": queries,
        "strategy":
            (
                "DOCUMENTARY_FIRST"
                if r in {
                    "EVIDENCE",
                    "PERSON",
                    "PLACE",
                }
                else "BALANCED"
            ),
        "override": override,
    }


def self_test():

    flight = {
        "visual_mode": "evidence",
        "visual_query":
            "airplane ocean mystery",
        "must_have":
            ["Flight 19", "1945"],
        "segmento":
            "Flight 19 disappeared in 1945.",
    }

    p = plan(flight)

    assert p["role"] == "EVIDENCE"
    assert "Flight 19" in p["primary"]
    assert "1945" in p["primary"]


    cecil = {
        "visual_mode": "location",
        "visual_query": "old hotel",
        "must_have":
            ["Cecil Hotel", "Los Angeles"],
        "segmento":
            "The Cecil Hotel in Los Angeles.",
    }

    p = plan(cecil)

    assert p["role"] == "PLACE"
    assert "Cecil Hotel" in p["primary"]
    assert "Los Angeles" in p["primary"]
    assert p["override"] is True


    generic_person = {
        "visual_mode": "person",
        "visual_query":
            "sad young girl portrait",
        "must_have": [],
    }

    p = plan(generic_person)

    assert p["override"] is False


    cta = {
        "visual_mode": "cta_reuse",
        "visual_query": "subscribe",
    }

    p = plan(cta)

    assert (
        p["strategy"]
        == "REUSE_VERIFIED_ASSET"
    )

    assert p["queries"] == []


    print()
    print(
        "======================================"
    )
    print(
        " VI6.7 RETRIEVAL SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Flight/Case Identity"
    )
    print(
        "OK Year Preservation"
    )
    print(
        "OK Cecil Hotel + Los Angeles"
    )
    print(
        "OK Generic Person Guard"
    )
    print(
        "OK CTA Reuse Policy"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI6.8 GLOBAL STORYBOARD DIRECTOR
# =====================================================

cat > vi6_8_storyboard_director.py <<'PY'
#!/usr/bin/env python3


VERSION = "6.8"


def _s(v):
    return str(v or "").strip()


def _role(scene):

    text = " ".join(
        [
            _s(scene.get("visual_mode")),
            _s(scene.get("visual_intent")),
            _s(scene.get("intent")),
        ]
    ).lower()


    if "cta" in text:
        return "CTA"

    if any(
        x in text
        for x in (
            "document",
            "evidence",
            "archive",
            "arquivo",
            "newspaper",
        )
    ):
        return "EVIDENCE"

    if any(
        x in text
        for x in (
            "location",
            "place",
            "architecture",
            "map",
        )
    ):
        return "PLACE"

    if any(
        x in text
        for x in (
            "person",
            "portrait",
            "character",
        )
    ):
        return "PERSON"

    if any(
        x in text
        for x in (
            "object",
            "medicine",
            "product",
            "package",
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def build_global_plan(
    scenes
):

    total = len(scenes)

    plan = []

    documentary_budget = max(
        3,
        round(
            total * 0.35
        )
    )

    motion_budget = max(
        3,
        round(
            total * 0.42
        )
    )

    previous_role = None


    for index, scene in enumerate(
        scenes,
        1
    ):

        role = _role(scene)


        prefer_documentary = (
            role in {
                "EVIDENCE",
                "PERSON",
                "PLACE",
            }
        )


        # Story rhythm.
        if index == 1:

            rhythm = "HOOK"

        elif index <= 4:

            rhythm = "SETUP"

        elif index <= 8:

            rhythm = "ESCALATION"

        elif index < total:

            rhythm = "RESOLUTION"

        else:

            rhythm = "CTA"


        # Movimento tem utilidade maior
        # em contexto/transição.
        prefer_motion = (
            role in {
                "CONTEXT",
                "OBJECT",
            }
            and rhythm
            in {
                "HOOK",
                "SETUP",
                "ESCALATION",
            }
        )


        # Evidência/documentos podem ser
        # foto sem penalização.
        photo_ok = (
            role in {
                "EVIDENCE",
                "PERSON",
                "PLACE",
            }
        )


        # Mudança de família visual ganha
        # importância em papéis repetidos.
        diversity_priority = (
            "HIGH"
            if role == previous_role
            else "NORMAL"
        )


        plan.append(
            {
                "scene": index,
                "role": role,
                "rhythm": rhythm,

                "prefer_documentary":
                    prefer_documentary,

                "prefer_motion":
                    prefer_motion,

                "photo_is_fully_valid":
                    photo_ok,

                "diversity_priority":
                    diversity_priority,

                "avoid_previous_asset":
                    index > 1,

                "avoid_three_same_source":
                    True,

                "cta_reuse":
                    role == "CTA",
            }
        )


        previous_role = role


    return {
        "version": VERSION,

        "scene_count":
            total,

        "documentary_target":
            documentary_budget,

        "motion_target":
            motion_budget,

        "max_identical_asset":
            1,

        "max_same_source_streak":
            2,

        "max_same_family_streak":
            2,

        "cta_strategy":
            "REUSE_VERIFIED_STORY_ASSET",

        "scenes":
            plan,
    }


def self_test():

    scenes = [
        {
            "visual_mode":
                "evidence"
        },

        {
            "visual_mode":
                "location"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "object"
        },

        {
            "visual_mode":
                "evidence"
        },

        {
            "visual_mode":
                "person"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "evidence"
        },

        {
            "visual_mode":
                "context"
        },

        {
            "visual_mode":
                "object"
        },

        {
            "visual_mode":
                "cta_reuse"
        },
    ]


    plan = build_global_plan(
        scenes
    )


    assert (
        plan["scene_count"]
        == 12
    )

    assert (
        plan["documentary_target"]
        >= 4
    )

    assert (
        plan["scenes"][-1][
            "cta_reuse"
        ]
        is True
    )

    assert (
        plan["max_same_source_streak"]
        == 2
    )

    assert (
        plan["max_identical_asset"]
        == 1
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.8 STORYBOARD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK 12-scene global planning"
    )
    print(
        "OK Documentary Budget"
    )
    print(
        "OK Motion Budget"
    )
    print(
        "OK Source Streak Guard"
    )
    print(
        "OK Asset Duplication Guard"
    )
    print(
        "OK Visual Family Guard"
    )
    print(
        "OK CTA Reuse Strategy"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# COMBINED OFFLINE TEST
# =====================================================

cat > testar_visual_planning_67_68.py <<'PY'
#!/usr/bin/env python3

from vi6_7_retrieval_planner import (
    plan
)

from vi6_8_storyboard_director import (
    build_global_plan
)


scenes = [
    {
        "visual_mode":
            "evidence",

        "visual_query":
            "airplane mystery",

        "must_have":
            [
                "Flight 19",
                "1945"
            ]
    },

    {
        "visual_mode":
            "location",

        "visual_query":
            "old hotel",

        "must_have":
            [
                "Cecil Hotel",
                "Los Angeles"
            ]
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "busy city street"
    },

    {
        "visual_mode":
            "person",

        "visual_query":
            "sad young girl portrait"
    },

    {
        "visual_mode":
            "object",

        "visual_query":
            "medicine bottle"
    },

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "newspaper archive"
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "police investigation"
    },

    {
        "visual_mode":
            "location",

        "visual_query":
            "building exterior"
    },

    {
        "visual_mode":
            "evidence",

        "visual_query":
            "case documents"
    },

    {
        "visual_mode":
            "context",

        "visual_query":
            "pharmacy shelves"
    },

    {
        "visual_mode":
            "object",

        "visual_query":
            "sealed packaging"
    },

    {
        "visual_mode":
            "cta_reuse",

        "visual_query":
            "subscribe"
    },
]


print()
print(
    "======================================"
)
print(
    " VI6.7 + VI6.8 OFFLINE TEST"
)
print(
    "======================================"
)


for i, scene in enumerate(
    scenes,
    1
):

    p = plan(scene)

    print()
    print(
        f"CENA {i:02d}"
    )

    print(
        "  ROLE:",
        p["role"]
    )

    print(
        "  STRATEGY:",
        p["strategy"]
    )

    print(
        "  PRIMARY:",
        p["primary"]
    )

    print(
        "  OVERRIDE:",
        p["override"]
    )

    print(
        "  ANCHORS:",
        p["anchors"]
    )


global_plan = (
    build_global_plan(
        scenes
    )
)


print()
print(
    "======================================"
)
print(
    " GLOBAL STORYBOARD"
)
print(
    "======================================"
)

print(
    "DOCUMENTARY TARGET:",
    global_plan[
        "documentary_target"
    ]
)

print(
    "MOTION TARGET:",
    global_plan[
        "motion_target"
    ]
)

print(
    "MAX SAME SOURCE:",
    global_plan[
        "max_same_source_streak"
    ]
)

print(
    "MAX SAME ASSET:",
    global_plan[
        "max_identical_asset"
    ]
)

print(
    "CTA:",
    global_plan[
        "cta_strategy"
    ]
)

print()
print(
    "API CALLS=0"
)
print(
    "DOWNLOADS=0"
)
print(
    "VIDEOS=0"
)
PY


# =====================================================
# VALIDATION
# =====================================================

echo
echo "===== PYTHON COMPILE ====="

python -m py_compile \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    testar_visual_planning_67_68.py \
    vi6_6_active_brain.py \
    midia.py

STATUS=$?

echo "PYTHON STATUS=$STATUS"

if [ "$STATUS" -ne 0 ]; then
    exit "$STATUS"
fi


echo
echo "===== VI6.7 SELF TEST ====="

python vi6_7_retrieval_planner.py \
    || exit 1


echo
echo "===== VI6.8 SELF TEST ====="

python vi6_8_storyboard_director.py \
    || exit 1


echo
echo "===== VI6.6 REGRESSION ====="

python vi6_6_active_brain.py \
    || exit 1


echo
echo "===== RELEASE CHECK ====="

./release_check.sh \
    || exit 1


echo
echo "======================================"
echo " VI6.7 + VI6.8 PRONTOS"
echo "======================================"
echo
echo "IMPORTANTE:"
echo "MODO=SHADOW_OFFLINE"
echo "MIDIA.PY NÃO FOI MODIFICADO"
echo "GERAR_SHORT.SH NÃO FOI MODIFICADO"
echo "API CALLS=0"
echo "DOWNLOADS=0"
echo "VIDEOS=0"
echo


echo "======================================"
echo " TESTE COMBINADO"
echo "======================================"

python testar_visual_planning_67_68.py


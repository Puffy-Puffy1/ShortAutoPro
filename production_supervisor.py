#!/usr/bin/env python3

import os
import json
import re
import glob
from datetime import date

from source_identity import validar_identidade


# =====================================================
# SHORTAUTO PRO
# PRODUCTION INTELLIGENCE SUPERVISOR 5.0
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

ROTEIROS = os.path.join(
    BASE,
    "roteiros"
)

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)


PATHS = {

    "topic_real":
        os.path.join(
            ROTEIROS,
            f"used_topic_{SHORT_ID}.txt"
        ),

    "topic":
        os.path.join(
            ROTEIROS,
            f"topic_{SHORT_ID}.txt"
        ),

    "script":
        os.path.join(
            ROTEIROS,
            f"short_{SHORT_ID}.txt"
        ),

    "source":
        os.path.join(
            ROTEIROS,
            f"fonte_{SHORT_ID}.txt"
        ),

    "scene_map":
        os.path.join(
            ROTEIROS,
            f"scene_map_{SHORT_ID}.json"
        ),

    "motion":
        os.path.join(
            ROTEIROS,
            f"motion_plan_{SHORT_ID}.json"
        ),

    "publish":
        os.path.join(
            ROTEIROS,
            f"publish_{SHORT_ID}.txt"
        ),

    "report":
        os.path.join(
            ROTEIROS,
            f"supervisor_{SHORT_ID}.json"
        )
}


# =====================================================
# HELPERS
# =====================================================

def ler_txt(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


def ler_json(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def palavras(texto):

    return re.findall(
        r"\b[\wÀ-ÿ'-]+\b",
        str(texto),
        flags=re.UNICODE
    )


def contar_palavras(texto):

    return len(
        palavras(
            texto
        )
    )


def normalizar(texto):

    return " ".join(
        re.findall(
            r"[a-z0-9à-ÿ]+",
            str(texto).lower()
        )
    )


def tokens(texto):

    stop = {
        "a", "o", "as", "os",
        "de", "da", "do",
        "das", "dos",
        "e", "em",
        "um", "uma",
        "the", "a", "of",
        "and", "in", "on",
        "cinematic",
        "dramatic",
        "dark",
        "vintage",
        "historic"
    }

    return {
        x
        for x in re.findall(
            r"[a-z0-9à-ÿ]+",
            str(texto).lower()
        )
        if (
            x not in stop
            and len(x) >= 3
        )
    }


def similaridade(
    a,
    b
):

    ta = tokens(a)
    tb = tokens(b)

    if not ta or not tb:
        return 0.0

    return (
        len(
            ta.intersection(tb)
        )
        / len(
            ta.union(tb)
        )
    )


def primeira_frase(texto):

    partes = re.split(
        r"(?<=[.!?])\s+",
        str(texto).strip()
    )

    if partes:
        return partes[0]

    return ""


def media_files():

    if not os.path.isdir(
        MEDIA_DIR
    ):
        return []

    saida = []

    for path in sorted(
        glob.glob(
            os.path.join(
                MEDIA_DIR,
                "scene_*"
            )
        )
    ):

        ext = os.path.splitext(
            path
        )[1].lower()

        if ext in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4"
        }:

            saida.append(
                path
            )

    return saida


# =====================================================
# INPUT
# =====================================================

topic = (
    ler_txt(
        PATHS["topic_real"]
    )
    or ler_txt(
        PATHS["topic"]
    )
)

script = ler_txt(
    PATHS["script"]
)

source_text = ler_txt(
    PATHS["source"]
)

scene_map = ler_json(
    PATHS["scene_map"]
)

motion = ler_json(
    PATHS["motion"]
)


# =====================================================
# SCORE
# =====================================================

score = 100

critical = []
warnings = []
strengths = []


# =====================================================
# 1. IDENTIDADE FACTUAL
# =====================================================

wiki_title = ""

m = re.search(
    r"Wikipedia\s*[—-]\s*(.+)",
    source_text,
    flags=re.IGNORECASE
)

if m:

    wiki_title = (
        m.group(1)
        .splitlines()[0]
        .strip()
    )


if topic and wiki_title:

    identidade = validar_identidade(
        topic,
        wiki_title,
        source_text
    )

    if not identidade[
        "valid"
    ]:

        critical.append(
            "source_identity_mismatch"
        )

        score -= 50

    else:

        strengths.append(
            "source_identity_pass"
        )

else:

    warnings.append(
        "source_identity_not_measurable"
    )

    score -= 5


# =====================================================
# 2. ROTEIRO
# =====================================================

wc = contar_palavras(
    script
)


if not 105 <= wc <= 125:

    critical.append(
        f"script_words_{wc}"
    )

    score -= 25

else:

    strengths.append(
        "script_length"
    )


hook = primeira_frase(
    script
)

hook_wc = contar_palavras(
    hook
)


if 6 <= hook_wc <= 16:

    strengths.append(
        "hook_length"
    )

else:

    warnings.append(
        f"hook_words_{hook_wc}"
    )

    score -= 5


frases = [
    x.strip()
    for x in re.split(
        r"[.!?]+",
        script
    )
    if x.strip()
]


longas = [
    x
    for x in frases
    if contar_palavras(
        x
    ) > 24
]


if len(longas) > 2:

    warnings.append(
        f"long_sentences_{len(longas)}"
    )

    score -= 5


# =====================================================
# 3. SCENE MAP
# =====================================================

scenes = scene_map.get(
    "scenes",
    []
)


if len(scenes) != 12:

    critical.append(
        f"scene_count_{len(scenes)}"
    )

    score -= 35

else:

    strengths.append(
        "scene_count_12"
    )


empty_query = 0
empty_must = 0
repeticoes = 0


for i, scene in enumerate(
    scenes
):

    query = str(
        scene.get(
            "query",
            ""
        )
    ).strip()

    must = scene.get(
        "must_have",
        []
    )


    if not query:

        empty_query += 1


    if not isinstance(
        must,
        list
    ) or not must:

        empty_must += 1


    if i > 0:

        anterior = str(
            scenes[
                i - 1
            ].get(
                "query",
                ""
            )
        )

        sim = similaridade(
            anterior,
            query
        )

        if sim >= 0.55:

            repeticoes += 1


if empty_query:

    critical.append(
        f"empty_queries_{empty_query}"
    )

    score -= (
        empty_query * 5
    )


if empty_must:

    warnings.append(
        f"empty_must_{empty_must}"
    )

    score -= min(
        empty_must * 2,
        10
    )


if repeticoes:

    warnings.append(
        f"visual_repetition_{repeticoes}"
    )

    score -= min(
        repeticoes * 3,
        12
    )

else:

    strengths.append(
        "visual_variety"
    )


# =====================================================
# 4. VISUAL MODES
# =====================================================

modes = [
    str(
        x.get(
            "visual_mode",
            ""
        )
    )
    for x in scenes
]


unique_modes = len(
    {
        x
        for x in modes
        if x
    }
)


if unique_modes >= 4:

    strengths.append(
        "visual_mode_variety"
    )

else:

    warnings.append(
        f"visual_modes_only_{unique_modes}"
    )

    score -= 6


# =====================================================
# 5. MÍDIA FÍSICA
# =====================================================

media = media_files()


if media:

    if len(media) != 12:

        critical.append(
            f"physical_media_{len(media)}"
        )

        score -= 25

    else:

        strengths.append(
            "physical_media_12"
        )


    videos = sum(
        1
        for x in media
        if x.lower().endswith(
            ".mp4"
        )
    )

    fotos = (
        len(media)
        - videos
    )


    if videos >= 3:

        strengths.append(
            f"video_mix_{videos}"
        )

    else:

        warnings.append(
            f"low_video_mix_{videos}"
        )

        score -= 5

else:

    videos = 0
    fotos = 0


# =====================================================
# 6. MOTION
# =====================================================

motion_scenes = motion.get(
    "scenes",
    []
)


if motion_scenes:

    if len(
        motion_scenes
    ) == 12:

        strengths.append(
            "motion_plan"
        )

    else:

        warnings.append(
            f"motion_count_{len(motion_scenes)}"
        )

        score -= 6


    movimentos = [
        x.get(
            "motion_profile",
            ""
        )
        for x in motion_scenes
    ]


    movimento_unicos = len(
        set(
            movimentos
        )
    )


    if movimento_unicos >= 4:

        strengths.append(
            "motion_variety"
        )

    else:

        warnings.append(
            f"motion_variety_{movimento_unicos}"
        )

        score -= 4


# =====================================================
# 7. CTA
# =====================================================

final_text = " ".join(
    palavras(
        script
    )[-20:]
).lower()


cta_comment = any(
    x in final_text
    for x in {
        "comente",
        "opinião",
        "acha",
        "teoria",
        "aconteceu"
    }
)


if cta_comment:

    strengths.append(
        "comment_cta"
    )

else:

    warnings.append(
        "weak_comment_cta"
    )

    score -= 3


# =====================================================
# RESULTADO
# =====================================================

score = max(
    0,
    min(
        score,
        100
    )
)


if critical:

    status = "BLOCK"

elif score >= 85:

    status = "EXCELLENT"

elif score >= 75:

    status = "PASS"

else:

    status = "WARNING"


report = {

    "short_id":
        SHORT_ID,

    "version":
        "5.0",

    "topic":
        topic,

    "wiki_title":
        wiki_title,

    "score":
        score,

    "status":
        status,

    "critical":
        critical,

    "warnings":
        warnings,

    "strengths":
        strengths,

    "metrics": {

        "script_words":
            wc,

        "hook_words":
            hook_wc,

        "scenes":
            len(
                scenes
            ),

        "visual_modes":
            unique_modes,

        "visual_repetitions":
            repeticoes,

        "media_files":
            len(
                media
            ),

        "videos":
            videos,

        "photos":
            fotos,

        "motion_scenes":
            len(
                motion_scenes
            )
    }
}


with open(
    PATHS["report"],
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
print("PRODUCTION SUPERVISOR 5.0")
print("================================")
print()

print(
    f"Assunto: {topic}"
)

print(
    f"Score global: {score}/100"
)

print(
    f"Status: {status}"
)

print()


if strengths:

    print(
        "PONTOS FORTES:"
    )

    for x in strengths:

        print(
            f"  + {x}"
        )

    print()


if warnings:

    print(
        "AVISOS:"
    )

    for x in warnings:

        print(
            f"  - {x}"
        )

    print()


if critical:

    print(
        "BLOQUEIOS:"
    )

    for x in critical:

        print(
            f"  ! {x}"
        )

    print()


print(
    f"Relatório:\n"
    f"{PATHS['report']}"
)

print()


if status == "BLOCK":

    print(
        "PRODUCTION SUPERVISOR: BLOCK"
    )

    raise SystemExit(1)


print(
    "PRODUCTION SUPERVISOR: PASS"
)
print()

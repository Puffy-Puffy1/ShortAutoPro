#!/usr/bin/env python3

import os
import sys
import json
import re
from datetime import date


BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

MANIFEST = os.path.join(
    BASE,
    "manifests",
    f"{SHORT_ID}.json"
)

PUBLISH = os.path.join(
    BASE,
    "roteiros",
    f"publish_{SHORT_ID}.json"
)

ROTEIRO = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}.txt"
)

HOOK = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.txt"
)

SAIDA = os.path.join(
    BASE,
    "manifests",
    f"{SHORT_ID}_quality.json"
)


def ler_json(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        return d if isinstance(d, dict) else {}

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


def contar_palavras(texto):
    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            texto,
            flags=re.UNICODE
        )
    )


manifest = ler_json(MANIFEST)
publish = ler_json(PUBLISH)
roteiro = ler_txt(ROTEIRO)
hook = ler_txt(HOOK)


# =========================================
# 1. ROTEIRO - 25 PONTOS
# =========================================

script_score = 25.0

qtd_palavras = contar_palavras(
    roteiro
)

if not 105 <= qtd_palavras <= 125:
    script_score -= 12


frases = [
    x.strip()
    for x in re.split(
        r"[.!?]+",
        roteiro
    )
    if x.strip()
]

frases_longas = sum(
    1
    for f in frases
    if contar_palavras(f) > 24
)

script_score -= min(
    6,
    frases_longas * 2
)


abertura = " ".join(
    roteiro.split()[:15]
).lower()

fracas = [
    "hoje vamos",
    "neste vídeo",
    "nesse vídeo",
    "você sabia",
    "voce sabia",
    "vamos falar"
]

if any(
    abertura.startswith(x)
    for x in fracas
):
    script_score -= 6


script_score = max(
    0,
    script_score
)


# =========================================
# 2. HOOK - 25 PONTOS
# =========================================

hook_score = 0.0

if hook:

    palavras_hook = contar_palavras(
        hook
    )

    hook_score = 14.0

    if 7 <= palavras_hook <= 16:
        hook_score += 5

    elif palavras_hook > 22:
        hook_score -= 4

    gatilhos = [
        "nunca",
        "ninguém",
        "ninguem",
        "desapareceu",
        "morte",
        "corpo",
        "mistério",
        "misterio",
        "prova",
        "verdade",
        "como",
        "por que",
        "o que"
    ]

    lower = hook.lower()

    hits = sum(
        1
        for x in gatilhos
        if x in lower
    )

    hook_score += min(
        hits * 2,
        6
    )


hook_score = max(
    0,
    min(
        hook_score,
        25
    )
)


# =========================================
# 3. VISUAL + TÉCNICO - 30 PONTOS
# =========================================

quality = manifest.get(
    "quality",
    {}
)

video = manifest.get(
    "video",
    {}
)

scenes = manifest.get(
    "scenes",
    {}
)

visual_score = 0.0


if quality.get(
    "resolution_ok"
):
    visual_score += 7


if quality.get(
    "fps_ok"
):
    visual_score += 5


if quality.get(
    "audio_exists"
):
    visual_score += 5


scene_count = scenes.get(
    "count",
    0
)

physical_count = scenes.get(
    "physical_count",
    0
)

if scene_count == 12:
    visual_score += 6


if physical_count == 12:
    visual_score += 7


visual_score = min(
    visual_score,
    30
)


# =========================================
# 4. PUBLISH - 20 PONTOS
# =========================================

publish_score_raw = publish.get(
    "publish_score"
)

publish_score = 0.0


if isinstance(
    publish_score_raw,
    (int, float)
):

    publish_score = (
        max(
            0,
            min(
                float(publish_score_raw),
                100
            )
        )
        / 100
        * 20
    )

else:

    titulo = str(
        publish.get(
            "chosen_title",
            ""
        )
    ).strip()

    descricao = str(
        publish.get(
            "description",
            ""
        )
    ).strip()

    hashtags = publish.get(
        "hashtags",
        []
    )

    if titulo:
        publish_score += 8

    if 35 <= len(titulo) <= 70:
        publish_score += 4

    if descricao:
        publish_score += 4

    if (
        isinstance(hashtags, list)
        and len(hashtags) == 5
    ):
        publish_score += 4


publish_score = min(
    publish_score,
    20
)


# =========================================
# TOTAL
# =========================================

total = (
    script_score
    + hook_score
    + visual_score
    + publish_score
)

total = round(
    total,
    1
)


if total >= 85:
    nivel = "EXCELLENT"

elif total >= 75:
    nivel = "GOOD"

elif total >= 65:
    nivel = "ACCEPTABLE"

else:
    nivel = "WEAK"


resultado = {
    "short_id":
        SHORT_ID,

    "total_score":
        total,

    "level":
        nivel,

    "components": {
        "script":
            round(
                script_score,
                1
            ),

        "hook":
            round(
                hook_score,
                1
            ),

        "visual_technical":
            round(
                visual_score,
                1
            ),

        "publish":
            round(
                publish_score,
                1
            )
    },

    "details": {
        "script_words":
            qtd_palavras,

        "long_sentences":
            frases_longas,

        "scene_count":
            scene_count,

        "physical_scene_count":
            physical_count,

        "duration_seconds":
            video.get(
                "duration_seconds"
            )
    }
}


os.makedirs(
    os.path.dirname(SAIDA),
    exist_ok=True
)


with open(
    SAIDA,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        resultado,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("================================")
print("FINAL QUALITY SCORE - 2.3.8")
print("================================")
print()

print(
    f"Roteiro: "
    f"{script_score:.1f}/25"
)

print(
    f"Hook: "
    f"{hook_score:.1f}/25"
)

print(
    f"Visual/Técnico: "
    f"{visual_score:.1f}/30"
)

print(
    f"Publish: "
    f"{publish_score:.1f}/20"
)

print()
print(
    f"NOTA FINAL: {total:.1f}/100"
)

print(
    f"NÍVEL: {nivel}"
)

print()

print(
    f"Arquivo:\n{SAIDA}"
)

print()

print(
    "FINAL QUALITY SCORE: OK"
)

print()

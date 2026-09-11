#!/usr/bin/env python3

import os
import json
from datetime import date


# =====================================================
# SHORTAUTO PRO
# CINEMATIC MOTION DIRECTOR 3.8
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

OUTPUT = os.path.join(
    BASE,
    "roteiros",
    f"motion_plan_{SHORT_ID}.json"
)


# =====================================================
# CARREGAR MAPA
# =====================================================

if not os.path.exists(
    SCENE_MAP
):

    raise SystemExit(
        f"ERRO: scene_map ausente:\n"
        f"{SCENE_MAP}"
    )


try:

    with open(
        SCENE_MAP,
        "r",
        encoding="utf-8"
    ) as f:

        mapa = json.load(f)

except Exception as e:

    raise SystemExit(
        f"ERRO lendo scene_map: {e}"
    )


cenas = mapa.get(
    "scenes",
    []
)


if not isinstance(
    cenas,
    list
) or not cenas:

    raise SystemExit(
        "ERRO: scene_map sem cenas."
    )


# =====================================================
# LOCALIZAR MÍDIA
# =====================================================

def localizar_midia(
    numero
):

    prefixo = (
        f"scene_{numero:02d}"
    )


    if not os.path.isdir(
        MEDIA_DIR
    ):

        return None


    for nome in os.listdir(
        MEDIA_DIR
    ):

        if nome.startswith(
            prefixo
        ):

            return os.path.join(
                MEDIA_DIR,
                nome
            )


    return None


def tipo_midia(
    path
):

    if not path:

        return "unknown"


    ext = os.path.splitext(
        path
    )[1].lower()


    if ext == ".mp4":
        return "video"


    if ext in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }:

        return "photo"


    return "unknown"


# =====================================================
# PERFIS
# =====================================================

PERFIS = {

    "still":
        {
            "zoom_start": 1.00,
            "zoom_end": 1.015,
            "pan": "none",
            "intensity": 1
        },

    "document_push":
        {
            "zoom_start": 1.00,
            "zoom_end": 1.045,
            "pan": "center",
            "intensity": 2
        },

    "slow_push":
        {
            "zoom_start": 1.00,
            "zoom_end": 1.065,
            "pan": "center",
            "intensity": 3
        },

    "slow_pan_left":
        {
            "zoom_start": 1.03,
            "zoom_end": 1.07,
            "pan": "left",
            "intensity": 3
        },

    "slow_pan_right":
        {
            "zoom_start": 1.03,
            "zoom_end": 1.07,
            "pan": "right",
            "intensity": 3
        },

    "hook_push":
        {
            "zoom_start": 1.00,
            "zoom_end": 1.095,
            "pan": "center",
            "intensity": 4
        },

    "environment_drift":
        {
            "zoom_start": 1.02,
            "zoom_end": 1.08,
            "pan": "right",
            "intensity": 3
        }
}


# =====================================================
# ESCOLHER PERFIL
# =====================================================

def escolher_perfil(
    numero,
    visual_mode,
    media_type
):

    # Vídeos já possuem movimento próprio.
    if media_type == "video":

        return (
            "native_video",
            {
                "zoom_start": 1.00,
                "zoom_end": 1.00,
                "pan": "none",
                "intensity": 0
            }
        )


    # Primeira cena ganha mais energia.
    if numero == 1:

        return (
            "hook_push",
            PERFIS[
                "hook_push"
            ]
        )


    if visual_mode in {
        "document",
        "evidence",
        "map_context"
    }:

        return (
            "document_push",
            PERFIS[
                "document_push"
            ]
        )


    if visual_mode in {
        "location",
        "environment"
    }:

        # Alternância simples de direção
        # para não parecer repetitivo.
        if numero % 2 == 0:

            return (
                "slow_pan_left",
                PERFIS[
                    "slow_pan_left"
                ]
            )

        return (
            "slow_pan_right",
            PERFIS[
                "slow_pan_right"
            ]
        )


    if visual_mode in {
        "architecture",
        "transport",
        "object"
    }:

        return (
            "slow_push",
            PERFIS[
                "slow_push"
            ]
        )


    if visual_mode == "human_context":

        return (
            "still",
            PERFIS[
                "still"
            ]
        )


    return (
        "slow_push",
        PERFIS[
            "slow_push"
        ]
    )


# =====================================================
# GERAR PLANO
# =====================================================

plano = []


for cena in cenas:

    try:

        numero = int(
            cena.get(
                "scene",
                0
            )
        )

    except Exception:

        continue


    visual_mode = str(
        cena.get(
            "visual_mode",
            "environment"
        )
    ).strip().lower()


    shot_type = str(
        cena.get(
            "shot_type",
            "medium"
        )
    ).strip().lower()


    arquivo = localizar_midia(
        numero
    )

    media_type = tipo_midia(
        arquivo
    )


    perfil_nome, perfil = (
        escolher_perfil(
            numero,
            visual_mode,
            media_type
        )
    )


    item = {
        "scene":
            numero,

        "visual_mode":
            visual_mode,

        "shot_type":
            shot_type,

        "media_type":
            media_type,

        "media":
            arquivo,

        "motion_profile":
            perfil_nome,

        "zoom_start":
            perfil[
                "zoom_start"
            ],

        "zoom_end":
            perfil[
                "zoom_end"
            ],

        "pan":
            perfil[
                "pan"
            ],

        "intensity":
            perfil[
                "intensity"
            ]
    }


    plano.append(
        item
    )


# =====================================================
# QUALITY CHECK DO PLANO
# =====================================================

problemas = []


if len(
    plano
) != len(
    cenas
):

    problemas.append(
        "scene_count_mismatch"
    )


# Evitar 3 movimentos iguais seguidos.
for i in range(
    2,
    len(plano)
):

    if (
        plano[i][
            "motion_profile"
        ]
        ==
        plano[i - 1][
            "motion_profile"
        ]
        ==
        plano[i - 2][
            "motion_profile"
        ]
        and plano[i][
            "motion_profile"
        ]
        not in {
            "native_video",
            "document_push"
        }
    ):

        # Troca apenas a direção visual
        # quando isso for seguro.
        if plano[i][
            "motion_profile"
        ] == "slow_pan_left":

            plano[i][
                "motion_profile"
            ] = "slow_pan_right"

            plano[i][
                "pan"
            ] = "right"


        elif plano[i][
            "motion_profile"
        ] == "slow_pan_right":

            plano[i][
                "motion_profile"
            ] = "slow_pan_left"

            plano[i][
                "pan"
            ] = "left"


# =====================================================
# SALVAR
# =====================================================

resultado = {
    "short_id":
        SHORT_ID,

    "version":
        "3.8",

    "scene_count":
        len(
            plano
        ),

    "problems":
        problemas,

    "scenes":
        plano
}


with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        resultado,
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# TERMINAL
# =====================================================

print()
print("================================")
print("CINEMATIC MOTION DIRECTOR 3.8")
print("================================")
print()


for item in plano:

    print(
        f"{item['scene']:02d}. "
        f"{item['visual_mode']:<16} "
        f"{item['media_type']:<7} "
        f"-> {item['motion_profile']}"
    )

    print(
        f"    zoom "
        f"{item['zoom_start']:.3f}"
        f" -> "
        f"{item['zoom_end']:.3f}"
        f" | pan={item['pan']} "
        f"| intensity={item['intensity']}"
    )


print()

print(
    f"Cenas: "
    f"{len(plano)}/{len(cenas)}"
)


if problemas:

    print(
        "MOTION PLAN: WARNING"
    )

    for problema in problemas:

        print(
            f"  - {problema}"
        )

else:

    print(
        "MOTION PLAN: PASS"
    )


print()

print(
    f"Plano:\n{OUTPUT}"
)

print()

print(
    "CINEMATIC MOTION DIRECTOR: OK"
)

print()

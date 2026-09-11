#!/usr/bin/env python3

import os
import json
from datetime import date


# =====================================================
# SHORTAUTO PRO
# MONTAGE RHYTHM DIRECTOR 4.3
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

MOTION_PLAN = os.path.join(
    BASE,
    "roteiros",
    f"motion_plan_{SHORT_ID}.json"
)

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

OUTPUT = os.path.join(
    BASE,
    "roteiros",
    f"rhythm_plan_{SHORT_ID}.json"
)

BACKUP = os.path.join(
    BASE,
    "roteiros",
    f"motion_plan_pre_rhythm_{SHORT_ID}.json"
)


# =====================================================
# LOAD
# =====================================================

def carregar(path):

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return {}


motion = carregar(
    MOTION_PLAN
)

scene_map = carregar(
    SCENE_MAP
)


cenas_motion = motion.get(
    "scenes",
    []
)

cenas_map = scene_map.get(
    "scenes",
    []
)


if not cenas_motion:

    raise SystemExit(
        "ERRO: motion_plan sem cenas."
    )


if len(cenas_motion) != len(cenas_map):

    raise SystemExit(
        "ERRO: motion_plan e scene_map "
        "possuem quantidades diferentes."
    )


# Backup do plano original.
with open(
    BACKUP,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        motion,
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# ENERGY CURVE
# =====================================================
#
# Não altera duração.
#
# 1       hook
# 2-3     contexto
# 4-6     desenvolvimento
# 7-9     escalada
# 10      virada / evidência
# 11-12   payoff / fechamento
# =====================================================

def energia_base(numero, total):

    if numero == 1:
        return 5

    proporcao = (
        numero
        / max(
            total,
            1
        )
    )

    if proporcao <= 0.25:
        return 2

    if proporcao <= 0.50:
        return 3

    if proporcao <= 0.75:
        return 4

    if numero == total:
        return 2

    return 3


# =====================================================
# PROTEÇÃO DOCUMENTAL
# =====================================================

CALMOS = {
    "document",
    "evidence",
    "map_context"
}

DINAMICOS = {
    "location",
    "environment",
    "transport",
    "architecture"
}


def ajustar_zoom(
    cena,
    energia
):

    inicio = float(
        cena.get(
            "zoom_start",
            1.0
        )
    )

    fim = float(
        cena.get(
            "zoom_end",
            1.06
        )
    )

    modo = str(
        cena.get(
            "visual_mode",
            ""
        )
    )

    media = str(
        cena.get(
            "media_type",
            ""
        )
    )


    # Vídeo tem movimento nativo.
    if media == "video":

        return (
            1.0,
            1.0
        )


    # Documento/evidência:
    # movimento elegante e discreto.
    if modo in CALMOS:

        amplitude = {
            1: 0.015,
            2: 0.025,
            3: 0.035,
            4: 0.045,
            5: 0.055
        }.get(
            energia,
            0.035
        )


    elif modo in DINAMICOS:

        amplitude = {
            1: 0.025,
            2: 0.040,
            3: 0.055,
            4: 0.070,
            5: 0.090
        }.get(
            energia,
            0.055
        )


    else:

        amplitude = {
            1: 0.020,
            2: 0.035,
            3: 0.050,
            4: 0.065,
            5: 0.080
        }.get(
            energia,
            0.050
        )


    inicio = max(
        1.0,
        min(
            inicio,
            1.05
        )
    )


    fim = max(
        inicio,
        min(
            inicio + amplitude,
            1.11
        )
    )


    return (
        inicio,
        fim
    )


# =====================================================
# PROCESSAR
# =====================================================

total = len(
    cenas_motion
)

resultado = []

perfil_anterior = None
pan_anterior = None


for idx, cena in enumerate(
    cenas_motion,
    start=1
):

    nova = dict(
        cena
    )

    modo = str(
        nova.get(
            "visual_mode",
            ""
        )
    )

    media = str(
        nova.get(
            "media_type",
            ""
        )
    )

    perfil = str(
        nova.get(
            "motion_profile",
            ""
        )
    )

    pan = str(
        nova.get(
            "pan",
            "center"
        )
    )


    energia = energia_base(
        idx,
        total
    )


    # Hook recebe energia máxima.
    if idx == 1:
        energia = 5


    # Evidência real/documento não deve
    # parecer efeito de TikTok.
    if modo in CALMOS:
        energia = min(
            energia,
            3
        )


    # Vídeo não recebe zoom artificial.
    if media == "video":
        energia_visual = 0

    else:
        energia_visual = energia


    # ---------------------------------
    # EVITAR PAN REPETIDO
    # ---------------------------------

    if (
        media == "photo"
        and pan in {
            "left",
            "right"
        }
        and pan == pan_anterior
    ):

        pan = (
            "right"
            if pan == "left"
            else "left"
        )


    # ---------------------------------
    # EVITAR PERFIL REPETIDO
    # ---------------------------------

    if (
        media == "photo"
        and perfil == perfil_anterior
        and modo not in CALMOS
    ):

        if pan == "center":

            pan = (
                "left"
                if idx % 2 == 0
                else "right"
            )


    zoom_start, zoom_end = (
        ajustar_zoom(
            nova,
            energia
        )
    )


    nova[
        "energy"
    ] = energia

    nova[
        "visual_energy"
    ] = energia_visual

    nova[
        "zoom_start"
    ] = round(
        zoom_start,
        4
    )

    nova[
        "zoom_end"
    ] = round(
        zoom_end,
        4
    )

    nova[
        "pan"
    ] = pan


    # Perfil passa a registrar que houve
    # direção de ritmo.
    if media == "photo":

        nova[
            "rhythm_profile"
        ] = (
            "hook"
            if idx == 1
            else
            "calm_documentary"
            if modo in CALMOS
            else
            "dynamic"
            if energia >= 4
            else
            "balanced"
        )

    else:

        nova[
            "rhythm_profile"
        ] = "native_video"


    resultado.append(
        nova
    )


    perfil_anterior = perfil
    pan_anterior = pan


# =====================================================
# AUDITORIA
# =====================================================

problemas = []


for i in range(
    2,
    len(resultado)
):

    pans = [
        resultado[i - 2].get(
            "pan"
        ),
        resultado[i - 1].get(
            "pan"
        ),
        resultado[i].get(
            "pan"
        )
    ]

    if (
        pans[0]
        == pans[1]
        == pans[2]
        and pans[0]
        in {
            "left",
            "right"
        }
    ):

        problemas.append(
            f"pan_triplo_cena_{i + 1}"
        )


# =====================================================
# SALVAR
# =====================================================

motion[
    "version"
] = "4.3"

motion[
    "rhythm_director"
] = {
    "applied":
        True,

    "problems":
        problemas
}

motion[
    "scenes"
] = resultado


with open(
    MOTION_PLAN,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        motion,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "short_id":
                SHORT_ID,

            "version":
                "4.3",

            "problems":
                problemas,

            "scenes":
                resultado
        },
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# TERMINAL
# =====================================================

print()
print("================================")
print("MONTAGE RHYTHM DIRECTOR 4.3")
print("================================")
print()


for cena in resultado:

    print(
        f"{cena['scene']:02d}. "
        f"energy={cena['energy']} "
        f"{cena['rhythm_profile']:<18} "
        f"{cena['media_type']}"
    )

    print(
        f"    motion="
        f"{cena['motion_profile']} "
        f"| zoom="
        f"{cena['zoom_start']:.3f}"
        f"->{cena['zoom_end']:.3f} "
        f"| pan={cena['pan']}"
    )


print()

if problemas:

    print(
        "RHYTHM QUALITY: WARNING"
    )

    for x in problemas:
        print(
            f"  - {x}"
        )

else:

    print(
        "RHYTHM QUALITY: PASS"
    )


print()

print(
    f"Plano:\n{OUTPUT}"
)

print()

print(
    "MONTAGE RHYTHM DIRECTOR: OK"
)

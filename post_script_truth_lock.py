#!/usr/bin/env python3

import os
import re
import json
from datetime import date

from source_identity import (
    validar_identidade,
    detectar_alias,
    normalizar,
    extrair_ids_numericos
)


# =====================================================
# SHORTAUTO PRO
# POST-SCRIPT TRUTH LOCK 6.2
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

R = os.path.join(
    BASE,
    "roteiros"
)


TOPIC_REAL = os.path.join(
    R,
    f"used_topic_{SHORT_ID}.txt"
)

TOPIC = os.path.join(
    R,
    f"topic_{SHORT_ID}.txt"
)

SOURCE = os.path.join(
    R,
    f"fonte_{SHORT_ID}.txt"
)

SCRIPT = os.path.join(
    R,
    f"short_{SHORT_ID}.txt"
)

SCENE_MAP = os.path.join(
    R,
    f"scene_map_{SHORT_ID}.json"
)

REPORT = os.path.join(
    R,
    f"post_script_truth_{SHORT_ID}.json"
)


# =====================================================
# IO
# =====================================================

def read(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


def read_json(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


# =====================================================
# SOURCE TITLE
# =====================================================

def extrair_titulo_fonte(
    texto
):

    for linha in str(
        texto
    ).splitlines():

        linha_limpa = linha.strip()

        m = re.match(
            r"(?i)^FONTE\s*:\s*(.+)$",
            linha_limpa
        )

        if not m:
            continue

        valor = m.group(
            1
        ).strip()

        valor = re.sub(
            r"(?i)^Wikipedia\s*[—–\-:]\s*",
            "",
            valor
        ).strip()

        return valor

    return ""


# =====================================================
# FLIGHT IDENTITY
# =====================================================

def flight_ids(
    texto
):

    n = normalizar(
        texto
    )

    ids = set()

    # Flight 19
    # Voo 19
    # Voo TAM 3054
    # Flight MH370 fica protegido também
    # pelo alias conhecido.
    patterns = [
        r"\bvoo\s+(?:[a-z]{2,15}\s+)?(\d{1,5})\b",
        r"\bflight\s+(?:[a-z]{2,15}\s+)?(\d{1,5})\b"
    ]

    for pattern in patterns:

        for x in re.findall(
            pattern,
            n
        ):

            ids.add(
                x
            )

    return ids


# =====================================================
# ALIAS MENTIONS
# =====================================================

def alias_canonico(
    texto
):

    return detectar_alias(
        texto
    )


# =====================================================
# SCENE TEXT
# =====================================================

def texto_cenas(
    mapa
):

    partes = []

    for cena in mapa.get(
        "scenes",
        []
    ):

        partes.append(
            str(
                cena.get(
                    "segment",
                    ""
                )
            )
        )

        partes.append(
            str(
                cena.get(
                    "query",
                    ""
                )
            )
        )

        partes.extend(
            str(x)
            for x in cena.get(
                "must_have",
                []
            )
        )

    return "\n".join(
        partes
    )


# =====================================================
# EXECUÇÃO
# =====================================================

topic = (
    read(
        TOPIC_REAL
    )
    or read(
        TOPIC
    )
)

source = read(
    SOURCE
)

script = read(
    SCRIPT
)

scene_map = read_json(
    SCENE_MAP
)

source_title = extrair_titulo_fonte(
    source
)

critical = []
warnings = []
strengths = []


print()
print("======================================")
print(" POST-SCRIPT TRUTH LOCK 6.2")
print("======================================")
print()

print(
    "SHORT_ID:",
    SHORT_ID
)

print(
    "TOPIC:",
    topic or "AUSENTE"
)

print(
    "SOURCE:",
    source_title or "AUSENTE"
)

print()


# =====================================================
# ARQUIVOS OBRIGATÓRIOS
# =====================================================

if not topic:

    critical.append(
        "topic_missing"
    )


if not source:

    critical.append(
        "source_missing"
    )


if not source_title:

    critical.append(
        "source_title_missing"
    )


if not script:

    critical.append(
        "script_missing"
    )


if not scene_map.get(
    "scenes"
):

    critical.append(
        "scene_map_missing"
    )


# =====================================================
# TOPIC -> SOURCE
# =====================================================

source_identity = None


if (
    topic
    and source_title
):

    source_identity = (
        validar_identidade(
            topic,
            source_title,
            source
        )
    )


    print(
        "SOURCE IDENTITY:",
        "PASS"
        if source_identity.get(
            "valid"
        )
        else "BLOCK"
    )

    print(
        "SOURCE REASON:",
        source_identity.get(
            "reason"
        )
    )


    if not source_identity.get(
        "valid"
    ):

        critical.append(
            "topic_source_identity_mismatch:"
            + str(
                source_identity.get(
                    "reason"
                )
            )
        )

    else:

        strengths.append(
            "topic_source_identity_pass"
        )


# =====================================================
# NUMERIC IDENTITY
# =====================================================

topic_ids = extrair_ids_numericos(
    topic
)

source_ids = extrair_ids_numericos(
    source_title
)

script_ids = extrair_ids_numericos(
    script
)

scene_text = texto_cenas(
    scene_map
)

scene_ids = extrair_ids_numericos(
    scene_text
)


# Identidade de voo é tratada separadamente,
# porque anos e quantidades não podem ser
# confundidos com número de voo.

topic_flights = flight_ids(
    topic
)

source_flights = flight_ids(
    source_title
)

script_flights = flight_ids(
    script
)

scene_flights = flight_ids(
    scene_text
)


print()
print(
    "FLIGHT IDS TOPIC:",
    sorted(
        topic_flights
    )
)

print(
    "FLIGHT IDS SOURCE:",
    sorted(
        source_flights
    )
)

print(
    "FLIGHT IDS SCRIPT:",
    sorted(
        script_flights
    )
)

print(
    "FLIGHT IDS SCENES:",
    sorted(
        scene_flights
    )
)


# =====================================================
# FLIGHT CONFLICT
# =====================================================

if (
    topic_flights
    and source_flights
    and not (
        topic_flights
        & source_flights
    )
):

    critical.append(
        "flight_identity_conflict:"
        f"topic={sorted(topic_flights)},"
        f"source={sorted(source_flights)}"
    )


if (
    topic_flights
    and script_flights
    and not (
        topic_flights
        & script_flights
    )
):

    critical.append(
        "script_flight_identity_conflict:"
        f"topic={sorted(topic_flights)},"
        f"script={sorted(script_flights)}"
    )


if (
    topic_flights
    and scene_flights
    and not (
        topic_flights
        & scene_flights
    )
):

    critical.append(
        "scene_flight_identity_conflict:"
        f"topic={sorted(topic_flights)},"
        f"scenes={sorted(scene_flights)}"
    )


# Se o tema explicitamente contém número
# de voo mas roteiro/cenas não repetem esse
# identificador, avisamos sem bloquear.
#
# Isso evita falso positivo em roteiros
# que usam "o avião", "a aeronave" etc.

if (
    topic_flights
    and not script_flights
):

    warnings.append(
        "topic_flight_id_not_explicit_in_script"
    )


if (
    topic_flights
    and not scene_flights
):

    warnings.append(
        "topic_flight_id_not_explicit_in_scenes"
    )


# =====================================================
# KNOWN ALIAS CONSISTENCY
# =====================================================

topic_alias = alias_canonico(
    topic
)

source_alias = alias_canonico(
    source_title + " " + source[:3000]
)

script_alias = alias_canonico(
    script
)

scene_alias = alias_canonico(
    scene_text
)


print()
print(
    "TOPIC ALIAS:",
    topic_alias
)

print(
    "SOURCE ALIAS:",
    source_alias
)

print(
    "SCRIPT ALIAS:",
    script_alias
)

print(
    "SCENE ALIAS:",
    scene_alias
)


if topic_alias:

    if (
        source_alias
        and source_alias
        != topic_alias
    ):

        critical.append(
            "source_known_alias_conflict:"
            f"{topic_alias}!={source_alias}"
        )


    if (
        script_alias
        and script_alias
        != topic_alias
    ):

        critical.append(
            "script_known_alias_conflict:"
            f"{topic_alias}!={script_alias}"
        )


    if (
        scene_alias
        and scene_alias
        != topic_alias
    ):

        critical.append(
            "scene_known_alias_conflict:"
            f"{topic_alias}!={scene_alias}"
        )


    if script_alias == topic_alias:

        strengths.append(
            "script_known_alias_pass"
        )


    if scene_alias == topic_alias:

        strengths.append(
            "scene_known_alias_pass"
        )


# =====================================================
# SOURCE NUMERIC DIAGNOSTIC
# =====================================================

# Não usamos números arbitrários de roteiro
# como veto porque datas, idade, quantidade,
# altitude etc. são comuns.
#
# O Source Identity 6.2 continua responsável
# pelo conflito numérico forte do título.

print()
print(
    "NUMERIC TOPIC:",
    sorted(
        topic_ids
    )
)

print(
    "NUMERIC SOURCE TITLE:",
    sorted(
        source_ids
    )
)


# =====================================================
# SCENE COUNT
# =====================================================

scene_count = len(
    scene_map.get(
        "scenes",
        []
    )
)

if scene_count == 12:

    strengths.append(
        "scene_count_12"
    )

else:

    warnings.append(
        f"scene_count={scene_count}"
    )


# =====================================================
# RESULT
# =====================================================

if critical:

    status = "BLOCK"

elif warnings:

    status = "WARNING"

else:

    status = "PASS"


report = {
    "short_id":
        SHORT_ID,

    "topic":
        topic,

    "source_title":
        source_title,

    "status":
        status,

    "critical":
        critical,

    "warnings":
        warnings,

    "strengths":
        strengths,

    "source_identity":
        source_identity,

    "topic_ids":
        sorted(
            topic_ids
        ),

    "source_ids":
        sorted(
            source_ids
        ),

    "flight_ids": {
        "topic":
            sorted(
                topic_flights
            ),

        "source":
            sorted(
                source_flights
            ),

        "script":
            sorted(
                script_flights
            ),

        "scenes":
            sorted(
                scene_flights
            )
    },

    "aliases": {
        "topic":
            topic_alias,

        "source":
            source_alias,

        "script":
            script_alias,

        "scenes":
            scene_alias
    },

    "scene_count":
        scene_count
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
print(
    "CRITICAL:",
    len(
        critical
    )
)

print(
    "WARNINGS:",
    len(
        warnings
    )
)

print(
    "STATUS:",
    status
)

print()
print(
    "REPORT:",
    REPORT
)


if critical:

    print()

    for item in critical:

        print(
            "ERRO:",
            item
        )

    print()
    print(
        "POST-SCRIPT TRUTH LOCK: BLOCK"
    )

    raise SystemExit(
        1
    )


if warnings:

    for item in warnings:

        print(
            "AVISO:",
            item
        )


print()
print(
    "POST-SCRIPT TRUTH LOCK:",
    status
)

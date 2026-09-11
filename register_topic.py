#!/usr/bin/env python3

import os
import json
from datetime import datetime


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    ""
)

USED_TOPIC = os.path.join(
    BASE,
    "roteiros",
    f"used_topic_{SHORT_ID}.txt"
)

TOPIC_FALLBACK = os.path.join(
    BASE,
    "roteiros",
    f"topic_{SHORT_ID}.txt"
)

HISTORICO = os.path.join(
    BASE,
    "historico_assuntos.json"
)


arquivo_topic = None


if os.path.exists(
    USED_TOPIC
):

    arquivo_topic = USED_TOPIC

elif os.path.exists(
    TOPIC_FALLBACK
):

    arquivo_topic = TOPIC_FALLBACK


if not arquivo_topic:

    raise SystemExit(0)


with open(
    arquivo_topic,
    "r",
    encoding="utf-8"
) as f:

    topic = f.read().strip()


if not topic:

    raise SystemExit(0)


dados = []


if os.path.exists(
    HISTORICO
):

    try:

        with open(
            HISTORICO,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

        if not isinstance(
            dados,
            list
        ):

            dados = []

    except Exception:

        dados = []


topic_norm = topic.lower().strip()


for item in dados:

    existente = str(
        item.get(
            "topic",
            ""
        )
    ).lower().strip()

    if existente == topic_norm:

        print(
            f"Assunto já estava registrado: {topic}"
        )

        raise SystemExit(0)


dados.append(
    {
        "short_id": SHORT_ID,
        "topic": topic,
        "created_at":
            datetime.now().isoformat()
    }
)


with open(
    HISTORICO,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        dados,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    f"Assunto registrado: {topic}"
)

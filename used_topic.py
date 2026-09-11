#!/usr/bin/env python3

import os
import re
from datetime import date


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

FONTE = os.path.join(
    BASE,
    "roteiros",
    f"fonte_{SHORT_ID}.txt"
)

USED_TOPIC = os.path.join(
    BASE,
    "roteiros",
    f"used_topic_{SHORT_ID}.txt"
)


if not os.path.exists(FONTE):

    raise SystemExit(
        "ERRO: fonte factual não encontrada."
    )


with open(
    FONTE,
    "r",
    encoding="utf-8"
) as f:

    texto = f.read()


match = re.search(
    r"^ASSUNTO:\s*(.+)$",
    texto,
    flags=re.MULTILINE
)


if not match:

    raise SystemExit(
        "ERRO: ASSUNTO não encontrado na fonte."
    )


assunto = match.group(1).strip()


if not assunto:

    raise SystemExit(
        "ERRO: assunto vazio."
    )


with open(
    USED_TOPIC,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        assunto
    )


print(
    f"Assunto realmente usado: {assunto}"
)

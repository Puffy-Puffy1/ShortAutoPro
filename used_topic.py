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

ROTEIROS = os.path.join(
    BASE,
    "roteiros"
)

FONTE = os.path.join(
    ROTEIROS,
    f"fonte_{SHORT_ID}.txt"
)

USED_TOPIC = os.path.join(
    ROTEIROS,
    f"used_topic_{SHORT_ID}.txt"
)


if not os.path.isfile(FONTE):
    raise SystemExit(
        "ERRO: fonte factual não encontrada."
    )


try:
    with open(
        FONTE,
        "r",
        encoding="utf-8"
    ) as f:
        texto = f.read()
except Exception as exc:
    raise SystemExit(
        f"ERRO lendo fonte factual: {exc}"
    )


match = re.search(
    r"^\s*ASSUNTO\s*:\s*(.+?)\s*$",
    texto,
    flags=re.MULTILINE | re.IGNORECASE
)

if not match:
    raise SystemExit(
        "ERRO: ASSUNTO não encontrado na fonte."
    )


assunto = " ".join(
    match.group(1).split()
).strip()

if not assunto:
    raise SystemExit(
        "ERRO: assunto vazio."
    )

# O assunto deve ser um identificador curto, nunca um bloco de texto.
if "\n" in assunto or "\r" in assunto or len(assunto) > 300:
    raise SystemExit(
        "ERRO: ASSUNTO inválido na fonte."
    )


os.makedirs(
    ROTEIROS,
    exist_ok=True
)

temporario = USED_TOPIC + ".tmp"

try:
    with open(
        temporario,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(assunto)
        f.flush()
        os.fsync(f.fileno())

    os.replace(
        temporario,
        USED_TOPIC
    )
finally:
    if os.path.exists(temporario):
        try:
            os.remove(temporario)
        except OSError:
            pass


print(
    f"Assunto realmente usado: {assunto}"
)

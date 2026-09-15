#!/usr/bin/env python3

import os
import sys
import re
import json
import time
import requests
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

ROTEIRO = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}.txt"
)

KEYWORDS = os.path.join(
    BASE,
    "roteiros",
    f"keywords_{SHORT_ID}.txt"
)

MAPA = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

GEMINI_KEY = os.getenv(
    "GEMINI_API_KEY"
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

try:
    QTD_CENAS = int(
        os.getenv(
            "SHORT_QTD_CENAS",
            "12"
        )
    )
except ValueError:
    QTD_CENAS = 12

QTD_CENAS = max(
    6,
    min(QTD_CENAS, 20)
)

if not GEMINI_KEY:

    sys.exit(
        "ERRO: GEMINI_API_KEY não configurada."
    )

if not os.path.exists(ROTEIRO):

    sys.exit(
        f"ERRO: roteiro não encontrado:\n"
        f"{ROTEIRO}"
    )


with open(
    ROTEIRO,
    "r",
    encoding="utf-8"
) as f:

    roteiro = f.read().strip()


if not roteiro:

    sys.exit(
        "ERRO: roteiro vazio."
    )


def extrair_palavras(texto):

    return re.findall(
        r"\b[\wÀ-ÿ'-]+\b",
        texto,
        flags=re.UNICODE
    )


total_palavras = len(
    extrair_palavras(
        roteiro
    )
)


URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)

HEADERS = {
    "Content-Type": "application/json",
    "x-goog-api-key": GEMINI_KEY
}


def chamar_gemini(prompt):

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.20,
            "maxOutputTokens": 1800
        }
    }


    for tentativa in range(
        1,
        5
    ):

        print(
            f"Scene Director tentativa "
            f"{tentativa}/4..."
        )

        try:

            r = requests.post(
                URL,
                headers=HEADERS,
                json=payload,
                timeout=120
            )

        except Exception as e:

            if tentativa == 4:

                raise RuntimeError(
                    str(e)
                )

            time.sleep(5)
            continue


        if r.ok:

            dados = r.json()

            try:

                return (
                    dados["candidates"][0]
                    ["content"]["parts"][0]["text"]
                    .strip()
                )

            except Exception:

                raise RuntimeError(
                    "Gemini retornou resposta inválida."
                )


        if (
            r.status_code
            in [429, 500, 502, 503, 504]
            and tentativa < 4
        ):

            time.sleep(8)
            continue


        raise RuntimeError(
            f"HTTP {r.status_code}: {r.text}"
        )


    raise RuntimeError(
        "Gemini não respondeu."
    )


prompt = f"""
Você é um diretor profissional de edição.

Abaixo está o roteiro FINAL de um YouTube Short:

========================

{roteiro}

========================

Divida o roteiro em EXATAMENTE
{QTD_CENAS} segmentos semânticos consecutivos.

Cada segmento:

- precisa seguir a ordem original do roteiro;
- representa uma ideia visual;
- não pode inventar fatos;
- não pode alterar a narrativa;
- deve conter aproximadamente
  6 a 14 palavras quando possível;
- pode ser um pouco maior ou menor
  para preservar o sentido.

Para cada segmento crie uma busca visual
EM INGLÊS.

A busca:

- 4 a 9 palavras;
- descreve algo visível;
- pessoa, objeto, ação ou lugar;
- funciona em Pexels, Pixabay e Coverr;
- estilo B-roll cinematográfico;
- não usa conceitos abstratos;
- não representa CTA com celular;
- não usa likes ou comentários;
- não introduz teoria antes da narração;
- última cena fecha visualmente a história.

RESPONDA SOMENTE EM JSON VÁLIDO.

Formato:

{{
  "scenes": [
    {{
      "segment": "trecho do roteiro em português",
      "query": "visual search in english"
    }}
  ]
}}

O array deve ter EXATAMENTE
{QTD_CENAS} elementos.

Não use markdown.
Não explique nada.
"""


print()
print("================================")
print("SCENE DIRECTOR V6.3")
print("================================")
print()

print(
    f"ID: {SHORT_ID}"
)

print(
    f"Palavras: {total_palavras}"
)

print(
    f"Cenas: {QTD_CENAS}"
)

print()


try:

    bruto = chamar_gemini(
        prompt
    )

except Exception as e:

    sys.exit(
        f"ERRO Scene Director: {e}"
    )


bruto = (
    bruto
    .replace("```json", "")
    .replace("```", "")
    .strip()
)


try:

    dados = json.loads(
        bruto
    )

except Exception:

    print()
    print(
        "Resposta recebida:"
    )

    print(
        bruto
    )

    sys.exit(
        "ERRO: JSON inválido."
    )


scenes = dados.get(
    "scenes",
    []
)


if len(scenes) != QTD_CENAS:

    sys.exit(
        f"ERRO: Scene Director retornou "
        f"{len(scenes)} cenas; "
        f"esperado {QTD_CENAS}."
    )


resultado = []
soma_pesos = 0


for numero, item in enumerate(
    scenes,
    start=1
):

    trecho = str(
        item.get(
            "segment",
            ""
        )
    ).strip()

    busca = str(
        item.get(
            "query",
            ""
        )
    ).strip()

    busca = (
        busca
        .lstrip("[")
        .rstrip("]")
        .strip()
    )


    if not trecho:

        sys.exit(
            f"ERRO: cena {numero} "
            "sem segmento."
        )


    if not busca:

        sys.exit(
            f"ERRO: cena {numero} "
            "sem busca."
        )


    qtd = len(
        extrair_palavras(
            trecho
        )
    )

    qtd = max(
        1,
        qtd
    )

    soma_pesos += qtd


    resultado.append(
        {
            "scene": numero,
            "segment": trecho,
            "query": busca,
            "words": qtd
        }
    )


for item in resultado:

    item["weight"] = (
        item["words"]
        / soma_pesos
    )


saida = {
    "short_id": SHORT_ID,
    "total_script_words":
        total_palavras,
    "mapped_words":
        soma_pesos,
    "scene_count":
        QTD_CENAS,
    "scenes":
        resultado
}


with open(
    MAPA,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        saida,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    KEYWORDS,
    "w",
    encoding="utf-8"
) as f:

    for item in resultado:

        f.write(
            item["query"]
            + "\n"
        )


print()
print("================================")
print("MAPA SEMÂNTICO CRIADO!")
print("================================")
print()


for item in resultado:

    print(
        f"CENA {item['scene']:02d}"
    )

    print(
        f"TRECHO: {item['segment']}"
    )

    print(
        f"BUSCA: {item['query']}"
    )

    print(
        f"PALAVRAS: {item['words']}"
    )

    print()


print(
    f"Palavras mapeadas: "
    f"{soma_pesos}"
)

print(
    f"Palavras roteiro: "
    f"{total_palavras}"
)

print()

print(
    f"Mapa:\n{MAPA}"
)

print()

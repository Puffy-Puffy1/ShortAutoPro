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
        f"ERRO: roteiro não encontrado:\n{ROTEIRO}"
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
    extrair_palavras(roteiro)
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
            "temperature": 0.15,
            "maxOutputTokens": 2400
        }
    }

    for tentativa in range(1, 5):

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
Você é um diretor profissional de edição visual.

Abaixo está o roteiro FINAL de um YouTube Short:

========================

{roteiro}

========================

Divida o roteiro em EXATAMENTE
{QTD_CENAS} segmentos semânticos consecutivos.

Cada segmento precisa seguir a ordem original
e representar uma ideia visual específica.

Para CADA cena gere:

1. segment
Trecho correspondente do roteiro em português.

2. query
Busca visual em inglês para Pexels/Pixabay/Coverr.

3. must_have
Lista de 1 a 3 termos em inglês que DEVEM aparecer
semanticamente na mídia ideal.

4. avoid
Lista de 0 a 5 termos em inglês que indicam
uma mídia inadequada para aquela cena.

REGRAS:

- não invente fatos;
- não altere a narrativa;
- cada segment deve ter aproximadamente
  6 a 14 palavras quando possível;
- query deve ter 4 a 9 palavras;
- query deve descrever algo concretamente visível;
- must_have deve conter objetos, locais ou ações
  essenciais da cena;
- evite termos abstratos em must_have;
- avoid deve bloquear visuais comuns mas errados;
- não use celular, like, subscribe ou comentário
  para representar CTA;
- não introduza teorias antes da narração;
- a última cena deve fechar visualmente a história.

EXEMPLO:

Trecho:
"O corpo foi encontrado dentro de um tanque de água
no topo do hotel."

query:
rooftop hotel water tank cinematic

must_have:
["water tank", "rooftop"]

avoid:
["street", "computer", "woman walking"]

RESPONDA SOMENTE EM JSON VÁLIDO.

Formato EXATO:

{{
  "scenes": [
    {{
      "segment": "trecho em português",
      "query": "visual search in english",
      "must_have": ["term"],
      "avoid": ["term"]
    }}
  ]
}}

O array deve conter EXATAMENTE {QTD_CENAS} itens.

Não use markdown.
Não escreva explicações.
"""


print()
print("================================")
print("SCENE DIRECTOR V6.5")
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
    print(bruto)

    sys.exit(
        "ERRO: JSON inválido."
    )


scenes = dados.get(
    "scenes",
    []
)


# =====================================================
# SCENE DIRECTOR 6.6
# GUARANTEED 12-SCENE BUILDER
# =====================================================

scene_count_original = len(
    scenes
)

recovery_actions = []


def _scene_words_6_6(
    item
):

    return extrair_palavras(
        str(
            item.get(
                "segment",
                ""
            )
        )
    )


def _clean_list_6_6(
    value,
    limit
):

    if not isinstance(
        value,
        list
    ):

        return []

    saida = []

    for x in value:

        x = str(
            x
        ).strip()

        if (
            x
            and x.lower()
            not in [
                y.lower()
                for y in saida
            ]
        ):

            saida.append(
                x
            )

    return saida[:limit]


def _split_scene_6_6(
    item
):

    palavras = _scene_words_6_6(
        item
    )


    if len(palavras) < 4:

        return None


    meio = max(
        2,
        len(palavras) // 2
    )


    esquerda = " ".join(
        palavras[:meio]
    ).strip()


    direita = " ".join(
        palavras[meio:]
    ).strip()


    if (
        not esquerda
        or not direita
    ):

        return None


    base_query = str(
        item.get(
            "query",
            ""
        )
    ).strip()


    must = _clean_list_6_6(
        item.get(
            "must_have",
            []
        ),
        3
    )


    avoid = _clean_list_6_6(
        item.get(
            "avoid",
            []
        ),
        5
    )


    comum = {
        k: v
        for k, v in item.items()
        if k not in {
            "segment",
            "scene",
            "words",
            "weight"
        }
    }


    a = dict(
        comum
    )

    b = dict(
        comum
    )


    a[
        "segment"
    ] = esquerda

    b[
        "segment"
    ] = direita


    a[
        "query"
    ] = (
        base_query
        or "documentary detail scene"
    )

    b[
        "query"
    ] = (
        base_query
        or "documentary detail scene"
    )


    a[
        "must_have"
    ] = list(
        must
    )

    b[
        "must_have"
    ] = list(
        must
    )


    a[
        "avoid"
    ] = list(
        avoid
    )

    b[
        "avoid"
    ] = list(
        avoid
    )


    a[
        "recovery_6_6"
    ] = "split_left"

    b[
        "recovery_6_6"
    ] = "split_right"


    return (
        a,
        b
    )


def _merge_pair_6_6(
    a,
    b
):

    segmento = (
        str(
            a.get(
                "segment",
                ""
            )
        ).strip()
        + " "
        + str(
            b.get(
                "segment",
                ""
            )
        ).strip()
    ).strip()


    query_a = str(
        a.get(
            "query",
            ""
        )
    ).strip()

    query_b = str(
        b.get(
            "query",
            ""
        )
    ).strip()


    query = (
        query_a
        or query_b
        or "documentary scene"
    )


    must = _clean_list_6_6(
        (
            list(
                a.get(
                    "must_have",
                    []
                )
                if isinstance(
                    a.get(
                        "must_have",
                        []
                    ),
                    list
                )
                else []
            )
            +
            list(
                b.get(
                    "must_have",
                    []
                )
                if isinstance(
                    b.get(
                        "must_have",
                        []
                    ),
                    list
                )
                else []
            )
        ),
        3
    )


    avoid = _clean_list_6_6(
        (
            list(
                a.get(
                    "avoid",
                    []
                )
                if isinstance(
                    a.get(
                        "avoid",
                        []
                    ),
                    list
                )
                else []
            )
            +
            list(
                b.get(
                    "avoid",
                    []
                )
                if isinstance(
                    b.get(
                        "avoid",
                        []
                    ),
                    list
                )
                else []
            )
        ),
        5
    )


    merged = dict(
        a
    )


    merged[
        "segment"
    ] = segmento

    merged[
        "query"
    ] = query

    merged[
        "must_have"
    ] = must

    merged[
        "avoid"
    ] = avoid

    merged[
        "recovery_6_6"
    ] = "merged_adjacent"


    return merged


# -----------------------------------------------------
# Nenhuma cena utilizável continua sendo erro crítico.
# -----------------------------------------------------

if not scenes:

    sys.exit(
        "ERRO: Gemini não retornou "
        "nenhuma cena utilizável."
    )


# -----------------------------------------------------
# MENOS DE 12
#
# Divide os maiores segmentos.
# Nenhuma palavra nova é criada.
# -----------------------------------------------------

while len(
    scenes
) < QTD_CENAS:

    candidatos_split = sorted(
        range(
            len(
                scenes
            )
        ),
        key=lambda i:
            len(
                _scene_words_6_6(
                    scenes[i]
                )
            ),
        reverse=True
    )


    recuperou = False


    for indice in candidatos_split:

        dividido = _split_scene_6_6(
            scenes[
                indice
            ]
        )


        if not dividido:

            continue


        esquerda, direita = dividido


        scenes[
            indice:
            indice + 1
        ] = [
            esquerda,
            direita
        ]


        recovery_actions.append(
            {
                "action":
                    "split",

                "index":
                    indice + 1
            }
        )


        recuperou = True

        break


    if not recuperou:

        sys.exit(
            "ERRO: não foi possível completar "
            f"{QTD_CENAS} cenas sem inventar texto."
        )


# -----------------------------------------------------
# MAIS DE 12
#
# Consolida o par vizinho com menor quantidade
# combinada de palavras.
# -----------------------------------------------------

while len(
    scenes
) > QTD_CENAS:

    melhor_indice = None
    melhor_tamanho = None


    for i in range(
        len(
            scenes
        ) - 1
    ):

        tamanho = (
            len(
                _scene_words_6_6(
                    scenes[i]
                )
            )
            +
            len(
                _scene_words_6_6(
                    scenes[
                        i + 1
                    ]
                )
            )
        )


        if (
            melhor_tamanho is None
            or tamanho < melhor_tamanho
        ):

            melhor_tamanho = tamanho
            melhor_indice = i


    if melhor_indice is None:

        sys.exit(
            "ERRO: não foi possível consolidar "
            "cenas excedentes."
        )


    merged = _merge_pair_6_6(
        scenes[
            melhor_indice
        ],
        scenes[
            melhor_indice + 1
        ]
    )


    scenes[
        melhor_indice:
        melhor_indice + 2
    ] = [
        merged
    ]


    recovery_actions.append(
        {
            "action":
                "merge",

            "index":
                melhor_indice + 1
        }
    )


print()
print(
    "SCENE COUNT ORIGINAL:",
    scene_count_original
)

print(
    "RECOVERY ACTIONS:",
    len(
        recovery_actions
    )
)

print(
    "SCENE COUNT FINAL:",
    f"{len(scenes)}/{QTD_CENAS}"
)


if recovery_actions:

    splits = sum(
        1
        for x in recovery_actions
        if x.get(
            "action"
        ) == "split"
    )

    merges = sum(
        1
        for x in recovery_actions
        if x.get(
            "action"
        ) == "merge"
    )


    print(
        "RECOVERY SPLITS:",
        splits
    )

    print(
        "RECOVERY MERGES:",
        merges
    )


if len(
    scenes
) != QTD_CENAS:

    sys.exit(
        "ERRO: Guaranteed Builder "
        f"terminou com {len(scenes)} cenas."
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

    must_have = item.get(
        "must_have",
        []
    )

    avoid = item.get(
        "avoid",
        []
    )

    if not isinstance(
        must_have,
        list
    ):
        must_have = []

    if not isinstance(
        avoid,
        list
    ):
        avoid = []

    must_have = [
        str(x).strip().lower()
        for x in must_have
        if str(x).strip()
    ][:3]

    avoid = [
        str(x).strip().lower()
        for x in avoid
        if str(x).strip()
    ][:5]

    busca = (
        busca
        .lstrip("[")
        .rstrip("]")
        .strip()
    )

    if not trecho:
        sys.exit(
            f"ERRO: cena {numero} sem segmento."
        )

    if not busca:
        sys.exit(
            f"ERRO: cena {numero} sem busca."
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
            "must_have": must_have,
            "avoid": avoid,
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

    "scene_count_original":
        scene_count_original,

    "scene_recovery_6_6":
        recovery_actions,

    "scene_director_version":
        "6.6",
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
print("VISUAL RELEVANCE MAP CRIADO!")
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
        f"MUST: "
        f"{', '.join(item['must_have'])}"
    )

    print(
        f"AVOID: "
        f"{', '.join(item['avoid'])}"
    )

    print()


print(
    f"Mapa:\n{MAPA}"
)

print()

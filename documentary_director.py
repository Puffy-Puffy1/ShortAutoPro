#!/usr/bin/env python3

import os
import sys
import json
import time
import shutil
import requests
from datetime import date


# =====================================================
# SHORTAUTO PRO
# DOCUMENTARY DIRECTOR - STABLE 3.1
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)


SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

FONTE = os.path.join(
    BASE,
    "roteiros",
    f"fonte_{SHORT_ID}.txt"
)

TOPIC_REAL = os.path.join(
    BASE,
    "roteiros",
    f"used_topic_{SHORT_ID}.txt"
)

TOPIC_FALLBACK = os.path.join(
    BASE,
    "roteiros",
    f"topic_{SHORT_ID}.txt"
)

BACKUP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_pre_documentary_{SHORT_ID}.json"
)

REPORT = os.path.join(
    BASE,
    "roteiros",
    f"documentary_director_{SHORT_ID}.json"
)


# =====================================================
# PRÉ-CHECK
# =====================================================

if not API_KEY:

    sys.exit(
        "ERRO: GEMINI_API_KEY não configurada."
    )


if not os.path.exists(
    SCENE_MAP
):

    sys.exit(
        f"ERRO: scene_map ausente:\n"
        f"{SCENE_MAP}"
    )


# =====================================================
# LEITURA
# =====================================================

def ler_txt(
    caminho
):

    if not os.path.exists(
        caminho
    ):
        return ""

    try:

        with open(
            caminho,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


try:

    with open(
        SCENE_MAP,
        "r",
        encoding="utf-8"
    ) as f:

        mapa = json.load(f)

except Exception as e:

    sys.exit(
        f"ERRO lendo scene_map: {e}"
    )


cenas = mapa.get(
    "scenes",
    []
)


if not isinstance(
    cenas,
    list
) or len(cenas) != 12:

    sys.exit(
        "ERRO: Documentary Director "
        "esperava exatamente 12 cenas."
    )


assunto = (
    ler_txt(
        TOPIC_REAL
    )
    or ler_txt(
        TOPIC_FALLBACK
    )
)

fonte = ler_txt(
    FONTE
)


# Backup antes de qualquer alteração.

shutil.copy2(
    SCENE_MAP,
    BACKUP
)


# =====================================================
# FUNÇÕES
# =====================================================

def limpar(
    texto
):

    return " ".join(
        str(texto)
        .replace("\n", " ")
        .split()
    )


def limpar_lista(
    valor,
    minimo=0,
    maximo=10
):

    if not isinstance(
        valor,
        list
    ):
        return []


    saida = []


    for item in valor:

        item = limpar(
            item
        ).lower()

        if (
            item
            and item not in saida
        ):

            saida.append(
                item
            )


    return saida[
        :maximo
    ]


MODOS_VALIDOS = {
    "location",
    "object",
    "evidence",
    "document",
    "human_context",
    "environment",
    "transport",
    "architecture",
    "map_context",
    "abstract_context"
}


SHOTS_VALIDOS = {
    "wide",
    "medium",
    "close_up",
    "aerial",
    "detail",
    "interior",
    "exterior",
    "overhead",
    "silhouette"
}


# =====================================================
# ENTRADA COMPACTA
# =====================================================

entrada = []


for cena in cenas:

    entrada.append(
        {
            "scene":
                cena.get(
                    "scene"
                ),

            "segment":
                limpar(
                    cena.get(
                        "segment",
                        ""
                    )
                ),

            "query":
                limpar(
                    cena.get(
                        "query",
                        ""
                    )
                ),

            "must_have":
                limpar_lista(
                    cena.get(
                        "must_have",
                        []
                    )
                ),

            "avoid":
                limpar_lista(
                    cena.get(
                        "avoid",
                        []
                    )
                )
        }
    )


# =====================================================
# PROMPT
# =====================================================

prompt = f"""
Você é o diretor visual de um documentário factual
vertical para YouTube Shorts.

ASSUNTO:

{assunto}

FONTE FACTUAL DISPONÍVEL:

========================
{fonte[:14000]}
========================

Você receberá 12 cenas já associadas ao roteiro.

Seu trabalho é criar uma DIREÇÃO DOCUMENTAL mais
profissional para essas 12 cenas.

Você NÃO pode mudar o texto narrado.

Você NÃO pode inventar fatos.

Você NÃO deve representar alegações controversas
como se fossem fatos confirmados.

==================================================
OBJETIVO VISUAL
==================================================

O Short não deve parecer apenas uma sequência
de stock footage genérico.

Use uma gramática documental variada.

Os modos disponíveis são:

location
= local ou ambiente onde o fato ocorreu.

object
= objeto relevante para o fato.

evidence
= representação neutra de evidência física.

document
= relatório, arquivo, jornal, registro ou documento.

human_context
= pessoas genéricas somente quando necessárias.

environment
= ambiente natural/contextual.

transport
= avião, carro, navio, trem etc.

architecture
= prédio, hotel, corredor, estrutura física.

map_context
= mapa, rota, localização ou deslocamento.

abstract_context
= somente para ideias difíceis de representar
literalmente.

==================================================
REGRAS DE QUALIDADE
==================================================

1. Cada cena precisa representar a frase narrada.

2. O OBJETO PRINCIPAL da frase tem prioridade.

Exemplo:

"O avião levava uma equipe de rugby."

Prioridade:
airplane > passengers > rugby.

Não transforme isso simplesmente em atletas correndo.

3. Em fatos históricos, use aparência compatível
com a época quando isso for relevante.

4. Evite pessoas aleatórias quando um objeto,
local, documento ou ambiente pode explicar melhor
a frase.

5. Sempre que houver informação investigativa,
use documentos/evidências quando fizer sentido.

6. Sempre que houver local importante,
considere location ou architecture.

7. Não mostrar morte explícita, cadáver gráfico,
sangue ou ferimentos gráficos.

8. Alegações de UFO, paranormal, conspiração ou
causas controversas devem ser visualmente ambíguas:

mysterious light
unidentified distant object
shadow
night sky
document
radio
testimony context

Nunca:
detailed alien spacecraft
visible ghost
alien creature

9. Não invente retratos de pessoas reais.

10. Se banco de mídia provavelmente não possuir a
pessoa real, use contexto documental.

11. Alterne os tipos visuais.

Não faça:

environment
environment
environment
environment

quando existirem alternativas factualmente corretas.

12. Não use o mesmo visual_mode mais de 2 vezes
consecutivas.

13. Não use o mesmo shot_type mais de 2 vezes
consecutivas.

14. query deve estar em INGLÊS.

15. query deve ter aproximadamente 5 a 13 palavras.

16. must_have:
1 a 3 conceitos essenciais.

17. avoid:
2 a 5 conceitos que produziriam imagem errada.

18. Relevância factual é mais importante que
movimento.

19. Não force vídeos. Fotos documentais boas são
preferíveis a vídeos semanticamente errados.

==================================================
CENAS
==================================================

{json.dumps(
    entrada,
    ensure_ascii=False,
    indent=2
)}

RESPONDA SOMENTE JSON:

{{
  "scenes": [
    {{
      "scene": 1,
      "visual_mode": "location",
      "shot_type": "wide",
      "query": "english search query",
      "must_have": [
        "important object"
      ],
      "avoid": [
        "wrong thing",
        "wrong environment"
      ],
      "reason": "explicação curta"
    }}
  ]
}}

EXATAMENTE 12 cenas.
Sem markdown.
Sem texto fora do JSON.
"""


# =====================================================
# GEMINI
# =====================================================

URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)

HEADERS = {
    "Content-Type":
        "application/json",

    "x-goog-api-key":
        API_KEY
}


payload = {
    "contents": [
        {
            "parts": [
                {
                    "text":
                        prompt
                }
            ]
        }
    ],

    "generationConfig": {
        "temperature":
            0.20,

        "maxOutputTokens":
            5000
    }
}


bruto = None


print()
print("================================")
print("DOCUMENTARY DIRECTOR - STABLE 3.1")
print("================================")
print()


for tentativa in range(
    1,
    4
):

    print(
        f"Documentary Director tentativa "
        f"{tentativa}/3..."
    )


    try:

        r = requests.post(
            URL,
            headers=HEADERS,
            json=payload,
            timeout=120
        )

    except Exception as e:

        if tentativa == 3:

            sys.exit(
                f"ERRO Documentary Director: {e}"
            )

        time.sleep(
            4
        )

        continue


    if r.ok:

        try:

            bruto = (
                r.json()
                ["candidates"][0]
                ["content"]
                ["parts"][0]
                ["text"]
                .strip()
            )

            break

        except Exception:

            bruto = None


    if (
        r.status_code
        in [
            429,
            500,
            502,
            503,
            504
        ]
        and tentativa < 3
    ):

        time.sleep(
            6
        )

        continue


    sys.exit(
        f"ERRO Documentary Director "
        f"HTTP {r.status_code}"
    )


if not bruto:

    sys.exit(
        "ERRO: Documentary Director "
        "sem resposta."
    )


bruto = (
    bruto
    .replace(
        "```json",
        ""
    )
    .replace(
        "```",
        ""
    )
    .strip()
)


try:

    resposta = json.loads(
        bruto
    )

except Exception:

    sys.exit(
        "ERRO: Documentary Director "
        "retornou JSON inválido."
    )


novas = resposta.get(
    "scenes",
    []
)


if not isinstance(
    novas,
    list
) or len(novas) != 12:

    sys.exit(
        f"ERRO: Documentary Director "
        f"retornou {len(novas)} cenas."
    )


# =====================================================
# VALIDAR NUMERAÇÃO
# =====================================================

por_numero = {}


for item in novas:

    if not isinstance(
        item,
        dict
    ):
        continue


    try:

        numero = int(
            item.get(
                "scene"
            )
        )

    except Exception:

        continue


    por_numero[
        numero
    ] = item


esperado = set(
    range(
        1,
        13
    )
)


if set(
    por_numero.keys()
) != esperado:

    sys.exit(
        "ERRO: Documentary Director "
        "alterou a numeração das cenas."
    )


# =====================================================
# CONSTRUIR MAPA
# =====================================================

resultado = []

relatorio = []


for cena_original in cenas:

    numero = int(
        cena_original[
            "scene"
        ]
    )

    novo = por_numero[
        numero
    ]


    mode = limpar(
        novo.get(
            "visual_mode",
            ""
        )
    ).lower()


    if mode not in MODOS_VALIDOS:

        mode = "environment"


    shot = limpar(
        novo.get(
            "shot_type",
            ""
        )
    ).lower()


    if shot not in SHOTS_VALIDOS:

        shot = "medium"


    query = limpar(
        novo.get(
            "query",
            ""
        )
    )


    query_palavras = len(
        query.split()
    )


    if not (
        4
        <= query_palavras
        <= 16
    ):

        query = limpar(
            cena_original.get(
                "query",
                ""
            )
        )


    must = limpar_lista(
        novo.get(
            "must_have",
            []
        ),
        maximo=3
    )


    if not must:

        must = limpar_lista(
            cena_original.get(
                "must_have",
                []
            ),
            maximo=3
        )


    avoid = limpar_lista(
        novo.get(
            "avoid",
            []
        ),
        maximo=5
    )


    if len(
        avoid
    ) < 2:

        avoid = limpar_lista(
            cena_original.get(
                "avoid",
                []
            ),
            maximo=5
        )


    cena_final = dict(
        cena_original
    )


    cena_final[
        "query"
    ] = query

    cena_final[
        "must_have"
    ] = must

    cena_final[
        "avoid"
    ] = avoid

    cena_final[
        "visual_mode"
    ] = mode

    cena_final[
        "shot_type"
    ] = shot


    resultado.append(
        cena_final
    )


    relatorio.append(
        {
            "scene":
                numero,

            "segment":
                limpar(
                    cena_original.get(
                        "segment",
                        ""
                    )
                ),

            "visual_mode":
                mode,

            "shot_type":
                shot,

            "query_before":
                limpar(
                    cena_original.get(
                        "query",
                        ""
                    )
                ),

            "query_after":
                query,

            "must_have":
                must,

            "avoid":
                avoid,

            "reason":
                limpar(
                    novo.get(
                        "reason",
                        ""
                    )
                )
        }
    )


# =====================================================
# DIVERSIDADE
# =====================================================

repeticoes_mode = 0
repeticoes_shot = 0


for i in range(
    2,
    len(resultado)
):

    a = resultado[
        i
    ]

    b = resultado[
        i - 1
    ]

    c = resultado[
        i - 2
    ]


    if (
        a.get(
            "visual_mode"
        )
        == b.get(
            "visual_mode"
        )
        == c.get(
            "visual_mode"
        )
    ):

        repeticoes_mode += 1


    if (
        a.get(
            "shot_type"
        )
        == b.get(
            "shot_type"
        )
        == c.get(
            "shot_type"
        )
    ):

        repeticoes_shot += 1


# =====================================================
# SALVAR
# =====================================================

mapa_final = dict(
    mapa
)

mapa_final[
    "scenes"
] = resultado


mapa_final[
    "documentary_director"
] = {
    "version":
        "3.1",

    "applied":
        True,

    "visual_mode_triple_repetitions":
        repeticoes_mode,

    "shot_triple_repetitions":
        repeticoes_shot
}


with open(
    SCENE_MAP,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa_final,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "short_id":
                SHORT_ID,

            "topic":
                assunto,

            "backup":
                BACKUP,

            "visual_mode_triple_repetitions":
                repeticoes_mode,

            "shot_triple_repetitions":
                repeticoes_shot,

            "scenes":
                relatorio
        },
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# TERMINAL
# =====================================================

print()
print("DIREÇÃO DOCUMENTAL:")
print()


for item in relatorio:

    print(
        f"{item['scene']:02d}. "
        f"[{item['visual_mode']}] "
        f"[{item['shot_type']}]"
    )

    print(
        f"    {item['query_after']}"
    )

    print(
        "    MUST: "
        + ", ".join(
            item[
                "must_have"
            ]
        )
    )

    print(
        "    AVOID: "
        + ", ".join(
            item[
                "avoid"
            ]
        )
    )

    print()


print(
    "Repetições de 3 visual_modes: "
    f"{repeticoes_mode}"
)

print(
    "Repetições de 3 enquadramentos: "
    f"{repeticoes_shot}"
)

print()

print(
    f"Relatório:\n"
    f"{REPORT}"
)

print()

print(
    "DOCUMENTARY DIRECTOR: OK"
)

print()

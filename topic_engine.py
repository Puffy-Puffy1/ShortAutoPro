#!/usr/bin/env python3

import os
import sys
import json
import re
import time
import math
import requests
from datetime import date

from topic_memory import encontrar_duplicata
from topic_reserve import melhor_reserva
from wiki_client import search as wiki_search_client
from wiki_client import extract as wiki_extract_client
from source_identity import validar_identidade
from wiki_client import WikiRateLimit


BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

TEMA = os.getenv(
    "SHORT_TEMA",
    "mistérios, casos inexplicáveis e true crime"
)

API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

HISTORICO = os.path.join(
    BASE,
    "historico_assuntos.json"
)

SAIDA = os.path.join(
    BASE,
    "roteiros",
    f"topic_{SHORT_ID}.txt"
)

VERIFICACAO = os.path.join(
    BASE,
    "roteiros",
    f"topic_verified_{SHORT_ID}.json"
)

os.makedirs(
    os.path.dirname(SAIDA),
    exist_ok=True
)

if not API_KEY:
    sys.exit(
        "ERRO: GEMINI_API_KEY não configurada."
    )


# =====================================================
# UTILIDADES
# =====================================================

def normalizar(texto):

    texto = str(texto).lower()

    texto = re.sub(
        r"[^\wÀ-ÿ]+",
        " ",
        texto
    )

    return " ".join(
        texto.split()
    )


def carregar_historico():

    if not os.path.exists(
        HISTORICO
    ):
        return []

    try:

        with open(
            HISTORICO,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

        if isinstance(
            dados,
            list
        ):
            return dados

    except Exception:
        pass

    return []


historico = carregar_historico()


# =====================================================
# WIKIPEDIA
# =====================================================

HEADERS_WIKI = {
    "User-Agent":
        "ShortAutoPro-Stable-1.5/1.0"
}


def wiki_search(query):

    return wiki_search_client(
        query,
        limit=5
    )


def wiki_extract(title):

    return wiki_extract_client(
        title
    )


def variacoes_busca(nome):

    candidatos = [
        nome,

        re.sub(
            r"^(O|A|Os|As)\s+",
            "",
            nome,
            flags=re.IGNORECASE
        ),

        re.sub(
            r"^(O|A)\s+Caso\s+",
            "",
            nome,
            flags=re.IGNORECASE
        ),

        re.sub(
            r"^Caso\s+",
            "",
            nome,
            flags=re.IGNORECASE
        )
    ]

    saida = []

    for item in candidatos:

        item = item.strip()

        if not item:
            continue

        if item.lower() in [
            x.lower()
            for x in saida
        ]:
            continue

        saida.append(
            item
        )

    return saida


def verificar_wikipedia(nome):

    for consulta in variacoes_busca(
        nome
    ):

        resultados = wiki_search(
            consulta
        )

        if not resultados:
            continue

        for resultado in resultados:

            titulo = str(
                resultado.get(
                    "title",
                    ""
                )
            ).strip()

            if not titulo:
                continue

            texto = wiki_extract(
                titulo
            )

            if len(texto) < 700:
                continue

            stop_titulo = {
                "o", "a", "os", "as",
                "de", "da", "do", "das", "dos",
                "e", "em", "no", "na",
                "caso", "incidente",
                "desaparecimento",
                "misterio", "mistério"
            }

            nome_tokens = {
                x
                for x in normalizar(nome).split()
                if x not in stop_titulo
            }

            titulo_tokens = {
                x
                for x in normalizar(titulo).split()
                if x not in stop_titulo
            }

            if not nome_tokens:
                continue

            comuns = (
                nome_tokens
                .intersection(
                    titulo_tokens
                )
            )

            inter = len(comuns)

            semelhanca = (
                inter
                / len(nome_tokens)
            )

            # Uma única palavra genérica não basta.
            #
            # Exemplos que DEVEM ser rejeitados:
            # Boy in the Box -> Boy in the Striped Pyjamas
            # Falcon Lake -> The Loud House
            #
            # Para nomes curtos de 1 termo significativo,
            # exige correspondência exata desse termo.
            if len(nome_tokens) == 1:

                if inter != 1:
                    continue

            else:

                if inter < 2:
                    continue

                if semelhanca < 0.45:
                    continue

            # =========================================
            # SOURCE IDENTITY GATE 4.1
            # =========================================

            identidade = validar_identidade(
                nome,
                titulo,
                texto
            )

            if not identidade[
                "valid"
            ]:

                continue


            return {
                "ok": True,
                "wiki_title": titulo,
                "chars": len(texto),
                "similarity": round(
                    semelhanca,
                    3
                ),
                "identity_score": round(
                    float(
                        identidade.get(
                            "score",
                            0.0
                        )
                    ),
                    3
                ),
                "identity_reason":
                    identidade.get(
                        "reason",
                        ""
                    )
            }

    return {
        "ok": False,
        "wiki_title": "",
        "chars": 0,
        "similarity": 0,
        "identity_score": 0.0,
        "identity_reason": "no_valid_source"
    }


# =====================================================
# SINAIS DO ASSUNTO
# =====================================================

PALAVRAS_VISUAIS = {
    "hotel",
    "elevator",
    "elevador",
    "aircraft",
    "avião",
    "aviao",
    "ship",
    "navio",
    "forest",
    "floresta",
    "mountain",
    "montanha",
    "island",
    "ilha",
    "ocean",
    "oceano",
    "snow",
    "neve",
    "police",
    "polícia",
    "policia",
    "house",
    "casa",
    "road",
    "estrada",
    "train",
    "trem",
    "car",
    "carro",
    "building",
    "prédio",
    "predio",
    "water",
    "água",
    "agua",
    "room",
    "quarto",
    "cave",
    "caverna",
    "desert",
    "deserto"
}


PALAVRAS_HOOK = {
    "desapareceu",
    "desaparecimento",
    "sumiu",
    "morreu",
    "morte",
    "encontrado",
    "encontrada",
    "mistério",
    "misterio",
    "sem",
    "nunca",
    "último",
    "ultimo",
    "corpo",
    "tripulação",
    "tripulacao",
    "avião",
    "aviao",
    "navio",
    "ilha",
    "hotel",
    "elevador",
    "neve"
}


def score_visual_nome(nome):

    toks = set(
        normalizar(nome).split()
    )

    hits = len(
        toks.intersection(
            PALAVRAS_VISUAIS
        )
    )

    return min(
        10.0,
        5.0 + hits * 1.5
    )


def score_hook_nome(nome):

    toks = set(
        normalizar(nome).split()
    )

    hits = len(
        toks.intersection(
            PALAVRAS_HOOK
        )
    )

    return min(
        10.0,
        5.0 + hits * 1.2
    )


def score_documentacao(chars):

    if chars >= 12000:
        return 10.0

    if chars >= 8000:
        return 9.5

    if chars >= 5000:
        return 9.0

    if chars >= 3000:
        return 8.0

    if chars >= 1800:
        return 7.0

    if chars >= 1000:
        return 6.0

    return 5.0


def score_titulo(similarity):

    return max(
        0.0,
        min(
            10.0,
            similarity * 10
        )
    )


def score_novidade(nome):

    if not historico:
        return 10.0

    dup = encontrar_duplicata(
        nome,
        historico,
        limite=1.1
    )

    sim = float(
        dup.get(
            "similarity",
            0
        )
    )

    return max(
        0.0,
        10.0 - sim * 10
    )


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
            "temperature": 0.65,
            "maxOutputTokens": 1800
        }
    }

    for tentativa in range(
        1,
        4
    ):

        print(
            f"Topic Engine tentativa "
            f"{tentativa}/3..."
        )

        try:

            r = requests.post(
                URL,
                headers=HEADERS,
                json=payload,
                timeout=100
            )

        except Exception as e:

            if tentativa == 3:
                raise RuntimeError(
                    str(e)
                )

            time.sleep(4)
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
            and tentativa < 3
        ):

            time.sleep(6)
            continue

        raise RuntimeError(
            f"HTTP {r.status_code}: {r.text}"
        )

    raise RuntimeError(
        "Gemini não respondeu."
    )


# =====================================================
# PROMPT
# =====================================================

usados = [
    str(
        item.get(
            "topic",
            ""
        )
    )
    for item in historico[-60:]
    if isinstance(
        item,
        dict
    )
]

usados_texto = (
    "\n".join(
        f"- {x}"
        for x in usados
    )
    if usados
    else "nenhum"
)


prompt = f"""
Você é pesquisador de temas para YouTube Shorts.

Tema do canal:

{TEMA}

Gere EXATAMENTE 10 candidatos de casos REAIS.

IMPORTANTE:

- apenas casos documentados;
- não combine casos diferentes;
- não invente nomes;
- não invente crimes;
- não invente desaparecimentos;
- prefira casos conhecidos;
- prefira casos com artigo provável na Wikipedia;
- evite assuntos já utilizados;
- varie países, épocas e tipos de mistério;
- priorize histórias com começo forte;
- priorize casos com bons elementos visuais.

ASSUNTOS JÁ UTILIZADOS:

{usados_texto}

Para cada candidato dê notas de 0 a 10:

curiosity
visual
documentation
retention
comment_potential

RESPONDA SOMENTE EM JSON:

{{
  "topics": [
    {{
      "topic": "nome exato",
      "curiosity": 0,
      "visual": 0,
      "documentation": 0,
      "retention": 0,
      "comment_potential": 0
    }}
  ]
}}

Exatamente 10 itens.
Sem markdown.
Sem explicações.
"""


# =====================================================
# EXECUÇÃO
# =====================================================

print()
print("================================")
print("VIRAL TOPIC ENGINE - STABLE 1.5")
print("================================")
print()

print(
    f"Assuntos no histórico: "
    f"{len(historico)}"
)

print()


try:

    bruto = chamar_gemini(
        prompt
    )

except Exception as e:

    sys.exit(
        f"ERRO Topic Engine: {e}"
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

    dados = json.loads(
        bruto
    )

except Exception:

    print(bruto)

    sys.exit(
        "ERRO: JSON inválido."
    )


topics = dados.get(
    "topics",
    []
)


if len(topics) < 8:

    sys.exit(
        "ERRO: poucos candidatos."
    )


# =====================================================
# PRÉ-RANKING + VERIFICAÇÃO REDUZIDA
# =====================================================

aprovados = []
relatorio = []

pre_candidatos = []

for item in topics:

    nome = str(
        item.get(
            "topic",
            ""
        )
    ).strip()

    if not nome:
        continue

    duplicata = encontrar_duplicata(
        nome,
        historico,
        limite=0.72
    )

    if duplicata["duplicate"]:

        relatorio.append(
            {
                "topic": nome,
                "approved": False,
                "reason": "duplicate",
                "similar_to":
                    duplicata["topic"],
                "similarity":
                    duplicata["similarity"]
            }
        )

        continue

    try:

        curiosity = float(
            item.get(
                "curiosity",
                0
            )
        )

        visual_gemini = float(
            item.get(
                "visual",
                0
            )
        )

        documentation_gemini = float(
            item.get(
                "documentation",
                0
            )
        )

        retention = float(
            item.get(
                "retention",
                0
            )
        )

        comment_potential = float(
            item.get(
                "comment_potential",
                0
            )
        )

    except Exception:
        continue


    # Pré-score sem Wikipedia.
    pre_score = (
        curiosity * 1.20
        + visual_gemini * 0.80
        + documentation_gemini * 1.10
        + retention * 1.30
        + comment_potential * 0.90
    )


    pre_candidatos.append(
        {
            "item": item,
            "nome": nome,
            "pre_score": pre_score
        }
    )


pre_candidatos.sort(
    key=lambda x: x["pre_score"],
    reverse=True
)


# Só verifica os 5 melhores.
pre_candidatos = pre_candidatos[:5]


print(
    "Verificando apenas os melhores "
    "candidatos na Wikipedia..."
)

print()


for numero, pre in enumerate(
    pre_candidatos,
    start=1
):

    item = pre["item"]
    nome = pre["nome"]

    nome = str(
        item.get(
            "topic",
            ""
        )
    ).strip()

    if not nome:
        continue


    try:

        verificacao = verificar_wikipedia(
            nome
        )

    except WikiRateLimit:

        sys.exit(
            "ERRO: Wikipedia temporariamente "
            "limitada. Tente novamente depois."
        )

    except Exception as e:

        print(
            f"AVISO Wikipedia: {e}"
        )

        continue


    if not verificacao[
        "ok"
    ]:

        print(
            f"{numero:02d}. REJEITADO "
            f"(sem fonte): {nome}"
        )

        relatorio.append(
            {
                "topic": nome,
                "approved": False,
                "reason":
                    "wikipedia_not_verified"
            }
        )

        continue


    try:

        curiosity = float(
            item.get(
                "curiosity",
                0
            )
        )

        visual_gemini = float(
            item.get(
                "visual",
                0
            )
        )

        documentation_gemini = float(
            item.get(
                "documentation",
                0
            )
        )

        retention = float(
            item.get(
                "retention",
                0
            )
        )

        comment_potential = float(
            item.get(
                "comment_potential",
                0
            )
        )

    except Exception:

        continue


    visual_obj = score_visual_nome(
        nome
    )

    hook_obj = score_hook_nome(
        nome
    )

    doc_obj = score_documentacao(
        verificacao[
            "chars"
        ]
    )

    titulo_obj = score_titulo(
        verificacao[
            "similarity"
        ]
    )

    novidade_obj = score_novidade(
        nome
    )


    # Gemini contribui,
    # mas sinais verificáveis têm peso grande.

    score = (
        curiosity * 1.10
        + retention * 1.20
        + comment_potential * 0.90
        + visual_gemini * 0.55
        + documentation_gemini * 0.45

        + visual_obj * 1.10
        + hook_obj * 1.15
        + doc_obj * 1.25
        + titulo_obj * 0.55
        + novidade_obj * 0.75
    )


    aprovado = {
        "topic": nome,

        "score":
            round(
                score,
                2
            ),

        "gemini": {
            "curiosity":
                curiosity,
            "visual":
                visual_gemini,
            "documentation":
                documentation_gemini,
            "retention":
                retention,
            "comment_potential":
                comment_potential
        },

        "objective": {
            "visual":
                visual_obj,
            "hook":
                hook_obj,
            "documentation":
                doc_obj,
            "title_match":
                titulo_obj,
            "novelty":
                novidade_obj
        },

        "wiki_title":
            verificacao[
                "wiki_title"
            ],

        "wiki_chars":
            verificacao[
                "chars"
            ],

        "wiki_similarity":
            verificacao[
                "similarity"
            ]
    }


    aprovados.append(
        aprovado
    )


    print(
        f"{numero:02d}. APROVADO: "
        f"{nome}"
    )

    print(
        f"    score viral: "
        f"{score:.1f}"
    )

    print(
        f"    wiki: "
        f"{verificacao['wiki_title']}"
    )

    print(
        f"    contexto: "
        f"{verificacao['chars']} chars"
    )


    relatorio.append(
        {
            "topic": nome,
            "approved": True,
            "score":
                round(
                    score,
                    2
                ),
            "wiki_title":
                verificacao[
                    "wiki_title"
                ]
        }
    )


    if len(aprovados) >= 3:

        print()
        print(
            "Já existem 3 temas verificados. "
            "Encerrando consultas à Wikipedia."
        )

        break


# =====================================================
# RESULTADO
# =====================================================

if not aprovados:

    print()
    print(
        "Nenhum tema novo foi aprovado."
    )

    print(
        "Consultando Verified Topic Reserve..."
    )

    reserva = melhor_reserva()


    if reserva:

        print()
        print(
            "TEMA DE RESERVA ENCONTRADO:"
        )

        print(
            reserva["topic"]
        )

        print(
            "Wikipedia:"
        )

        print(
            reserva["wiki_title"]
        )


        escolhido = {
            "topic":
                reserva["topic"],

            "score":
                reserva["score"],

            "wiki_title":
                reserva["wiki_title"],

            "wiki_chars":
                0,

            "wiki_similarity":
                1.0,

            "gemini": {},

            "objective": {
                "visual": 0,
                "hook": 0,
                "documentation": 0,
                "title_match": 10,
                "novelty": 10
            },

            "reserve":
                True
        }


        aprovados = [
            escolhido
        ]


    else:

        sys.exit(
            "ERRO: nenhum tema novo aprovado "
            "e nenhuma reserva verificada disponível."
        )


aprovados.sort(
    key=lambda x: x[
        "score"
    ],
    reverse=True
)


escolhido = aprovados[
    0
]


with open(
    SAIDA,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        escolhido[
            "topic"
        ]
    )


with open(
    VERIFICACAO,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "short_id":
                SHORT_ID,

            "selected":
                escolhido,

            "ranking":
                aprovados,

            "verification":
                relatorio
        },
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("================================")
print("RANKING VIRAL")
print("================================")
print()


for numero, item in enumerate(
    aprovados,
    start=1
):

    marca = (
        " <-- ESCOLHIDO"
        if numero == 1
        else ""
    )

    print(
        f"{numero}. "
        f"{item['topic']} "
        f"score={item['score']:.1f}"
        f"{marca}"
    )

    print(
        f"   visual="
        f"{item['objective']['visual']:.1f} "
        f"hook="
        f"{item['objective']['hook']:.1f} "
        f"doc="
        f"{item['objective']['documentation']:.1f} "
        f"novidade="
        f"{item['objective']['novelty']:.1f}"
    )


print()
print(
    "Assunto escolhido:"
)

print(
    escolhido[
        "topic"
    ]
)

print()
print(
    "VIRAL TOPIC ENGINE: OK"
)

print()

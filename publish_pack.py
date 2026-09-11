#!/usr/bin/env python3

import os
import sys
import json
import re
import time
import requests
from datetime import date


# =====================================================
# SHORTAUTO PRO
# PUBLISH QUALITY GUARD 2.3.7
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)


ROTEIRO = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}.txt"
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

HOOK = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.txt"
)

SAIDA_JSON = os.path.join(
    BASE,
    "roteiros",
    f"publish_{SHORT_ID}.json"
)

SAIDA_TXT = os.path.join(
    BASE,
    "roteiros",
    f"publish_{SHORT_ID}.txt"
)


if not API_KEY:

    sys.exit(
        "ERRO: GEMINI_API_KEY não configurada."
    )


if not os.path.exists(
    ROTEIRO
):

    sys.exit(
        "ERRO: roteiro não encontrado."
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


roteiro = ler_txt(
    ROTEIRO
)

fonte = ler_txt(
    FONTE
)

assunto = (
    ler_txt(
        TOPIC_REAL
    )
    or ler_txt(
        TOPIC_FALLBACK
    )
)

hook = ler_txt(
    HOOK
)


# =====================================================
# UTILIDADES
# =====================================================

def normalizar(
    texto
):

    return " ".join(
        re.findall(
            r"[a-záàâãéêíóôõúç0-9]+",
            str(texto).lower()
        )
    )


def contar_caracteres(
    texto
):

    return len(
        str(texto).strip()
    )


def palavras(
    texto
):

    return set(
        normalizar(
            texto
        ).split()
    )


# =====================================================
# PALAVRAS FRACAS / CLICKBAIT
# =====================================================

EXPRESSOES_FRACAS = [
    "você não vai acreditar",
    "voce nao vai acreditar",
    "chocante demais",
    "isso vai te chocar",
    "ninguém esperava isso",
    "ninguem esperava isso",
    "a verdade absoluta",
    "segredo finalmente revelado",
    "100% comprovado",
    "prova definitiva"
]


ERROS_CONHECIDOS = {
    "mentura",
    "investigacaoo",
    "desaparecimente",
    "misterío",
    "períciaa",
    "tragically"
}


# =====================================================
# SCORE DE TÍTULO
# =====================================================

def score_titulo(
    titulo,
    assunto,
    hook,
    roteiro
):

    titulo = str(
        titulo
    ).strip()

    if not titulo:

        return -999


    score = 50.0

    tamanho = len(
        titulo
    )


    # ---------------------------------
    # TAMANHO
    # ---------------------------------

    if 38 <= tamanho <= 62:

        score += 20

    elif 30 <= tamanho <= 70:

        score += 12

    elif tamanho > 90:

        score -= 25

    else:

        score -= 8


    lower = titulo.lower()


    # ---------------------------------
    # CLICKBAIT RUIM
    # ---------------------------------

    for termo in EXPRESSOES_FRACAS:

        if termo in lower:

            score -= 35


    # ---------------------------------
    # ERROS CONHECIDOS
    # ---------------------------------

    for erro in ERROS_CONHECIDOS:

        if erro in lower:

            score -= 60


    # ---------------------------------
    # CONEXÃO COM ASSUNTO
    # ---------------------------------

    titulo_tokens = palavras(
        titulo
    )

    assunto_tokens = palavras(
        assunto
    )

    hook_tokens = palavras(
        hook
    )

    roteiro_tokens = palavras(
        roteiro
    )


    if assunto_tokens:

        overlap = len(
            titulo_tokens.intersection(
                assunto_tokens
            )
        )

        if overlap >= 2:

            score += 12

        elif overlap == 1:

            score += 6


    if hook_tokens:

        overlap_hook = len(
            titulo_tokens.intersection(
                hook_tokens
            )
        )

        score += min(
            overlap_hook * 2,
            8
        )


    # Penaliza palavra importante
    # que não aparece em roteiro/assunto/hook.

    base_tokens = (
        assunto_tokens
        | hook_tokens
        | roteiro_tokens
    )

    estranhas = [
        x
        for x in titulo_tokens
        if (
            len(x) >= 7
            and x not in base_tokens
        )
    ]

    if len(estranhas) >= 3:

        score -= 8


    # ---------------------------------
    # FORMATAÇÃO
    # ---------------------------------

    if titulo.isupper():

        score -= 15


    if titulo.count("!") > 1:

        score -= 8


    if titulo.count("?") > 1:

        score -= 5


    return round(
        score,
        1
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


def chamar_gemini(
    prompt
):

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
            "temperature": 0.45,
            "maxOutputTokens": 1300
        }
    }


    for tentativa in range(
        1,
        4
    ):

        print(
            f"Publish Pack tentativa "
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

            time.sleep(
                4
            )

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
                    "Resposta Gemini inválida."
                )


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


        raise RuntimeError(
            f"HTTP {r.status_code}: "
            f"{r.text}"
        )


    raise RuntimeError(
        "Gemini não respondeu."
    )


# =====================================================
# PROMPT
# =====================================================

prompt = f"""
Você cria metadados profissionais para YouTube Shorts
em português do Brasil.

ASSUNTO REAL:

{assunto}

HOOK FINAL:

{hook}

ROTEIRO FINAL:

========================
{roteiro}
========================

FONTE FACTUAL:

========================
{fonte[:10000]}
========================

Use SOMENTE informações sustentadas pelo roteiro
e pela fonte factual.

Não invente fatos.

Não exagere uma conclusão.

Não transforme teoria em fato.

Não use informação que não esteja sustentada.

========================
TÍTULOS
========================

Crie EXATAMENTE 3 títulos.

Cada título:

- português natural do Brasil;
- ortografia correta;
- entre 35 e 70 caracteres;
- curiosidade forte;
- claro;
- factual;
- sem ALL CAPS;
- sem hashtag;
- no máximo 1 emoji;
- não use clickbait falso;
- não use palavras inventadas;
- não declare como comprovado algo que é apenas teoria.

========================
DESCRIÇÃO
========================

- entre 120 e 280 caracteres;
- factual;
- sem revelar tudo imediatamente;
- incentive comentário;
- português correto;
- não invente fatos.

========================
HASHTAGS
========================

Exatamente 5.

- incluir #Shorts;
- relacionadas ao assunto;
- sem hashtags genéricas irrelevantes;
- sem espaços dentro das hashtags.

========================
COMENTÁRIO FIXADO
========================

- uma pergunta curta;
- estimular opinião ou teoria;
- não pedir inscrição;
- não repetir a descrição inteira.

RESPONDA SOMENTE EM JSON VÁLIDO:

{{
  "titles": [
    "título 1",
    "título 2",
    "título 3"
  ],
  "description": "descrição",
  "hashtags": [
    "#Shorts",
    "#Exemplo",
    "#Exemplo2",
    "#Exemplo3",
    "#Exemplo4"
  ],
  "pinned_comment": "pergunta"
}}

Não informe chosen_title.
O sistema escolherá automaticamente o melhor título.
"""


# =====================================================
# EXECUÇÃO
# =====================================================

print()
print("================================")
print("PUBLISH QUALITY GUARD - 2.3.7")
print("================================")
print()

print(
    f"ID: {SHORT_ID}"
)

print(
    f"Assunto: {assunto}"
)

print()


try:

    bruto = chamar_gemini(
        prompt
    )

except Exception as e:

    sys.exit(
        f"ERRO Publish Pack: {e}"
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

    print(
        bruto
    )

    sys.exit(
        "ERRO: JSON inválido "
        "no Publish Pack."
    )


# =====================================================
# VALIDAR TÍTULOS
# =====================================================

titles = dados.get(
    "titles",
    []
)


if not isinstance(
    titles,
    list
):

    titles = []


titles = [
    str(x).strip()
    for x in titles
    if str(x).strip()
]


if len(titles) < 3:

    sys.exit(
        "ERRO: menos de 3 títulos válidos."
    )


titles = titles[:3]


ranking = []


for titulo in titles:

    score = score_titulo(
        titulo,
        assunto,
        hook,
        roteiro
    )

    ranking.append(
        {
            "title":
                titulo,

            "score":
                score
        }
    )


ranking.sort(
    key=lambda x: x[
        "score"
    ],
    reverse=True
)


chosen = ranking[
    0
]["title"]


# =====================================================
# DESCRIÇÃO
# =====================================================

description = str(
    dados.get(
        "description",
        ""
    )
).strip()


if not description:

    description = (
        f"Conheça os fatos por trás de {assunto}. "
        "Qual é a sua opinião sobre esse caso?"
    )


# Limite de segurança.
if len(description) > 350:

    description = (
        description[:347]
        .rsplit(
            " ",
            1
        )[0]
        + "..."
    )


# =====================================================
# HASHTAGS
# =====================================================

hashtags = dados.get(
    "hashtags",
    []
)


if not isinstance(
    hashtags,
    list
):

    hashtags = []


hashtags_limpas = []


for tag in hashtags:

    tag = str(
        tag
    ).strip()

    if not tag:

        continue


    tag = re.sub(
        r"\s+",
        "",
        tag
    )


    if not tag.startswith(
        "#"
    ):

        tag = "#" + tag


    if tag.lower() in {
        x.lower()
        for x in hashtags_limpas
    }:

        continue


    hashtags_limpas.append(
        tag
    )


# #Shorts sempre presente.
if not any(
    x.lower() == "#shorts"
    for x in hashtags_limpas
):

    hashtags_limpas.insert(
        0,
        "#Shorts"
    )


fallback_tags = [
    "#Mistério",
    "#Curiosidades",
    "#FatosReais",
    "#História"
]


for tag in fallback_tags:

    if len(
        hashtags_limpas
    ) >= 5:

        break


    if not any(
        x.lower()
        == tag.lower()
        for x in hashtags_limpas
    ):

        hashtags_limpas.append(
            tag
        )


hashtags = hashtags_limpas[:5]


# =====================================================
# COMENTÁRIO FIXADO
# =====================================================

pinned = str(
    dados.get(
        "pinned_comment",
        ""
    )
).strip()


if not pinned:

    pinned = (
        "Qual é a sua teoria "
        "sobre esse caso?"
    )


# =====================================================
# QUALITY SCORE
# =====================================================

best_score = ranking[
    0
]["score"]


if best_score >= 75:

    quality = "HIGH"

elif best_score >= 60:

    quality = "MEDIUM"

else:

    quality = "LOW"


# =====================================================
# SAÍDA
# =====================================================

saida = {
    "short_id":
        SHORT_ID,

    "topic":
        assunto,

    "titles":
        titles,

    "title_ranking":
        ranking,

    "chosen_title":
        chosen,

    "publish_quality":
        quality,

    "publish_score":
        best_score,

    "description":
        description,

    "hashtags":
        hashtags,

    "pinned_comment":
        pinned
}


with open(
    SAIDA_JSON,
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
    SAIDA_TXT,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "TÍTULO:\n"
    )

    f.write(
        chosen
    )

    f.write(
        "\n\nDESCRIÇÃO:\n"
    )

    f.write(
        description
    )

    f.write(
        "\n\nHASHTAGS:\n"
    )

    f.write(
        " ".join(
            hashtags
        )
    )

    f.write(
        "\n\nCOMENTÁRIO FIXADO:\n"
    )

    f.write(
        pinned
    )

    f.write(
        "\n"
    )


# =====================================================
# TERMINAL
# =====================================================

print(
    "TÍTULOS:"
)

print()


for numero, item in enumerate(
    ranking,
    start=1
):

    marca = (
        " <-- ESCOLHIDO"
        if numero == 1
        else ""
    )

    print(
        f"{numero}. "
        f"{item['title']}"
        f"{marca}"
    )

    print(
        f"   score="
        f"{item['score']:.1f}"
    )


print()

print(
    f"PUBLISH QUALITY: "
    f"{quality}"
)

print(
    f"PUBLISH SCORE: "
    f"{best_score:.1f}"
)

print()

print(
    "DESCRIÇÃO:"
)

print(
    description
)

print()

print(
    "HASHTAGS:"
)

print(
    " ".join(
        hashtags
    )
)

print()

print(
    "COMENTÁRIO FIXADO:"
)

print(
    pinned
)

print()

print(
    f"Arquivo:\n"
    f"{SAIDA_TXT}"
)

print()

print(
    "PUBLISH QUALITY GUARD: OK"
)

print()

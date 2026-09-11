#!/usr/bin/env python3

import os
import sys
import json
import re
import time
import shutil
import requests
from datetime import date


# =====================================================
# SHORTAUTO PRO
# NARRATIVE DIRECTOR - STABLE 3.2
# =====================================================

BASE = os.path.expanduser("~/ShortAutoPro")

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

HOOK = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.txt"
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
    f"short_pre_narrative_{SHORT_ID}.txt"
)

REPORT = os.path.join(
    BASE,
    "roteiros",
    f"narrative_{SHORT_ID}.json"
)


# =====================================================
# HELPERS
# =====================================================

def ler_txt(path):

    if not os.path.exists(path):
        return ""

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


def limpar(texto):

    texto = str(texto)

    texto = (
        texto
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    return " ".join(
        texto.split()
    )


def contar_palavras(texto):

    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            str(texto),
            flags=re.UNICODE
        )
    )


def normalizar(texto):

    return " ".join(
        re.findall(
            r"[a-z0-9à-ÿ]+",
            str(texto).lower()
        )
    )


def numeros(texto):

    return set(
        re.findall(
            r"\b\d+(?:[.,]\d+)?\b",
            str(texto)
        )
    )


def nomes_possiveis(texto):

    # Detector conservador de possíveis
    # nomes próprios. Não decide factualidade;
    # apenas ajuda a encontrar adições estranhas.

    palavras = re.findall(
        r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+\b",
        str(texto)
    )

    ignorar = {
        "O",
        "A",
        "Os",
        "As",
        "Em",
        "No",
        "Na",
        "Nos",
        "Nas",
        "Um",
        "Uma",
        "Depois",
        "Durante",
        "Quando",
        "Mas",
        "Por",
        "Para",
        "Segundo"
    }

    return {
        x
        for x in palavras
        if x not in ignorar
    }


INGLES_COMUM = {
    "tragically",
    "however",
    "although",
    "meanwhile",
    "therefore",
    "apparently",
    "suddenly",
    "eventually",
    "finally",
    "reportedly",
    "according"
}


def detectar_ingles(texto):

    palavras = {
        x.lower()
        for x in re.findall(
            r"\b[a-zA-Z]+\b",
            str(texto)
        )
    }

    return sorted(
        palavras.intersection(
            INGLES_COMUM
        )
    )


# =====================================================
# ENTRADAS
# =====================================================

roteiro_original = ler_txt(
    ROTEIRO
)

fonte = ler_txt(
    FONTE
)

hook = ler_txt(
    HOOK
)

assunto = (
    ler_txt(TOPIC_REAL)
    or ler_txt(TOPIC_FALLBACK)
)


if not roteiro_original:

    sys.exit(
        "ERRO: roteiro final não encontrado."
    )


if not API_KEY:

    print(
        "AVISO Narrative Director: "
        "Gemini não configurada."
    )

    print(
        "Mantendo roteiro original."
    )

    raise SystemExit(0)


# Backup antes de qualquer mudança.

shutil.copy2(
    ROTEIRO,
    BACKUP
)


# =====================================================
# PROMPT
# =====================================================

prompt = f"""
Você é editor-chefe de mini-documentários para
YouTube Shorts.

Sua tarefa é melhorar SOMENTE A ESTRUTURA NARRATIVA
de um roteiro factual já pesquisado.

ASSUNTO:

{assunto}

HOOK ESCOLHIDO:

{hook}

ROTEIRO FACTUAL ATUAL:

========================
{roteiro_original}
========================

FONTE FACTUAL:

========================
{fonte[:15000]}
========================

==================================================
OBJETIVO
==================================================

Transforme o texto em uma narrativa extremamente
fluida para um Short de aproximadamente 35 a 45 segundos.

O espectador deve sentir progressão.

A estrutura desejada é:

BEAT 1 — HOOK
0 a ~3 segundos

Uma frase imediata que cria curiosidade.

Se HOOK ESCOLHIDO estiver preenchido, preserve o
sentido e preferencialmente a própria frase.

BEAT 2 — CONTEXTO
~3 a 10 segundos

Explique rapidamente quem, onde e quando.

BEAT 3 — ESCALADA
~10 a 25 segundos

Apresente os acontecimentos que tornam o caso
cada vez mais estranho, grave ou interessante.

BEAT 4 — EVIDÊNCIA / VIRADA
~25 a 35 segundos

Apresente o detalhe mais importante, prova,
descoberta, consequência ou mudança de direção.

BEAT 5 — PAYOFF
~35 a 43 segundos

Diga o que sabemos hoje ou o que permaneceu
sem resposta.

Feche com uma pergunta curta que gere comentário.

==================================================
REGRAS OBRIGATÓRIAS
==================================================

- 105 a 125 palavras REAIS.

- Português natural do Brasil.

- Nenhuma palavra em inglês desnecessária.

- Não invente fatos.

- Não invente nomes.

- Não invente datas.

- Não invente números.

- Não transforme hipótese em fato.

- Não transforme relato em confirmação.

- Não acrescente conclusão que a fonte não sustenta.

- Preserve os fatos essenciais do roteiro original.

- Evite introduções como:
  "Hoje vamos..."
  "Você sabia..."
  "Neste vídeo..."

- Frases curtas e fortes.

- Preferencialmente menos de 22 palavras por frase.

- Evite repetir a mesma informação.

- Evite linguagem exagerada como:
  "a verdade definitiva"
  "prova absoluta"
  "o caso mais chocante da história"

- Não peça inscrição no meio do roteiro.

- CTA final deve priorizar comentário/opinião.

- O texto deve soar como mini-documentário,
  não como lista de curiosidades.

==================================================
SAÍDA
==================================================

Responda SOMENTE JSON válido:

{{
  "script": "roteiro completo",
  "beats": [
    {{
      "beat": "hook",
      "text": "trecho"
    }},
    {{
      "beat": "context",
      "text": "trecho"
    }},
    {{
      "beat": "escalation",
      "text": "trecho"
    }},
    {{
      "beat": "evidence_or_turn",
      "text": "trecho"
    }},
    {{
      "beat": "payoff",
      "text": "trecho"
    }}
  ]
}}

Sem markdown.
Sem explicações fora do JSON.
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
            0.22,

        "maxOutputTokens":
            2200
    }
}


bruto = None


print()
print("================================")
print("NARRATIVE DIRECTOR - STABLE 3.2")
print("================================")
print()


for tentativa in range(
    1,
    4
):

    print(
        f"Narrative Director tentativa "
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

            print(
                f"AVISO Narrative Director: {e}"
            )

            print(
                "Mantendo roteiro original."
            )

            raise SystemExit(0)

        time.sleep(4)

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

        time.sleep(6)

        continue


    print(
        f"AVISO Narrative Director HTTP "
        f"{r.status_code}."
    )

    print(
        "Mantendo roteiro original."
    )

    raise SystemExit(0)


if not bruto:

    print(
        "AVISO: resposta vazia."
    )

    print(
        "Mantendo roteiro original."
    )

    raise SystemExit(0)


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

    print(
        "AVISO: JSON inválido."
    )

    print(
        "Mantendo roteiro original."
    )

    raise SystemExit(0)


novo_roteiro = limpar(
    dados.get(
        "script",
        ""
    )
)

beats = dados.get(
    "beats",
    []
)


# =====================================================
# QUALITY / FACTUAL GUARD
# =====================================================

problemas = []


qtd = contar_palavras(
    novo_roteiro
)


if not (
    105
    <= qtd
    <= 125
):

    problemas.append(
        f"palavras={qtd}"
    )


if detectar_ingles(
    novo_roteiro
):

    problemas.append(
        "ingles_detectado"
    )


# Números novos são particularmente perigosos.

base_numeros = (
    numeros(
        roteiro_original
    )
    | numeros(
        fonte
    )
)

novos_numeros = (
    numeros(
        novo_roteiro
    )
    - base_numeros
)


if novos_numeros:

    problemas.append(
        "numeros_novos:"
        + ",".join(
            sorted(
                novos_numeros
            )
        )
    )


# Nomes próprios novos também são suspeitos.

base_nomes = (
    nomes_possiveis(
        roteiro_original
    )
    | nomes_possiveis(
        fonte
    )
    | nomes_possiveis(
        assunto
    )
)

novos_nomes = (
    nomes_possiveis(
        novo_roteiro
    )
    - base_nomes
)


if novos_nomes:

    problemas.append(
        "nomes_novos:"
        + ",".join(
            sorted(
                novos_nomes
            )
        )
    )


if not isinstance(
    beats,
    list
) or len(beats) != 5:

    problemas.append(
        "beats_invalidos"
    )


# =====================================================
# FRASES LONGAS
# =====================================================

frases = [
    x.strip()
    for x in re.split(
        r"[.!?]+",
        novo_roteiro
    )
    if x.strip()
]

longas = [
    x
    for x in frases
    if contar_palavras(
        x
    ) > 24
]


if len(
    longas
) >= 3:

    problemas.append(
        f"frases_longas={len(longas)}"
    )


# =====================================================
# RESULTADO
# =====================================================

aprovado = (
    bool(novo_roteiro)
    and len(problemas) == 0
)


report = {
    "short_id":
        SHORT_ID,

    "topic":
        assunto,

    "approved":
        aprovado,

    "original_words":
        contar_palavras(
            roteiro_original
        ),

    "new_words":
        qtd,

    "problems":
        problemas,

    "beats":
        beats,

    "backup":
        BACKUP
}


if aprovado:

    with open(
        ROTEIRO,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            novo_roteiro
        )

        f.write(
            "\n"
        )


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


# =====================================================
# TERMINAL
# =====================================================

print()

print(
    f"Roteiro original: "
    f"{report['original_words']} palavras"
)

print(
    f"Roteiro dirigido: "
    f"{report['new_words']} palavras"
)

print()


if aprovado:

    print(
        "ESTRUTURA:"
    )

    print()

    for beat in beats:

        if not isinstance(
            beat,
            dict
        ):
            continue

        print(
            f"{str(beat.get('beat', '?')).upper()}:"
        )

        print(
            limpar(
                beat.get(
                    "text",
                    ""
                )
            )
        )

        print()


    print(
        "NARRATIVE QUALITY: PASS"
    )

    print(
        "Roteiro novo ativado."
    )

else:

    print(
        "NARRATIVE QUALITY: REJECTED"
    )

    print(
        "Problemas:"
    )

    for problema in problemas:

        print(
            f"  - {problema}"
        )


    print()

    print(
        "Roteiro original preservado."
    )


print()

print(
    f"Relatório:\n{REPORT}"
)

print()

print(
    "NARRATIVE DIRECTOR: OK"
)

print()

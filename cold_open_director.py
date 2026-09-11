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
# COLD OPEN DIRECTOR - STABLE 3.3
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

HOOK_ATUAL = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.txt"
)

BACKUP = os.path.join(
    BASE,
    "roteiros",
    f"short_pre_cold_open_{SHORT_ID}.txt"
)

REPORT = os.path.join(
    BASE,
    "roteiros",
    f"cold_open_{SHORT_ID}.json"
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

    return " ".join(
        str(texto)
        .replace("```json", "")
        .replace("```", "")
        .split()
    )


def contar_palavras(texto):

    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            str(texto),
            flags=re.UNICODE
        )
    )


def primeira_frase(texto):

    partes = re.split(
        r"(?<=[.!?])\s+",
        str(texto).strip()
    )

    if partes:
        return partes[0].strip()

    return ""


def numeros(texto):

    return set(
        re.findall(
            r"\b\d+(?:[.,]\d+)?\b",
            str(texto)
        )
    )


def nomes_possiveis(texto):

    palavras = re.findall(
        r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]"
        r"[a-záàâãéêíóôõúç]+\b",
        str(texto)
    )

    ignorar = {
        "O", "A", "Os", "As",
        "Em", "No", "Na",
        "Nos", "Nas",
        "Um", "Uma",
        "Depois", "Durante",
        "Quando", "Mas",
        "Por", "Para",
        "Segundo", "Como"
    }

    return {
        x
        for x in palavras
        if x not in ignorar
    }


# =====================================================
# SCORE LOCAL DO COLD OPEN
# =====================================================

ABERTURAS_FRACAS = [
    "hoje vamos",
    "neste vídeo",
    "nesse vídeo",
    "você sabia",
    "voce sabia",
    "vamos conhecer",
    "essa é a história",
    "essa e a historia"
]


GATILHOS_NARRATIVOS = [
    "desapareceu",
    "sumiu",
    "encontrado",
    "encontraram",
    "morreu",
    "corpo",
    "último",
    "ultimo",
    "ninguém",
    "ninguem",
    "nunca",
    "sem deixar",
    "segundos",
    "minutos",
    "horas",
    "dias",
    "mas",
    "porém",
    "porem",
    "até hoje",
    "ate hoje"
]


def score_abertura(frase):

    frase = limpar(
        frase
    )

    qtd = contar_palavras(
        frase
    )

    score = 50.0

    lower = frase.lower()


    # ---------------------------------
    # TAMANHO
    # ---------------------------------

    if 7 <= qtd <= 13:

        score += 25

    elif 5 <= qtd <= 16:

        score += 15

    elif qtd > 20:

        score -= 20

    elif qtd < 4:

        score -= 15


    # ---------------------------------
    # INTRODUÇÕES FRACAS
    # ---------------------------------

    for termo in ABERTURAS_FRACAS:

        if lower.startswith(
            termo
        ):

            score -= 35


    # ---------------------------------
    # TENSÃO FACTUAL
    # ---------------------------------

    hits = 0

    for termo in GATILHOS_NARRATIVOS:

        if termo in lower:

            hits += 1


    score += min(
        hits * 5,
        20
    )


    # ---------------------------------
    # PERGUNTA
    # ---------------------------------

    if "?" in frase:

        score += 3


    return max(
        0.0,
        min(
            score,
            100.0
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

assunto = (
    ler_txt(
        TOPIC_REAL
    )
    or ler_txt(
        TOPIC_FALLBACK
    )
)

hook_anterior = ler_txt(
    HOOK_ATUAL
)


if not roteiro_original:

    sys.exit(
        "ERRO: roteiro não encontrado."
    )


# Backup sempre.

shutil.copy2(
    ROTEIRO,
    BACKUP
)


abertura_anterior = primeira_frase(
    roteiro_original
)

score_anterior = score_abertura(
    abertura_anterior
)


print()
print("================================")
print("COLD OPEN DIRECTOR - STABLE 3.3")
print("================================")
print()

print(
    f"Abertura atual: "
    f"{abertura_anterior}"
)

print(
    f"Score atual: "
    f"{score_anterior:.1f}/100"
)

print()


# =====================================================
# ABERTURA JÁ FORTE
# =====================================================

if score_anterior >= 82:

    print(
        "COLD OPEN: JÁ FORTE"
    )

    print(
        "Nenhuma reescrita necessária."
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

                "changed":
                    False,

                "reason":
                    "already_strong",

                "before":
                    abertura_anterior,

                "before_score":
                    score_anterior,

                "after":
                    abertura_anterior,

                "after_score":
                    score_anterior
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    raise SystemExit(0)


# =====================================================
# SEM API = MANTER
# =====================================================

if not API_KEY:

    print(
        "AVISO: Gemini não configurada."
    )

    print(
        "Roteiro original preservado."
    )

    raise SystemExit(0)


# =====================================================
# PROMPT
# =====================================================

prompt = f"""
Você é especialista em cold opens para
mini-documentários factuais de YouTube Shorts.

ASSUNTO:

{assunto}

HOOK ANTERIOR:

{hook_anterior}

ROTEIRO ATUAL:

========================
{roteiro_original}
========================

FONTE FACTUAL:

========================
{fonte[:16000]}
========================

==================================================
OBJETIVO
==================================================

Melhore SOMENTE os primeiros segundos da narrativa.

O roteiro inteiro deve continuar tendo entre
105 e 125 palavras.

A PRIMEIRA FRASE deve:

- ter preferencialmente 7 a 13 palavras;
- ser entendida imediatamente;
- apresentar o detalhe factual mais intrigante;
- criar uma lacuna de curiosidade;
- fazer o espectador querer ouvir a frase seguinte.

A SEGUNDA FRASE deve rapidamente fornecer contexto.

==================================================
EXEMPLO DE PRINCÍPIO
==================================================

FRACO:

"Em 1978, um jovem piloto australiano fazia um voo."

FORTE:

"Um piloto desapareceu logo após relatar uma luz sobre seu avião."

O segundo formato começa pelo acontecimento extraordinário
e explica data/local logo depois.

==================================================
REGRAS DE SEGURANÇA
==================================================

- Não invente fatos.

- Não invente números.

- Não invente nomes.

- Não invente falas.

- Não transforme hipótese em fato.

- Não transforme relato em confirmação.

- Não use clickbait falso.

- Não use:
  "Você não vai acreditar"
  "Isso vai te chocar"
  "A verdade finalmente revelada"

- Não use ALL CAPS.

- Não exagere adjetivos.

- Preserve a conclusão factual do roteiro.

- Preserve o CTA final.

- Português natural do Brasil.

- Frases curtas.

- Não altere o sentido factual do restante da história.

==================================================
SAÍDA
==================================================

Retorne SOMENTE JSON:

{{
  "script": "roteiro completo revisado",
  "cold_open": "primeira frase",
  "context_line": "segunda frase",
  "reason": "explicação curta"
}}

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
            0.18,

        "maxOutputTokens":
            1800
    }
}


bruto = None


for tentativa in range(
    1,
    4
):

    print(
        f"Cold Open tentativa "
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
                f"AVISO Cold Open: {e}"
            )

            print(
                "Roteiro original preservado."
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
        f"AVISO Cold Open HTTP "
        f"{r.status_code}"
    )

    print(
        "Roteiro original preservado."
    )

    raise SystemExit(0)


if not bruto:

    print(
        "AVISO: resposta vazia."
    )

    raise SystemExit(0)


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
        "AVISO: Cold Open retornou JSON inválido."
    )

    print(
        "Roteiro original preservado."
    )

    raise SystemExit(0)


novo_roteiro = limpar(
    dados.get(
        "script",
        ""
    )
)

nova_abertura = primeira_frase(
    novo_roteiro
)


# =====================================================
# FACTUAL GUARD
# =====================================================

problemas = []


qtd = contar_palavras(
    novo_roteiro
)


if not 105 <= qtd <= 125:

    problemas.append(
        f"palavras={qtd}"
    )


# ---------------------------------
# NOVOS NÚMEROS
# ---------------------------------

base_nums = (
    numeros(
        roteiro_original
    )
    | numeros(
        fonte
    )
)


novos_nums = (
    numeros(
        novo_roteiro
    )
    - base_nums
)


if novos_nums:

    problemas.append(
        "numeros_novos:"
        + ",".join(
            sorted(
                novos_nums
            )
        )
    )


# ---------------------------------
# NOVOS NOMES
# ---------------------------------

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


# =====================================================
# SCORE
# =====================================================

score_novo = score_abertura(
    nova_abertura
)


melhoria = (
    score_novo
    - score_anterior
)


if score_novo < 72:

    problemas.append(
        f"cold_open_fraco={score_novo:.1f}"
    )


if melhoria < 5:

    problemas.append(
        f"melhoria_insuficiente={melhoria:.1f}"
    )


# =====================================================
# APROVAR / REJEITAR
# =====================================================

aprovado = (
    bool(
        novo_roteiro
    )
    and not problemas
)


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


    # Atualiza o hook para que a etapa visual
    # conheça exatamente o cold open final.

    with open(
        HOOK_ATUAL,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            nova_abertura
        )

        f.write(
            "\n"
        )


report = {
    "short_id":
        SHORT_ID,

    "changed":
        aprovado,

    "before":
        abertura_anterior,

    "before_score":
        score_anterior,

    "after":
        (
            nova_abertura
            if aprovado
            else abertura_anterior
        ),

    "candidate_after":
        nova_abertura,

    "candidate_score":
        score_novo,

    "improvement":
        melhoria,

    "problems":
        problemas,

    "reason":
        limpar(
            dados.get(
                "reason",
                ""
            )
        ),

    "backup":
        BACKUP
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


# =====================================================
# TERMINAL
# =====================================================

print()

print(
    f"Candidato: "
    f"{nova_abertura}"
)

print(
    f"Score candidato: "
    f"{score_novo:.1f}/100"
)

print(
    f"Melhoria: "
    f"{melhoria:+.1f}"
)

print()


if aprovado:

    print(
        "COLD OPEN QUALITY: PASS"
    )

    print(
        "Cold open novo ativado."
    )

else:

    print(
        "COLD OPEN QUALITY: REJECTED"
    )

    for problema in problemas:

        print(
            f"  - {problema}"
        )


    print()

    print(
        "Roteiro anterior preservado."
    )


print()

print(
    f"Relatório:\n{REPORT}"
)

print()

print(
    "COLD OPEN DIRECTOR: OK"
)

print()

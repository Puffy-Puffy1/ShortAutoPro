#!/usr/bin/env python3

import os
import sys
import json
import re
import subprocess
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

AUDIO = os.path.join(
    BASE,
    "audios",
    f"short_{SHORT_ID}.mp3"
)

TEMP = os.path.join(
    BASE,
    "temp",
    SHORT_ID
)

VIDEO_DIR = os.path.join(
    BASE,
    "videos"
)

WHISPER = os.path.expanduser(
    "~/whisper.cpp/build/bin/whisper-cli"
)

MODEL = os.path.expanduser(
    "~/whisper.cpp/models/ggml-base.bin"
)

WAV = os.path.join(
    TEMP,
    "whisper_dinamico.wav"
)

JSON_BASE = os.path.join(
    TEMP,
    "whisper_timing"
)

JSON_PATH = JSON_BASE + ".json"

ASS_FINAL = os.path.join(
    VIDEO_DIR,
    f"short_{SHORT_ID}.ass"
)

os.makedirs(TEMP, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)


# =====================================
# VERIFICAÇÕES
# =====================================

for arquivo in [
    ROTEIRO,
    AUDIO,
    WHISPER,
    MODEL
]:
    if not os.path.exists(arquivo):
        sys.exit(
            f"ERRO: arquivo não encontrado:\n"
            f"{arquivo}"
        )


# =====================================
# ROTEIRO ORIGINAL
# =====================================

with open(
    ROTEIRO,
    "r",
    encoding="utf-8"
) as f:
    texto_original = f.read().strip()

texto_original = re.sub(
    r"\s+",
    " ",
    texto_original
)

palavras_originais = texto_original.split()

if not palavras_originais:
    sys.exit(
        "ERRO: roteiro original vazio."
    )


print()
print("================================")
print("LEGENDA DINAMICA V2")
print("ROTEIRO ORIGINAL + WHISPER")
print("================================")
print()

print(
    f"Palavras no roteiro: "
    f"{len(palavras_originais)}"
)


# =====================================
# ÁUDIO PARA WHISPER
# =====================================

print()
print("1/4 Preparando áudio...")

try:
    subprocess.run(
        [
            "ffmpeg",
            "-y",

            "-i",
            AUDIO,

            "-ar",
            "16000",

            "-ac",
            "1",

            "-c:a",
            "pcm_s16le",

            WAV
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

except subprocess.CalledProcessError:

    sys.exit(
        "ERRO preparando áudio."
    )


# =====================================
# WHISPER + TIMESTAMPS
# =====================================

print("2/4 Analisando tempos da fala...")

try:
    subprocess.run(
        [
            WHISPER,

            "-m",
            MODEL,

            "-f",
            WAV,

            "-l",
            "pt",

            "-ojf",

            "-of",
            JSON_BASE,

            "-dtw",
            "base",

            "-t",
            "4",

            "-np"
        ],
        check=True
    )

except subprocess.CalledProcessError:

    sys.exit(
        "ERRO: Whisper não conseguiu "
        "analisar o áudio."
    )


if not os.path.exists(JSON_PATH):

    sys.exit(
        "ERRO: JSON do Whisper não foi criado."
    )


with open(
    JSON_PATH,
    "r",
    encoding="utf-8"
) as f:
    dados = json.load(f)


# =====================================
# EXTRAI TEMPOS DO WHISPER
# =====================================

slots = []

for segmento in dados.get(
    "transcription",
    []
):

    for token in segmento.get(
        "tokens",
        []
    ):

        texto = token.get(
            "text",
            ""
        )

        if not texto:
            continue

        # ignora tokens internos
        if texto.startswith("[_"):
            continue

        offsets = token.get(
            "offsets",
            {}
        )

        inicio = offsets.get("from")
        fim = offsets.get("to")

        if inicio is None or fim is None:
            continue

        texto_limpo = texto.strip()

        if not texto_limpo:
            continue

        slots.append(
            {
                "texto": texto,
                "inicio": int(inicio),
                "fim": int(fim)
            }
        )


if not slots:

    sys.exit(
        "ERRO: Whisper não retornou "
        "timestamps utilizáveis."
    )


# =====================================
# JUNTA TOKENS EM PALAVRAS WHISPER
# =====================================

palavras_whisper = []

pontuacao = set(
    ".,!?;:%)]}»"
)

for token in slots:

    bruto = token["texto"]
    limpo = bruto.strip()

    if not limpo:
        continue

    # pontuação isolada
    if (
        len(limpo) <= 3
        and all(
            c in pontuacao
            for c in limpo
        )
        and palavras_whisper
    ):

        palavras_whisper[-1]["fim"] = max(
            palavras_whisper[-1]["fim"],
            token["fim"]
        )

        continue

    nova_palavra = (
        bruto[:1].isspace()
    )

    if nova_palavra or not palavras_whisper:

        palavras_whisper.append(
            {
                "inicio": token["inicio"],
                "fim": token["fim"]
            }
        )

    else:

        palavras_whisper[-1]["fim"] = max(
            palavras_whisper[-1]["fim"],
            token["fim"]
        )


if not palavras_whisper:

    sys.exit(
        "ERRO: nenhuma palavra temporal "
        "detectada pelo Whisper."
    )


print(
    f"Palavras detectadas pelo Whisper: "
    f"{len(palavras_whisper)}"
)


# =====================================
# CRIA UMA LINHA DE TEMPO CONTÍNUA
# =====================================

inicio_total = palavras_whisper[0]["inicio"]
fim_total = palavras_whisper[-1]["fim"]

if fim_total <= inicio_total:
    sys.exit(
        "ERRO: duração temporal inválida."
    )


# Lista de pontos temporais do Whisper.
# Usamos esses pontos para preservar
# ritmo, pausas e acelerações da fala.

centros = []

for p in palavras_whisper:

    centro = (
        p["inicio"] + p["fim"]
    ) / 2

    centros.append(centro)


N_ORIGINAL = len(palavras_originais)
N_WHISPER = len(centros)


def interpolar_tempo(indice_original):

    # posição relativa da palavra original
    if N_ORIGINAL <= 1:
        return inicio_total

    pos = (
        indice_original
        / (N_ORIGINAL - 1)
    ) * (N_WHISPER - 1)

    esquerda = int(pos)
    direita = min(
        esquerda + 1,
        N_WHISPER - 1
    )

    fracao = pos - esquerda

    tempo = (
        centros[esquerda]
        * (1 - fracao)
        +
        centros[direita]
        * fracao
    )

    return int(tempo)


# centro temporal de cada palavra original
tempos_centrais = [
    interpolar_tempo(i)
    for i in range(N_ORIGINAL)
]


# converte centros em início/fim
palavras_timed = []

for i, palavra in enumerate(
    palavras_originais
):

    centro = tempos_centrais[i]

    if i == 0:

        inicio = inicio_total

    else:

        inicio = int(
            (
                tempos_centrais[i - 1]
                + centro
            ) / 2
        )

    if i == N_ORIGINAL - 1:

        fim = fim_total

    else:

        fim = int(
            (
                centro
                + tempos_centrais[i + 1]
            ) / 2
        )

    if fim <= inicio:
        fim = inicio + 80

    palavras_timed.append(
        {
            "texto": palavra,
            "inicio": inicio,
            "fim": fim
        }
    )


# =====================================
# FUNÇÕES ASS
# =====================================

def ass_time(ms):

    ms = max(
        0,
        int(ms)
    )

    horas = ms // 3600000
    ms %= 3600000

    minutos = ms // 60000
    ms %= 60000

    segundos = ms // 1000

    cent = (
        ms % 1000
    ) // 10

    return (
        f"{horas}:"
        f"{minutos:02d}:"
        f"{segundos:02d}."
        f"{cent:02d}"
    )


def limpar_ass(texto):

    return (
        texto
        .replace("\\", "")
        .replace("{", "")
        .replace("}", "")
    )


# =====================================
# AGRUPA 3 PALAVRAS
# =====================================

PALAVRAS_POR_GRUPO = 3

grupos = []

for i in range(
    0,
    len(palavras_timed),
    PALAVRAS_POR_GRUPO
):

    grupos.append(
        palavras_timed[
            i:i + PALAVRAS_POR_GRUPO
        ]
    )


# =====================================
# CABEÇALHO ASS
# =====================================

cabecalho = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Dynamic,DejaVu Sans,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,1,2,90,90,250,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


# =====================================
# CRIA EVENTOS
# =====================================

print("3/4 Criando destaque dinâmico...")

eventos = []

for grupo in grupos:

    for indice, palavra in enumerate(
        grupo
    ):

        inicio = palavra["inicio"]

        if indice + 1 < len(grupo):

            fim = grupo[
                indice + 1
            ]["inicio"]

        else:

            fim = palavra["fim"]

        fim = max(
            fim,
            inicio + 100
        )

        partes = []

        for j, outra in enumerate(
            grupo
        ):

            texto = limpar_ass(
                outra["texto"]
            )

            if j == indice:

                # AMARELO
                partes.append(
                    r"{\c&H00FFFF&\b1}"
                    + texto
                    + r"{\c&HFFFFFF&\b1}"
                )

            else:

                partes.append(
                    texto
                )

        frase = " ".join(partes)

        eventos.append(
            "Dialogue: 0,"
            + ass_time(inicio)
            + ","
            + ass_time(fim)
            + ",Dynamic,,0,0,0,,"
            + frase
        )


with open(
    ASS_FINAL,
    "w",
    encoding="utf-8"
) as f:

    f.write(cabecalho)

    for evento in eventos:

        f.write(
            evento + "\n"
        )


if os.path.exists(WAV):

    try:
        os.remove(WAV)
    except:
        pass


print("4/4 Finalizando...")

print()
print("================================")
print("LEGENDA DINAMICA V2 CRIADA!")
print("================================")
print()
print(
    f"Palavras do roteiro: "
    f"{len(palavras_originais)}"
)
print(
    f"Eventos gerados: "
    f"{len(eventos)}"
)
print()
print(
    f"Arquivo:\n{ASS_FINAL}"
)
print()

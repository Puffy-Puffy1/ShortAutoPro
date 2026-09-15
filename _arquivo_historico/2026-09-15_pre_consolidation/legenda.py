#!/usr/bin/env python3

import os
import sys
import re
import subprocess
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

AUDIO = os.path.join(
    BASE, "audios", f"short_{SHORT_ID}.mp3"
)

VIDEO_DIR = os.path.join(BASE, "videos")
TEMP_DIR = os.path.join(BASE, "temp", SHORT_ID)

WHISPER = os.path.expanduser(
    "~/whisper.cpp/build/bin/whisper-cli"
)

MODEL = os.path.expanduser(
    "~/whisper.cpp/models/ggml-base.bin"
)

WAV = os.path.join(
    TEMP_DIR, "whisper_audio.wav"
)

WHISPER_BASE = os.path.join(
    TEMP_DIR, "whisper_original"
)

WHISPER_SRT = WHISPER_BASE + ".srt"

SRT_FINAL = os.path.join(
    VIDEO_DIR,
    f"short_{SHORT_ID}.srt"
)

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

if not os.path.exists(AUDIO):
    sys.exit(f"ERRO: áudio não encontrado:\n{AUDIO}")

if not os.path.exists(WHISPER):
    sys.exit("ERRO: whisper-cli não encontrado.")

if not os.path.exists(MODEL):
    sys.exit("ERRO: modelo Whisper não encontrado.")


def tempo_ms(t):
    h, m, resto = t.split(":")
    s, ms = resto.split(",")

    return (
        int(h) * 3600000
        + int(m) * 60000
        + int(s) * 1000
        + int(ms)
    )


def formato(ms):
    ms = max(0, int(ms))

    h = ms // 3600000
    ms %= 3600000

    m = ms // 60000
    ms %= 60000

    s = ms // 1000
    ms %= 1000

    return (
        f"{h:02d}:"
        f"{m:02d}:"
        f"{s:02d},"
        f"{ms:03d}"
    )


print()
print("================================")
print("GERANDO LEGENDA COM WHISPER...")
print("================================")
print()

# MP3 -> WAV 16 kHz
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-i", AUDIO,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        WAV
    ],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

print("Transcrevendo...")

subprocess.run(
    [
        WHISPER,
        "-m", MODEL,
        "-f", WAV,
        "-l", "pt",
        "-osrt",
        "-of", WHISPER_BASE,
        "-t", "4",
        "-np"
    ],
    check=True
)

if not os.path.exists(WHISPER_SRT):
    sys.exit("ERRO: Whisper não criou o SRT.")

# Lê o SRT em blocos
with open(
    WHISPER_SRT,
    "r",
    encoding="utf-8"
) as f:
    bruto = f.read().strip()

blocos_originais = re.split(
    r"\n\s*\n",
    bruto
)

resultado = []
contador = 1

for bloco in blocos_originais:

    linhas = [
        x.strip()
        for x in bloco.splitlines()
        if x.strip()
    ]

    if len(linhas) < 3:
        continue

    tempo = linhas[1]

    if "-->" not in tempo:
        continue

    inicio_txt, fim_txt = [
        x.strip()
        for x in tempo.split("-->", 1)
    ]

    texto = " ".join(linhas[2:]).strip()

    if not texto:
        continue

    palavras = texto.split()

    # 3 palavras por bloco
    grupos = [
        palavras[i:i + 3]
        for i in range(0, len(palavras), 3)
    ]

    inicio = tempo_ms(inicio_txt)
    fim = tempo_ms(fim_txt)

    duracao = max(
        fim - inicio,
        1
    )

    pesos = [
        max(1, len(" ".join(g)))
        for g in grupos
    ]

    peso_total = sum(pesos)

    cursor = inicio

    for indice, grupo in enumerate(grupos):

        frase = " ".join(grupo)

        if indice == len(grupos) - 1:
            fim_grupo = fim
        else:
            parte = (
                duracao
                * pesos[indice]
                / peso_total
            )

            fim_grupo = int(
                cursor + parte
            )

        if fim_grupo <= cursor:
            continue

        resultado.append(
            (
                contador,
                cursor,
                fim_grupo,
                frase
            )
        )

        contador += 1
        cursor = fim_grupo


if not resultado:
    sys.exit(
        "ERRO: nenhuma legenda foi criada."
    )

with open(
    SRT_FINAL,
    "w",
    encoding="utf-8"
) as out:

    for numero, inicio, fim, texto in resultado:

        out.write(f"{numero}\n")
        out.write(
            f"{formato(inicio)} --> "
            f"{formato(fim)}\n"
        )
        out.write(f"{texto}\n\n")


if os.path.exists(WAV):
    os.remove(WAV)

print()
print("================================")
print("LEGENDA CRIADA!")
print("================================")
print()
print(f"Blocos: {len(resultado)}")
print(f"Arquivo: {SRT_FINAL}")
print()

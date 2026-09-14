#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
from datetime import date

from subtitle_alignment import align_word_timings

BASE = os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
ROTEIRO = os.path.join(BASE, "roteiros", f"short_{SHORT_ID}.txt")
AUDIO = os.path.join(BASE, "audios", f"short_{SHORT_ID}.mp3")
TEMP = os.path.join(BASE, "temp", SHORT_ID)
VIDEO_DIR = os.path.join(BASE, "videos")
WHISPER = os.path.expanduser(
    os.getenv("WHISPER_CLI", "~/whisper.cpp/build/bin/whisper-cli")
)
MODEL = os.path.expanduser(
    os.getenv("WHISPER_MODEL", "~/whisper.cpp/models/ggml-base.bin")
)
WAV = os.path.join(TEMP, "whisper_dinamico.wav")
JSON_BASE = os.path.join(TEMP, "whisper_timing")
JSON_PATH = JSON_BASE + ".json"
ASS_FINAL = os.path.join(VIDEO_DIR, f"short_{SHORT_ID}.ass")

os.makedirs(TEMP, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)


def fail(message):
    try:
        if os.path.exists(WAV):
            os.remove(WAV)
    except OSError:
        pass
    raise SystemExit(f"ERRO: {message}")


def ass_time(ms):
    ms = max(0, int(ms))
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    cent = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cent:02d}"


def clean_ass_text(text):
    return (
        str(text)
        .replace("\\", "")
        .replace("{", "")
        .replace("}", "")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def whisper_words(data):
    slots = []
    transcription = data.get("transcription", [])
    if not isinstance(transcription, list):
        return []

    for segment in transcription:
        if not isinstance(segment, dict):
            continue
        tokens = segment.get("tokens", [])
        if not isinstance(tokens, list):
            continue
        for token in tokens:
            if not isinstance(token, dict):
                continue
            raw = str(token.get("text", ""))
            stripped = raw.strip()
            if not stripped or stripped.startswith("[_"):
                continue
            offsets = token.get("offsets", {})
            if not isinstance(offsets, dict):
                continue
            try:
                start = int(offsets.get("from"))
                end = int(offsets.get("to"))
            except (TypeError, ValueError):
                continue
            if end <= start:
                continue
            slots.append({"raw": raw, "start": start, "end": end})

    words = []
    punctuation = set(".,!?;:%)]}»…")

    for token in slots:
        raw = token["raw"]
        stripped = raw.strip()

        if stripped and all(ch in punctuation for ch in stripped) and words:
            words[-1]["text"] += stripped
            words[-1]["end"] = max(words[-1]["end"], token["end"])
            continue

        new_word = bool(raw[:1].isspace()) or not words
        if new_word:
            words.append(
                {"text": stripped, "start": token["start"], "end": token["end"]}
            )
        else:
            words[-1]["text"] += stripped
            words[-1]["end"] = max(words[-1]["end"], token["end"])

    return [x for x in words if x["text"].strip()]


for path, label in (
    (ROTEIRO, "roteiro"),
    (AUDIO, "áudio"),
    (WHISPER, "Whisper CLI"),
    (MODEL, "modelo Whisper"),
):
    if not os.path.isfile(path):
        fail(f"{label} não encontrado: {path}")

try:
    with open(ROTEIRO, "r", encoding="utf-8") as f:
        texto_original = re.sub(r"\s+", " ", f.read().strip())
except Exception as exc:
    fail(f"não foi possível ler roteiro: {exc}")

palavras_originais = texto_original.split()
if not palavras_originais:
    fail("roteiro original vazio")

print()
print("================================")
print("LEGENDA DINÂMICA V3")
print("ALINHAMENTO POR CONTEÚDO + WHISPER")
print("================================")
print(f"Palavras no roteiro: {len(palavras_originais)}")
print()

print("1/4 Preparando áudio...")
try:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", AUDIO,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", WAV,
        ],
        check=True,
        timeout=120,
    )
except subprocess.TimeoutExpired:
    fail("conversão para Whisper excedeu o tempo limite")
except subprocess.CalledProcessError as exc:
    fail(f"FFmpeg não conseguiu preparar áudio (código {exc.returncode})")

print("2/4 Analisando fala com Whisper...")
try:
    subprocess.run(
        [
            WHISPER, "-m", MODEL, "-f", WAV, "-l", "pt",
            "-ojf", "-of", JSON_BASE, "-dtw", "base", "-t", "4", "-np",
        ],
        check=True,
        timeout=240,
    )
except subprocess.TimeoutExpired:
    fail("Whisper excedeu 240 segundos")
except subprocess.CalledProcessError as exc:
    fail(f"Whisper falhou (código {exc.returncode})")

if not os.path.isfile(JSON_PATH):
    fail("JSON do Whisper não foi criado")

try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        dados = json.load(f)
except Exception as exc:
    fail(f"JSON do Whisper inválido: {exc}")

palavras_whisper = whisper_words(dados)
if not palavras_whisper:
    fail("Whisper não retornou palavras temporizadas")

inicio_total = palavras_whisper[0]["start"]
fim_total = palavras_whisper[-1]["end"]
if fim_total <= inicio_total:
    fail("linha do tempo do Whisper inválida")

try:
    palavras_timed, metodo, similarity = align_word_timings(
        palavras_originais,
        palavras_whisper,
        inicio_total,
        fim_total,
    )
except Exception as exc:
    fail(f"alinhamento de legenda falhou: {exc}")

if len(palavras_timed) != len(palavras_originais):
    fail("alinhamento perdeu palavras do roteiro")

print(f"Palavras detectadas pelo Whisper: {len(palavras_whisper)}")
print(f"Método: {metodo}")
print(f"Similaridade textual: {similarity:.3f}")

PALAVRAS_POR_GRUPO = 3
grupos = [
    palavras_timed[i:i + PALAVRAS_POR_GRUPO]
    for i in range(0, len(palavras_timed), PALAVRAS_POR_GRUPO)
]

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

print("3/4 Criando destaque dinâmico...")
eventos = []
for grupo in grupos:
    for indice, palavra in enumerate(grupo):
        inicio = palavra["start"]
        if indice + 1 < len(grupo):
            fim = grupo[indice + 1]["start"]
        else:
            fim = palavra["end"]
        fim = max(fim, inicio + 40)

        partes = []
        for j, outra in enumerate(grupo):
            texto = clean_ass_text(outra["text"])
            if j == indice:
                partes.append(
                    r"{\c&H00FFFF&\b1}" + texto + r"{\c&HFFFFFF&\b1}"
                )
            else:
                partes.append(texto)

        frase = " ".join(partes)
        eventos.append(
            "Dialogue: 0,"
            + ass_time(inicio)
            + ","
            + ass_time(fim)
            + ",Dynamic,,0,0,0,,"
            + frase
        )

if not eventos:
    fail("nenhum evento ASS foi gerado")

conteudo = cabecalho + "\n".join(eventos) + "\n"
tmp_ass = f"{ASS_FINAL}.{os.getpid()}.tmp"
try:
    with open(tmp_ass, "w", encoding="utf-8") as f:
        f.write(conteudo)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_ass, ASS_FINAL)
except Exception as exc:
    fail(f"não foi possível gravar legenda ASS: {exc}")
finally:
    try:
        if os.path.exists(tmp_ass):
            os.remove(tmp_ass)
    except OSError:
        pass
    try:
        if os.path.exists(WAV):
            os.remove(WAV)
    except OSError:
        pass

print("4/4 Finalizando...")
print()
print("================================")
print("LEGENDA DINÂMICA V3 CRIADA!")
print("================================")
print(f"Palavras do roteiro: {len(palavras_originais)}")
print(f"Eventos gerados: {len(eventos)}")
print(f"Alinhamento: {metodo} ({similarity:.3f})")
print(f"Arquivo: {ASS_FINAL}")
print()

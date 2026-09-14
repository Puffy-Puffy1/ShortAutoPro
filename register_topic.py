#!/usr/bin/env python3

import json
import os
from datetime import datetime

from topic_memory import normalizar

try:
    import fcntl
except ImportError:
    fcntl = None

BASE = os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))
SHORT_ID = os.getenv("SHORT_ID", "").strip()

if not SHORT_ID:
    raise SystemExit("ERRO: SHORT_ID ausente; assunto não será registrado.")

ROTEIROS = os.path.join(BASE, "roteiros")
USED_TOPIC = os.path.join(ROTEIROS, f"used_topic_{SHORT_ID}.txt")
TOPIC_FALLBACK = os.path.join(ROTEIROS, f"topic_{SHORT_ID}.txt")
HISTORICO = os.path.join(BASE, "historico_assuntos.json")
LOCK_PATH = HISTORICO + ".lock"

arquivo_topic = None
if os.path.isfile(USED_TOPIC):
    arquivo_topic = USED_TOPIC
elif os.path.isfile(TOPIC_FALLBACK):
    arquivo_topic = TOPIC_FALLBACK

if not arquivo_topic:
    raise SystemExit(
        "ERRO: arquivo do assunto não encontrado; histórico não foi alterado."
    )

try:
    with open(arquivo_topic, "r", encoding="utf-8") as f:
        topic = f.read().strip()
except Exception as exc:
    raise SystemExit(f"ERRO lendo assunto; histórico preservado: {exc}")

if not topic:
    raise SystemExit("ERRO: assunto vazio; histórico não foi alterado.")

topic_norm = normalizar(topic)
if not topic_norm:
    raise SystemExit("ERRO: assunto inválido após normalização.")

os.makedirs(BASE, exist_ok=True)

with open(LOCK_PATH, "a+", encoding="utf-8") as lock_file:
    if fcntl is not None:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

    dados = []
    if os.path.exists(HISTORICO):
        try:
            with open(HISTORICO, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception as exc:
            raise SystemExit(
                "ERRO: histórico de assuntos inválido; "
                f"arquivo preservado sem sobrescrever: {exc}"
            )

        if not isinstance(dados, list):
            raise SystemExit(
                "ERRO: histórico de assuntos não é uma lista; "
                "arquivo preservado sem sobrescrever."
            )

    for item in dados:
        if not isinstance(item, dict):
            continue
        existente = str(item.get("topic", "")).strip()
        if existente and normalizar(existente) == topic_norm:
            print(f"Assunto já estava registrado: {topic}")
            raise SystemExit(0)

    dados.append({
        "short_id": SHORT_ID,
        "topic": topic,
        "created_at": datetime.now().isoformat(),
    })

    temporario = f"{HISTORICO}.{os.getpid()}.tmp"
    try:
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, HISTORICO)
    finally:
        if os.path.exists(temporario):
            try:
                os.remove(temporario)
            except OSError:
                pass

print(f"Assunto registrado: {topic}")

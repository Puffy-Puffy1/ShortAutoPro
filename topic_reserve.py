#!/usr/bin/env python3

import glob
import json
import math
import os

from source_identity import validar_identidade
from topic_memory import encontrar_duplicata, normalizar

BASE = os.path.expanduser("~/ShortAutoPro")
ROTEIROS = os.path.join(BASE, "roteiros")
HISTORICO = os.path.join(BASE, "historico_assuntos.json")
INDEX = os.path.join(BASE, "topic_index.json")


def carregar_historico():
    if not os.path.exists(HISTORICO):
        return []
    try:
        with open(HISTORICO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return None
    return dados if isinstance(dados, list) else None


def score_seguro(valor):
    try:
        score = float(valor)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(score):
        return 0.0
    return score


def _chave(nome):
    return normalizar(nome) or str(nome).casefold().strip()


def _adicionar_melhor(candidatos, item):
    chave = _chave(item.get("topic", ""))
    if not chave:
        return
    atual = candidatos.get(chave)
    if atual is None or item["score"] > atual["score"]:
        candidatos[chave] = item


def carregar_do_indice():
    if not os.path.exists(INDEX):
        return []
    try:
        with open(INDEX, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return []
    if not isinstance(dados, dict):
        return []

    topics = dados.get("topics", [])
    if not isinstance(topics, list):
        return []

    historico = carregar_historico()
    if historico is None:
        return []

    candidatos = {}
    for item in topics:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("topic", "")).strip()
        wiki_title = str(item.get("wiki_title", "")).strip()
        if not nome or not wiki_title:
            continue

        duplicata = encontrar_duplicata(nome, historico, limite=0.72)
        if duplicata["duplicate"]:
            continue

        identidade = validar_identidade(nome, wiki_title)
        if not identidade["valid"]:
            continue

        _adicionar_melhor(
            candidatos,
            {
                "topic": nome,
                "wiki_title": wiki_title,
                "score": score_seguro(item.get("score", 0)),
                "source": "topic_index",
            },
        )

    saida = list(candidatos.values())
    saida.sort(key=lambda x: x["score"], reverse=True)
    return saida


def carregar_dos_verified():
    historico = carregar_historico()
    if historico is None:
        return []

    arquivos = glob.glob(
        os.path.join(ROTEIROS, "topic_verified_*.json")
    )
    candidatos = {}

    for arquivo in arquivos:
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            continue
        if not isinstance(dados, dict):
            continue

        ranking = dados.get("ranking") or dados.get("approved") or []
        if not isinstance(ranking, list):
            continue

        for item in ranking:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("topic", "")).strip()
            wiki_title = str(item.get("wiki_title", "")).strip()
            if not nome or not wiki_title:
                continue

            duplicata = encontrar_duplicata(nome, historico, limite=0.72)
            if duplicata["duplicate"]:
                continue

            identidade = validar_identidade(nome, wiki_title)
            if not identidade["valid"]:
                continue

            _adicionar_melhor(
                candidatos,
                {
                    "topic": nome,
                    "wiki_title": wiki_title,
                    "score": score_seguro(item.get("score", 0)),
                    "source": os.path.basename(arquivo),
                },
            )

    saida = list(candidatos.values())
    saida.sort(key=lambda x: x["score"], reverse=True)
    return saida


def carregar_reserva():
    candidatos = carregar_do_indice()
    if candidatos:
        return candidatos
    return carregar_dos_verified()


def melhor_reserva():
    candidatos = carregar_reserva()
    return candidatos[0] if candidatos else None


if __name__ == "__main__":
    candidatos = carregar_reserva()
    print()
    print("==============================")
    print("VERIFIED TOPIC RESERVE 2.2.8")
    print("==============================")
    print()
    if not candidatos:
        print("Nenhum tema de reserva disponível.")
        raise SystemExit(0)
    for numero, item in enumerate(candidatos[:20], start=1):
        print(f"{numero:02d}. {item['topic']}")
        print(f"    Wikipedia: {item['wiki_title']}")
        print(f"    score: {item['score']:.1f}")
        print(f"    origem: {item.get('source', '?')}")
        print()
    print("MELHOR RESERVA:")
    print(candidatos[0]["topic"])
    print()

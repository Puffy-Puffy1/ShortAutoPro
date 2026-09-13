#!/usr/bin/env python3

import json
import os
import re
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
OUTPUT = os.path.join(R, f"continuity_{SHORT_ID}.json")
BACKUP = os.path.join(R, f"scene_map_pre_continuity_{SHORT_ID}.json")

STOP = {
    "cinematic", "dramatic", "dark", "vintage", "historic", "historical",
    "view", "scene", "shot", "close", "medium", "wide", "old", "retro",
    "the", "a", "an", "of", "in", "on", "with", "and", "or", "to",
}


def atomic_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def tokens(texto):
    return {
        x
        for x in re.findall(r"[a-z0-9]+", str(texto).lower())
        if x not in STOP and len(x) >= 3
    }


def similaridade(a, b):
    ta = tokens(a)
    tb = tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def limpar_lista(valor):
    if not isinstance(valor, list):
        return []
    saida = []
    vistos = set()
    for x in valor:
        x = " ".join(str(x).split()).lower()
        if x and x not in vistos:
            vistos.add(x)
            saida.append(x)
    return saida


def limpar_query(query):
    return " ".join(str(query or "").split())


def adicionar_perspectiva(query, shot):
    query = limpar_query(query)
    if shot == "detail":
        sufixo = "detail view"
    elif shot == "close_up":
        sufixo = "close up"
    elif shot == "wide":
        sufixo = "wide establishing view"
    else:
        return query

    # Não injeta objetos, locais ou fatos novos. Só altera enquadramento.
    palavras = query.split()
    existentes = set(x.lower() for x in palavras)
    for palavra in sufixo.split():
        if palavra.lower() not in existentes:
            palavras.append(palavra)
            existentes.add(palavra.lower())

    # Impede que o guard faça a query crescer indefinidamente em reexecuções.
    return " ".join(palavras[:16])


if not os.path.isfile(SCENE_MAP):
    raise SystemExit("ERRO: scene_map não encontrado.")

try:
    with open(SCENE_MAP, "r", encoding="utf-8") as f:
        mapa = json.load(f)
except Exception as exc:
    raise SystemExit(f"ERRO lendo scene_map: {exc}")

if not isinstance(mapa, dict):
    raise SystemExit("ERRO: scene_map não é objeto JSON.")
cenas = mapa.get("scenes", [])
if not isinstance(cenas, list) or not all(isinstance(x, dict) for x in cenas):
    raise SystemExit("ERRO: scene_map sem lista válida de cenas.")
if len(cenas) != QTD_CENAS:
    raise SystemExit(
        f"ERRO: esperado {QTD_CENAS} cenas; encontrado {len(cenas)}."
    )

for esperado, cena in enumerate(cenas, start=1):
    try:
        numero = int(cena.get("scene"))
    except (TypeError, ValueError):
        raise SystemExit(f"ERRO: cena {esperado} sem número válido.")
    if numero != esperado:
        raise SystemExit("ERRO: numeração de cenas fora de sequência.")

atomic_json(BACKUP, mapa)
mudancas = []

for i in range(1, len(cenas)):
    anterior = cenas[i - 1]
    atual = cenas[i]
    query_ant = limpar_query(anterior.get("query", ""))
    query_atual = limpar_query(atual.get("query", ""))

    sim = similaridade(query_ant, query_atual)
    if sim < 0.45:
        continue

    shot_ant = str(anterior.get("shot_type", "")).lower()
    shot_atual = str(atual.get("shot_type", "")).lower()
    novo_shot = shot_atual

    if shot_ant == shot_atual:
        if shot_atual in {"wide", "exterior", "aerial"}:
            novo_shot = "detail"
        elif shot_atual in {"detail", "close_up"}:
            novo_shot = "wide"
        else:
            novo_shot = "close_up"

    # Se o enquadramento já é diferente, não mexe na query: a diversidade
    # existente já cumpre o objetivo sem risco de degradar a semântica.
    novo_query = query_atual
    if novo_shot != shot_atual:
        novo_query = adicionar_perspectiva(query_atual, novo_shot)

    must_ant = limpar_lista(anterior.get("must_have", []))
    must_atual = limpar_lista(atual.get("must_have", []))
    comuns = set(must_ant) & set(must_atual)

    mudancas.append({
        "scene": atual.get("scene"),
        "similarity": round(sim, 3),
        "before": query_atual,
        "after": novo_query,
        "shot_before": shot_atual,
        "shot_after": novo_shot,
        "shared_must": sorted(comuns),
    })

    atual["query"] = novo_query
    atual["shot_type"] = novo_shot

mapa["editorial_continuity"] = {
    "version": "4.5",
    "changes": len(mudancas),
    "expected_scenes": QTD_CENAS,
}

atomic_json(SCENE_MAP, mapa)
atomic_json(OUTPUT, {
    "short_id": SHORT_ID,
    "version": "4.5",
    "changes": mudancas,
})

print()
print("================================")
print("EDITORIAL CONTINUITY GUARD 4.5")
print("================================")
print(f"Cenas analisadas: {len(cenas)}/{QTD_CENAS}")
print(f"Repetições ajustadas: {len(mudancas)}")
print("EDITORIAL CONTINUITY: OK")
print()

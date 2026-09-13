#!/usr/bin/env python3

import json
import os
import re
import sys
import time
from datetime import date

import requests

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
ROTEIRO = os.path.join(BASE, "roteiros", f"short_{SHORT_ID}.txt")
KEYWORDS = os.path.join(BASE, "roteiros", f"keywords_{SHORT_ID}.txt")
MAPA = os.path.join(BASE, "roteiros", f"scene_map_{SHORT_ID}.json")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

if not GEMINI_KEY:
    sys.exit("ERRO: GEMINI_API_KEY não configurada.")
if not os.path.isfile(ROTEIRO):
    sys.exit(f"ERRO: roteiro não encontrado: {ROTEIRO}")

try:
    with open(ROTEIRO, "r", encoding="utf-8") as f:
        roteiro = f.read().strip()
except Exception as exc:
    sys.exit(f"ERRO lendo roteiro: {exc}")

if not roteiro:
    sys.exit("ERRO: roteiro vazio.")


def extrair_palavras(texto):
    return re.findall(r"\b[\wÀ-ÿ'-]+\b", str(texto), flags=re.UNICODE)


def atomic_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(text))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


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


total_palavras = len(extrair_palavras(roteiro))
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
HEADERS = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY}


def chamar_gemini(prompt):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 2400},
    }
    for tentativa in range(1, 5):
        print(f"Scene Director tentativa {tentativa}/4...")
        try:
            r = requests.post(URL, headers=HEADERS, json=payload, timeout=120)
        except Exception as exc:
            if tentativa == 4:
                raise RuntimeError(str(exc))
            time.sleep(5)
            continue

        if r.ok:
            try:
                dados = r.json()
                texto = dados["candidates"][0]["content"]["parts"][0]["text"]
                texto = str(texto).strip()
                if not texto:
                    raise ValueError("texto vazio")
                return texto
            except Exception as exc:
                raise RuntimeError(f"Gemini retornou resposta inválida: {exc}")

        if r.status_code in {429, 500, 502, 503, 504} and tentativa < 4:
            time.sleep(8)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:1200]}")
    raise RuntimeError("Gemini não respondeu.")


prompt = f"""
Você é um diretor profissional de edição visual.

ROTEIRO FINAL:
========================
{roteiro}
========================

Divida o roteiro em EXATAMENTE {QTD_CENAS} segmentos semânticos consecutivos.
Para cada cena gere:
- segment: trecho correspondente do roteiro em português;
- query: busca visual em inglês, 4 a 9 palavras;
- must_have: 1 a 3 termos concretos essenciais;
- avoid: 0 a 5 termos que indicam mídia inadequada.

REGRAS:
- preserve a ordem original;
- não invente fatos nem altere a narrativa;
- segment deve usar somente conteúdo do roteiro;
- query deve ser concretamente visível;
- não represente CTA com celular, like, subscribe ou comentário;
- a última cena fecha visualmente a história.

RESPONDA SOMENTE JSON VÁLIDO:
{{"scenes":[{{"segment":"trecho","query":"visual search","must_have":["term"],"avoid":["term"]}}]}}
O array deve conter EXATAMENTE {QTD_CENAS} itens.
"""

print()
print("================================")
print("SCENE DIRECTOR V6.7")
print("================================")
print(f"ID: {SHORT_ID}")
print(f"Palavras: {total_palavras}")
print(f"Cenas: {QTD_CENAS}")
print()

try:
    bruto = chamar_gemini(prompt)
except Exception as exc:
    sys.exit(f"ERRO Scene Director: {exc}")

bruto = bruto.replace("```json", "").replace("```", "").strip()
try:
    dados = json.loads(bruto)
except Exception:
    print("Resposta recebida:")
    print(bruto)
    sys.exit("ERRO: JSON inválido.")

if not isinstance(dados, dict):
    sys.exit("ERRO: resposta do Scene Director não é um objeto JSON.")
scenes = dados.get("scenes", [])
if not isinstance(scenes, list):
    sys.exit("ERRO: campo scenes não é uma lista.")
scenes = [item for item in scenes if isinstance(item, dict)]
if not scenes:
    sys.exit("ERRO: Gemini não retornou nenhuma cena utilizável.")

scene_count_original = len(scenes)
recovery_actions = []


def clean_list(value, limit):
    if not isinstance(value, list):
        return []
    saida = []
    vistos = set()
    for x in value:
        x = str(x).strip()
        key = x.casefold()
        if x and key not in vistos:
            vistos.add(key)
            saida.append(x)
    return saida[:limit]


def split_scene(item):
    palavras = extrair_palavras(item.get("segment", ""))
    if len(palavras) < 4:
        return None
    meio = max(2, len(palavras) // 2)
    esquerda = " ".join(palavras[:meio]).strip()
    direita = " ".join(palavras[meio:]).strip()
    if not esquerda or not direita:
        return None

    comum = {
        k: v
        for k, v in item.items()
        if k not in {"segment", "scene", "words", "weight"}
    }
    a = dict(comum)
    b = dict(comum)
    a["segment"] = esquerda
    b["segment"] = direita
    a["query"] = str(item.get("query", "")).strip() or "documentary detail scene"
    b["query"] = a["query"]
    a["must_have"] = clean_list(item.get("must_have", []), 3)
    b["must_have"] = list(a["must_have"])
    a["avoid"] = clean_list(item.get("avoid", []), 5)
    b["avoid"] = list(a["avoid"])
    a["recovery_6_7"] = "split_left"
    b["recovery_6_7"] = "split_right"
    return a, b


def merge_pair(a, b):
    segmento = (
        str(a.get("segment", "")).strip()
        + " "
        + str(b.get("segment", "")).strip()
    ).strip()
    query = (
        str(a.get("query", "")).strip()
        or str(b.get("query", "")).strip()
        or "documentary scene"
    )
    must = clean_list(
        (a.get("must_have", []) if isinstance(a.get("must_have"), list) else [])
        + (b.get("must_have", []) if isinstance(b.get("must_have"), list) else []),
        3,
    )
    avoid = clean_list(
        (a.get("avoid", []) if isinstance(a.get("avoid"), list) else [])
        + (b.get("avoid", []) if isinstance(b.get("avoid"), list) else []),
        5,
    )
    merged = dict(a)
    merged.update({
        "segment": segmento,
        "query": query,
        "must_have": must,
        "avoid": avoid,
        "recovery_6_7": "merged_adjacent",
    })
    return merged


while len(scenes) < QTD_CENAS:
    candidatos = sorted(
        range(len(scenes)),
        key=lambda i: len(extrair_palavras(scenes[i].get("segment", ""))),
        reverse=True,
    )
    recuperou = False
    for indice in candidatos:
        dividido = split_scene(scenes[indice])
        if not dividido:
            continue
        scenes[indice:indice + 1] = list(dividido)
        recovery_actions.append({"action": "split", "index": indice + 1})
        recuperou = True
        break
    if not recuperou:
        sys.exit(
            f"ERRO: não foi possível completar {QTD_CENAS} cenas sem inventar texto."
        )

while len(scenes) > QTD_CENAS:
    melhor_indice = None
    melhor_tamanho = None
    for i in range(len(scenes) - 1):
        tamanho = (
            len(extrair_palavras(scenes[i].get("segment", "")))
            + len(extrair_palavras(scenes[i + 1].get("segment", "")))
        )
        if melhor_tamanho is None or tamanho < melhor_tamanho:
            melhor_tamanho = tamanho
            melhor_indice = i
    if melhor_indice is None:
        sys.exit("ERRO: não foi possível consolidar cenas excedentes.")
    merged = merge_pair(scenes[melhor_indice], scenes[melhor_indice + 1])
    scenes[melhor_indice:melhor_indice + 2] = [merged]
    recovery_actions.append({"action": "merge", "index": melhor_indice + 1})

if len(scenes) != QTD_CENAS:
    sys.exit(f"ERRO: Scene Director terminou com {len(scenes)} cenas.")

resultado = []
soma_pesos = 0

for numero, item in enumerate(scenes, start=1):
    trecho = str(item.get("segment", "")).strip()
    busca = str(item.get("query", "")).strip().lstrip("[").rstrip("]").strip()
    must_have = clean_list(item.get("must_have", []), 3)
    avoid = clean_list(item.get("avoid", []), 5)

    if not trecho:
        sys.exit(f"ERRO: cena {numero} sem segmento.")
    if not busca:
        sys.exit(f"ERRO: cena {numero} sem busca.")

    qtd = max(1, len(extrair_palavras(trecho)))
    soma_pesos += qtd
    resultado.append({
        "scene": numero,
        "segment": trecho,
        "query": busca,
        "must_have": [x.lower() for x in must_have],
        "avoid": [x.lower() for x in avoid],
        "words": qtd,
    })

if soma_pesos <= 0:
    sys.exit("ERRO: Scene Director gerou peso total inválido.")

for item in resultado:
    item["weight"] = item["words"] / soma_pesos

saida = {
    "short_id": SHORT_ID,
    "total_script_words": total_palavras,
    "mapped_words": soma_pesos,
    "scene_count": QTD_CENAS,
    "scene_count_original": scene_count_original,
    "scene_recovery_6_7": recovery_actions,
    "scene_director_version": "6.7",
    "scenes": resultado,
}

atomic_json(MAPA, saida)
atomic_text(KEYWORDS, "\n".join(item["query"] for item in resultado) + "\n")

print()
print("================================")
print("VISUAL RELEVANCE MAP CRIADO!")
print("================================")
print(f"SCENE COUNT ORIGINAL: {scene_count_original}")
print(f"RECOVERY ACTIONS: {len(recovery_actions)}")
print(f"SCENE COUNT FINAL: {len(resultado)}/{QTD_CENAS}")
print(f"Mapa: {MAPA}")
print()

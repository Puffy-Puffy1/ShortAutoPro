#!/usr/bin/env python3

import json
import os
import re
import sys
import time
from datetime import date

from scene_must_policy import normalize_visual_musts

from gemini_runtime import generate_text

BASE = os.path.abspath(
    os.path.expanduser(
        os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")
    )
)
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


def chamar_gemini(prompt):
    return generate_text(
        prompt,
        temperature=0.15,
        max_output_tokens=2400,
        response_mime_type="application/json",
        component="Scene Director",
        api_key=GEMINI_KEY,
    )


def fallback_local_scenes(texto, quantidade):
    palavras = extrair_palavras(texto)
    if not palavras:
        return []

    quantidade = max(1, min(int(quantidade), len(palavras)))
    base = len(palavras) // quantidade
    resto = len(palavras) % quantidade
    cenas = []
    cursor = 0

    for indice in range(quantidade):
        tamanho = base + (1 if indice < resto else 0)
        trecho_palavras = palavras[cursor:cursor + tamanho]
        cursor += tamanho
        trecho = " ".join(trecho_palavras).strip()

        # The local fallback is deliberately conservative: it preserves the
        # narration exactly and uses a generic documentary query. Later visual
        # directors can enrich the query when AI is available.
        cenas.append(
            {
                "segment": trecho,
                "query": "documentary visual context scene",
                "must_have": [],
                "avoid": ["wrong person", "unrelated event"],
                "fallback_local": True,
                "must_policy": "NONE_LOCAL_FALLBACK",
            }
        )

    return cenas


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
- must_have: 1 a 2 âncoras visuais concretas e simples, somente quando realmente essenciais;
- avoid: 0 a 5 termos que indicam mídia inadequada.

REGRAS DE RECUPERAÇÃO DE MÍDIA:
- prefira substantivos visíveis e pesquisáveis, como "paper", "document", "tent", "person", "car" ou "mountain";
- evite MUSTs compostos ou relacionais como "trousers pocket", "aged paper" e "dark fabric" quando um substantivo visual simples representar a cena;
- não transforme cor, material, época, posição, estado emocional ou relação espacial em MUST separado, salvo se for o fato visual central da cena;
- query pode descrever a composição completa, mas MUST deve servir como âncora verificável nos metadados reais de uma imagem;
- se não houver objeto concreto essencial, use must_have vazio em vez de inventar uma exigência difícil de comprovar;
- NÃO use qualificadores como cor, luminosidade, época ou tipo técnico como parte obrigatória de um MUST; prefira o objeto verificável: "aircraft" em vez de "single engine aircraft", "horizon" em vez de "dark horizon";
- a política determinística pode normalizar apenas qualificadores visuais não essenciais conhecidos; a mídia continua obrigada a comprovar cada âncora resultante nos metadados reais;
- nunca relaxe um MUST na etapa de validação só para aceitar uma imagem sem evidência.

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

scenes = []
try:
    bruto = chamar_gemini(prompt)
    bruto = bruto.replace("```json", "").replace("```", "").strip()
    dados = json.loads(bruto)
    if isinstance(dados, dict) and isinstance(dados.get("scenes"), list):
        scenes = [item for item in dados.get("scenes", []) if isinstance(item, dict)]
except Exception as exc:
    print(
        "SCENE_DIRECTOR_AI=FAIL_OPEN "
        f"{type(exc).__name__}:{str(exc)[:180]}"
    )

if not scenes:
    print(
        "SCENE_DIRECTOR_FALLBACK=LOCAL_SEMANTIC_SPLIT "
        f"target={QTD_CENAS}"
    )
    scenes = fallback_local_scenes(roteiro, QTD_CENAS)

if not scenes:
    sys.exit("ERRO: Scene Director não conseguiu criar cenas locais.")

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
    must_raw = clean_list(item.get("must_have", []), 3)
    must_have, must_normalizations = normalize_visual_musts(must_raw)
    if must_normalizations:
        recovery_actions.extend({"action": "normalize_visual_must", "scene": numero, **event} for event in must_normalizations)
        print(f"SCENE_MUST_NORMALIZED scene={numero} count={len(must_normalizations)}")
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

#!/usr/bin/env python3

import json
import os
import re
import unicodedata
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())

try:
    QTD_CENAS = int(os.getenv("SHORT_QTD_CENAS", "12"))
except ValueError:
    QTD_CENAS = 12
QTD_CENAS = max(6, min(QTD_CENAS, 20))

R = os.path.join(BASE, "roteiros")
SCRIPT = os.path.join(R, f"short_{SHORT_ID}.txt")
SCENE_MAP = os.path.join(R, f"scene_map_{SHORT_ID}.json")
BACKUP = os.path.join(R, f"scene_map_pre_lossless_{SHORT_ID}.json")
REPORT = os.path.join(R, f"scene_lossless_{SHORT_ID}.json")

STOP = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "de", "da", "do", "das", "dos", "e", "ou", "em", "no", "na",
    "nos", "nas", "por", "para", "com", "sem", "que", "se",
    "ao", "aos", "à", "às", "foi", "era", "ser", "são",
    "como", "mais", "mas", "the", "of", "and", "in", "on", "at",
    "to", "for", "from", "with",
}


def _atomic_json(path, data):
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


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def sem_acento(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenizar(text, remove_stop=True):
    toks = re.findall(r"[a-z0-9]+", sem_acento(text).lower())
    if remove_stop:
        toks = [x for x in toks if len(x) >= 2 and x not in STOP]
    return toks


def token_set(text):
    return set(tokenizar(text))


def coverage(script, scenes_text):
    script_tokens = token_set(script)
    scene_tokens = token_set(scenes_text)
    if not script_tokens:
        return 1.0, set()
    missing = script_tokens - scene_tokens
    ratio = len(script_tokens & scene_tokens) / len(script_tokens)
    return ratio, missing


def split_sentences(value):
    text = str(value or "").strip()
    if not text:
        return []
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text)
        if part.strip()
    ]


def merge_source(current, source):
    current = str(current or "").strip()
    source = str(source or "").strip()
    if not source:
        return current
    if not current:
        return source

    source_tokens = token_set(source)
    current_tokens = token_set(current)
    if not source_tokens or source_tokens <= current_tokens:
        return current

    sentences = split_sentences(current)
    for index, sentence in enumerate(sentences):
        sentence_tokens = token_set(sentence)
        if not sentence_tokens:
            continue
        if sentence_tokens < source_tokens:
            overlap_ratio = len(sentence_tokens) / max(1, len(source_tokens))
            if overlap_ratio >= 0.60:
                sentences[index] = source
                return " ".join(sentences).strip()

    return f"{current} {source}".strip()


def word_count(value):
    return len(str(value or "").split())


def sentence_chunks(script):
    partes = split_sentences(script)
    if len(partes) < 6:
        palavras = script.split()
        alvo = max(8, round(len(palavras) / QTD_CENAS))
        partes = [
            " ".join(palavras[i:i + alvo]).strip()
            for i in range(0, len(palavras), alvo)
        ]
        partes = [x for x in partes if x]
    return partes


def scene_context(scene):
    partes = [
        str(scene.get("segment", "")),
        str(scene.get("query", "")),
        str(scene.get("visual_mode", "")),
    ]
    must = scene.get("must_have", [])
    if isinstance(must, list):
        partes.extend(str(x) for x in must)
    return " ".join(partes)


def afinidade(trecho, scene, scene_index, total_scenes, chunk_index, total_chunks):
    tt = token_set(trecho)
    st = token_set(scene_context(scene))
    overlap = len(tt & st) / max(1, len(tt))
    pos_scene = scene_index / max(1, total_scenes - 1)
    pos_chunk = chunk_index / max(1, total_chunks - 1)
    positional = 1.0 - min(1.0, abs(pos_scene - pos_chunk))
    return overlap * 0.78 + positional * 0.22


script = read(SCRIPT)
if not script:
    raise SystemExit(f"ERRO: roteiro ausente: {SCRIPT}")

mapa = read_json(SCENE_MAP)
scenes = mapa.get("scenes", []) if isinstance(mapa, dict) else []
if not isinstance(scenes, list):
    scenes = []
if len(scenes) != QTD_CENAS or not all(isinstance(x, dict) for x in scenes):
    raise SystemExit(
        f"ERRO: esperado {QTD_CENAS} cenas válidas, encontrado {len(scenes)}."
    )

original_text = "\n".join(str(x.get("segment", "")) for x in scenes)
before, missing_before = coverage(script, original_text)

print()
print("======================================")
print(" LOSSLESS SCENE COVERAGE REPAIR 6.3")
print("======================================")
print()
print("SHORT_ID:", SHORT_ID)
print("Cobertura inicial:", f"{before * 100:.1f}%")
print("Tokens ausentes:", len(missing_before))

if before >= 0.965:
    report = {
        "short_id": SHORT_ID,
        "version": "6.3",
        "coverage_before": round(before, 4),
        "coverage_after": round(before, 4),
        "changed_scenes": [],
        "missing_before": sorted(missing_before),
        "missing_after": sorted(missing_before),
        "status": "NO_REPAIR_NEEDED",
    }
    _atomic_json(REPORT, report)
    print()
    print("LOSSLESS REPAIR: NÃO NECESSÁRIO")
    print("Mapa original preservado.")
    raise SystemExit(0)

_atomic_json(BACKUP, mapa)
chunks = sentence_chunks(script)
changed = []

for chunk_index, trecho in enumerate(chunks):
    chunk_tokens = token_set(trecho)
    relevantes = chunk_tokens & missing_before
    if not relevantes:
        continue

    scores = [
        (
            afinidade(
                trecho,
                scene,
                scene_index,
                len(scenes),
                chunk_index,
                len(chunks),
            ),
            scene_index,
        )
        for scene_index, scene in enumerate(scenes)
    ]
    scores.sort(reverse=True)
    melhor_score, destino = scores[0]
    atual = str(scenes[destino].get("segment", "")).strip()

    if token_set(trecho) <= token_set(atual):
        continue

    novo_segmento = merge_source(atual, trecho)
    scenes[destino]["segment"] = novo_segmento
    scenes[destino]["lossless_repair_6_2"] = True
    scenes[destino].setdefault("lossless_sources_6_2", []).append(trecho)
    changed.append({
        "scene": destino + 1,
        "affinity": round(melhor_score, 3),
        "missing_tokens": sorted(relevantes),
        "source_text": trecho,
        "method": "source_chunk",
    })

final_text = "\n".join(str(x.get("segment", "")) for x in scenes)
after, missing_after = coverage(script, final_text)

if after < before:
    raise SystemExit(
        "ERRO: reparo reduziu cobertura; scene_map original preservado no backup."
    )

if after < 0.965:
    print()
    print("AVISO: primeira passagem não atingiu 96.5%.")
    print("Aplicando recuperação literal final.")

    palavras = script.split()
    for pos, palavra in enumerate(palavras):
        token_palavra = token_set(palavra)
        if not (token_palavra & missing_after):
            continue

        destino = min(
            QTD_CENAS - 1,
            int((pos / max(1, len(palavras))) * QTD_CENAS),
        )
        atual = str(scenes[destino].get("segment", "")).strip()
        scenes[destino]["segment"] = f"{atual} {palavra}".strip()
        scenes[destino]["lossless_repair_6_2"] = True
        changed.append({
            "scene": destino + 1,
            "affinity": None,
            "missing_tokens": sorted(token_palavra & missing_after),
            "source_text": palavra,
            "method": "literal_fallback",
        })

    final_text = "\n".join(str(x.get("segment", "")) for x in scenes)
    after, missing_after = coverage(script, final_text)

for scene in scenes:
    if scene.get("lossless_repair_6_2"):
        scene["words"] = word_count(scene.get("segment", ""))

mapa["scenes"] = scenes
mapa["lossless_scene_coverage_6_2"] = {
    "version": "6.3",
    "coverage_before": round(before, 4),
    "coverage_after": round(after, 4),
    "changed_scenes": sorted({x["scene"] for x in changed}),
}

_atomic_json(SCENE_MAP, mapa)
report = {
    "short_id": SHORT_ID,
    "version": "6.3",
    "coverage_before": round(before, 4),
    "coverage_after": round(after, 4),
    "changed_scenes": changed,
    "missing_before": sorted(missing_before),
    "missing_after": sorted(missing_after),
    "backup": BACKUP,
    "status": "PASS" if after >= 0.965 else "WARNING",
}
_atomic_json(REPORT, report)

print()
print("Cobertura final:", f"{after * 100:.1f}%")
print("Cenas ajustadas:", sorted({x["scene"] for x in changed}))
print("Tokens ainda ausentes:", sorted(missing_after))
print()
print("Backup:", BACKUP)
print("Relatório:", REPORT)

if after < 0.965:
    print()
    print("LOSSLESS REPAIR: WARNING")
    raise SystemExit(1)

print()
print("LOSSLESS REPAIR: PASS")

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
MAPA = os.path.join(R, f"scene_map_{SHORT_ID}.json")
BACKUP = os.path.join(R, f"scene_map_pre_truth_refiner_{SHORT_ID}.json")
REPORT = os.path.join(R, f"scene_truth_refiner_{SHORT_ID}.json")


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


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


def clean_list(valores, limite=6):
    if not isinstance(valores, list):
        return []
    saida = []
    vistos = set()
    for x in valores:
        x = str(x).strip().lower()
        key = x.casefold()
        if x and key not in vistos:
            vistos.add(key)
            saida.append(x)
    return saida[:limite]


def add_avoid(cena, *termos):
    atual = clean_list(cena.get("avoid", []), 12)
    for termo in termos:
        termo = str(termo).strip().lower()
        if termo and termo not in atual:
            atual.append(termo)
    cena["avoid"] = atual[:12]


def set_visual(cena, query, must, mode, intent, reason):
    cena["query"] = str(query).strip()
    cena["must_have"] = clean_list(list(must), 3)
    cena["visual_mode"] = mode
    cena["visual_intent_6_7"] = intent
    cena["truth_refiner_6_7"] = reason


if not os.path.isfile(MAPA):
    raise SystemExit(f"ERRO: scene_map ausente: {MAPA}")

try:
    with open(MAPA, "r", encoding="utf-8") as f:
        mapa = json.load(f)
except Exception as exc:
    raise SystemExit(f"ERRO lendo scene_map: {exc}")

if not isinstance(mapa, dict):
    raise SystemExit("ERRO: scene_map não é objeto JSON.")

cenas = mapa.get("scenes", [])
if not isinstance(cenas, list):
    raise SystemExit("ERRO: campo scenes inválido.")
if len(cenas) != QTD_CENAS or not all(isinstance(x, dict) for x in cenas):
    raise SystemExit(
        f"ERRO: esperado {QTD_CENAS} cenas válidas; encontrado {len(cenas)}."
    )

# Garante sequência coerente antes de alterar o mapa.
for esperado, cena in enumerate(cenas, start=1):
    try:
        numero = int(cena.get("scene"))
    except (TypeError, ValueError):
        raise SystemExit(f"ERRO: cena {esperado} sem numeração válida.")
    if numero != esperado:
        raise SystemExit(
            f"ERRO: numeração de cenas inconsistente: esperado {esperado}, recebido {numero}."
        )

atomic_json(BACKUP, mapa)
alteracoes = []

for numero, cena in enumerate(cenas, start=1):
    segmento = str(cena.get("segment", "")).strip()
    seg = normalizar(segmento)
    original = {
        "query": cena.get("query"),
        "must_have": cena.get("must_have"),
        "visual_mode": cena.get("visual_mode"),
    }

    # Regras factuais específicas só são acionadas quando o próprio
    # segmento contém os identificadores correspondentes. Fora desses
    # casos, o módulo preserva integralmente a direção recebida.
    if "mary kellerman" in seg or ("primeira vitima" in seg and "anos" in seg):
        set_visual(
            cena,
            "1980s Tylenol medicine bottle capsules archival newspaper context",
            ["medicine bottle", "capsules"],
            "evidence",
            "EVIDENCE",
            "named_minor_no_generic_portrait",
        )
        add_avoid(
            cena,
            "generic child portrait", "young girl portrait", "random child",
            "reenactment", "actor",
        )

    elif "familia janus" in seg:
        set_visual(
            cena,
            "1982 Chicago Tylenol poisoning newspaper archive medicine bottles",
            ["newspaper", "medicine"],
            "document",
            "DOCUMENT",
            "named_family_no_generic_family",
        )
        add_avoid(cena, "generic family", "sad family", "random people", "reenactment", "actors")

    elif "culpado" in seg and (
        "jamais" in seg or "nunca" in seg or "nao foi encontrado" in seg
    ):
        set_visual(
            cena,
            "unsolved investigation case files police documents newspaper archive",
            ["case files", "documents"],
            "document",
            "EVIDENCE",
            "unsolved_case_no_fictional_suspect",
        )
        add_avoid(
            cena,
            "mysterious man", "shadow person", "dark alley suspect", "hooded man",
            "criminal portrait",
        )

    elif "johnson" in seg and "recall" in seg:
        set_visual(
            cena,
            "1982 Tylenol recall medicine bottles pharmacy newspaper archive",
            ["medicine bottles", "pharmacy"],
            "document",
            "EVENT",
            "historical_recall_context",
        )
        add_avoid(cena, "generic warehouse only", "modern ecommerce warehouse")

    elif "seguranca" in seg and "industria farmaceutica" in seg:
        set_visual(
            cena,
            "tamper resistant medicine packaging sealed pharmaceutical bottle close up",
            ["medicine packaging", "safety seal"],
            "evidence",
            "EVIDENCE",
            "industry_change_visualized_by_packaging",
        )
        add_avoid(cena, "generic laboratory scientist", "medical experiment")

    elif "embalagens lacradas" in seg or "lacre" in seg:
        set_visual(
            cena,
            "tamper evident medicine bottle safety seal packaging close up",
            ["medicine bottle", "safety seal"],
            "evidence",
            "EVIDENCE",
            "direct_visual_consequence",
        )

    elif "comente" in seg or "siga" in seg or "mais historias reais" in seg:
        cena["visual_intent_6_7"] = "CTA"
        cena["visual_mode"] = "cta_reuse"
        cena["truth_refiner_6_7"] = "reuse_verified_story_visual"
        cena["cta_reuse_6_7"] = True
        add_avoid(cena, "social media icon", "thumbs up", "generic influencer", "random person")

    elif "qual remedio" in seg or "tem em casa" in seg:
        set_visual(
            cena,
            "sealed medicine bottles home medicine cabinet close up",
            ["medicine bottles", "cabinet"],
            "object",
            "CTA",
            "question_visual_without_identity_claim",
        )

    elif "cianeto" in seg and "chicago" in seg:
        set_visual(
            cena,
            "1982 medicine capsules Tylenol bottle archival evidence",
            ["capsules", "medicine bottle"],
            "evidence",
            "EVIDENCE",
            "remove_conflicting_table_street_concepts",
        )

    novo = {
        "query": cena.get("query"),
        "must_have": cena.get("must_have"),
        "visual_mode": cena.get("visual_mode"),
    }
    if novo != original:
        alteracoes.append({
            "scene": numero,
            "segment": segmento,
            "before": original,
            "after": novo,
            "reason": cena.get("truth_refiner_6_7"),
        })

mapa["scenes"] = cenas
mapa["scene_truth_refiner_6_7"] = {
    "changed": len(alteracoes),
    "version": "6.7.1",
    "expected_scenes": QTD_CENAS,
}

atomic_json(MAPA, mapa)
atomic_json(REPORT, {
    "short_id": SHORT_ID,
    "version": "6.7.1",
    "changed": len(alteracoes),
    "changes": alteracoes,
    "backup": BACKUP,
})

print()
print("======================================")
print(" SCENE TRUTH REFINER 6.7.1")
print("======================================")
print(f"Cenas: {len(cenas)}/{QTD_CENAS}")
print(f"Ajustadas: {len(alteracoes)}")
print(f"Mapa: {MAPA}")
print(f"Relatório: {REPORT}")
print("SCENE TRUTH REFINER: PASS")

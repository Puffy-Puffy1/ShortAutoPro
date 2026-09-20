#!/usr/bin/env python3

import json
import os
import re
import sys
from datetime import date


BASE = os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
SCENE_MAP = os.path.join(BASE, "roteiros", f"scene_map_{SHORT_ID}.json")
REPORT = os.path.join(BASE, "roteiros", f"visual_risk_{SHORT_ID}.json")



def atomic_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


RISCOS = {
    "ufo": "mysterious unidentified light",
    "flying saucer": "unidentified distant light",
    "alien spacecraft": "mysterious light in distance",
    "alien": "unidentified distant figure",
    "extraterrestrial": "unexplained distant light",
    "ghost": "shadowy silhouette",
    "paranormal entity": "unexplained shadow",
    "spirit": "shadowy atmosphere",
    "dead body": "covered stretcher",
    "corpse": "forensic scene context",
    "blood": "crime scene evidence",
    "bloody": "forensic scene",
    "murder scene": "police investigation scene",
}

TERMOS_ALEGACAO = [
    "alleged", "claimed", "reported", "reportedly", "theory", "theories",
    "speculation", "speculated", "mysterious", "unexplained", "unknown",
    "possible", "possibly", "alegou", "alegação", "alegacoes", "alegações",
    "relatou", "relato", "teoria", "teorias", "especulação", "especulacao",
    "mistério", "misterio", "inexplicável", "inexplicavel", "desconhecido",
]

PARANORMAL_SEMPRE = {
    "ufo", "flying saucer", "alien spacecraft", "alien", "extraterrestrial",
    "ghost", "paranormal entity", "spirit",
}

AVOID_INCERTO = [
    "detailed alien spacecraft",
    "flying saucer",
    "visible ghost",
    "alien creature",
]


def normalizar(texto):
    return " ".join(str(texto or "").replace("\n", " ").split())


def _padrao_termo(termo):
    """Casa termos completos e evita substring: 'alien' não casa 'Australian'."""
    return re.compile(
        r"(?<![a-z0-9])" + re.escape(str(termo)) + r"(?![a-z0-9])",
        flags=re.IGNORECASE,
    )


def contem_termo(texto, termo):
    return _padrao_termo(termo).search(normalizar(texto)) is not None


def substituir_termo(texto, termo, substituto):
    return _padrao_termo(termo).sub(str(substituto), normalizar(texto))


def tem_contexto_incerto(segmento):
    texto = normalizar(segmento)
    return any(contem_termo(texto, termo) for termo in TERMOS_ALEGACAO)


def remover_duplicatas(lista):
    saida = []
    for item in lista:
        item_n = normalizar(item).lower()
        if item_n and item_n not in saida:
            saida.append(item_n)
    return saida


def processar_mapa(mapa):
    if not isinstance(mapa, dict):
        raise ValueError("scene_map deve ser um objeto JSON")

    cenas = mapa.get("scenes", [])
    if not isinstance(cenas, list):
        raise ValueError("scenes inválido")

    mudancas = []

    for cena in cenas:
        if not isinstance(cena, dict):
            raise ValueError("cena inválida: esperado objeto")

        numero = cena.get("scene")
        segmento = normalizar(cena.get("segment", ""))
        query_original = normalizar(cena.get("query", ""))
        query = query_original
        must = [normalizar(x).lower() for x in (cena.get("must_have", []) or [])]
        avoid = [normalizar(x).lower() for x in (cena.get("avoid", []) or [])]
        contexto_incerto = tem_contexto_incerto(segmento)
        alterada = False
        motivos = []

        for termo, substituto in RISCOS.items():
            if not contem_termo(query, termo):
                continue
            if contexto_incerto or termo in PARANORMAL_SEMPRE:
                query = substituir_termo(query, termo, substituto)
                motivos.append(f"query:{termo}")
                alterada = True

        must_novo = []
        for item in must:
            novo_item = item
            for termo, substituto in RISCOS.items():
                if not contem_termo(novo_item, termo):
                    continue
                if contexto_incerto or termo in PARANORMAL_SEMPRE:
                    novo_item = substituto
                    motivos.append(f"must:{termo}")
                    alterada = True
            must_novo.append(novo_item)

        if contexto_incerto:
            for item in AVOID_INCERTO:
                if item not in avoid:
                    avoid.append(item)

        cena["query"] = normalizar(query)
        cena["must_have"] = remover_duplicatas(must_novo)
        cena["avoid"] = remover_duplicatas(avoid)

        if alterada:
            mudancas.append({
                "scene": numero,
                "segment": segmento,
                "query_before": query_original,
                "query_after": cena["query"],
                "reasons": motivos,
            })

    mapa["visual_risk_guard"] = {
        "version": "3.0.3",
        "changes": len(mudancas),
    }
    return mapa, mudancas


def main():
    if not os.path.exists(SCENE_MAP):
        sys.exit("ERRO: scene_map não encontrado.")

    try:
        with open(SCENE_MAP, "r", encoding="utf-8") as f:
            mapa = json.load(f)
        mapa, mudancas = processar_mapa(mapa)
    except Exception as exc:
        sys.exit(f"ERRO lendo/processando scene_map: {exc}")

    atomic_json(SCENE_MAP, mapa)
    atomic_json(REPORT, {"short_id": SHORT_ID, "changes": mudancas})

    cenas = mapa.get("scenes", [])
    print()
    print("================================")
    print("FACTUAL VISUAL RISK GUARD 3.0.3")
    print("================================")
    print()
    print(f"Cenas analisadas: {len(cenas)}")
    print(f"Cenas ajustadas: {len(mudancas)}")
    print()

    for item in mudancas:
        numero = item.get("scene")
        rotulo = f"{numero:02d}" if isinstance(numero, int) else str(numero or "?")
        print(f"Cena {rotulo}:")
        print(f"  ANTES: {item['query_before']}")
        print(f"  DEPOIS: {item['query_after']}")
        print()

    print("VISUAL RISK GUARD: OK")
    print()


if __name__ == "__main__":
    main()

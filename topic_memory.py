#!/usr/bin/env python3

import re
import unicodedata
from difflib import SequenceMatcher

STOPWORDS = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "do", "da", "dos", "das", "de", "em", "no", "na", "nos", "nas", "e",
    "caso", "casos", "misterio", "misterios", "desaparecimento",
    "desaparecimentos", "morte", "mortes", "crime", "crimes", "incidente",
    "historia", "voo", "flight"
}


def remover_acentos(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def normalizar(texto):
    texto = remover_acentos(texto).lower()
    substituicoes = [
        (r"\bmalaysia airlines flight\s*370\b", "mh370"),
        (r"\bmalaysia airlines\s*370\b", "mh370"),
        (r"\bflight\s*mh\s*370\b", "mh370"),
        (r"\bvoo\s*mh\s*370\b", "mh370"),
        (r"\bvoo\s*370\s*da\s*malaysia\s*airlines\b", "mh370"),
        (r"\bmh[\s\-]*370\b", "mh370")
    ]
    for padrao, novo in substituicoes:
        texto = re.sub(padrao, novo, texto)
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(x for x in texto.split() if x not in STOPWORDS).strip()


def tokens(texto):
    return set(normalizar(texto).split())


def identificadores_especiais(tokens_):
    saida = set()
    for token in tokens_:
        if len(token) < 3 or not any(c.isdigit() for c in token):
            continue
        if any(c.isalpha() for c in token):
            saida.add(token)
            continue
        try:
            numero = int(token)
        except ValueError:
            continue
        if 1800 <= numero <= 2099:
            continue
        saida.add(token)
    return saida


def similaridade(a, b):
    na = normalizar(a)
    nb = normalizar(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    ta = set(na.split())
    tb = set(nb.split())
    compartilhados = identificadores_especiais(ta) & identificadores_especiais(tb)

    # Só IDs alfanuméricos são identidade forte por si só.
    # Um número puro pode aparecer em casos diferentes.
    if any(any(c.isalpha() for c in token) for token in compartilhados):
        return 1.0

    intersecao = ta & tb
    uniao = ta | tb
    jaccard = len(intersecao) / len(uniao) if uniao else 0.0
    menor = min(len(ta), len(tb))
    overlap = len(intersecao) / menor if menor else 0.0

    if menor >= 2 and overlap == 1.0:
        return 0.96

    bonus_core = 0.86 if len(intersecao) >= 2 and overlap >= 0.66 else 0.0
    sequence = SequenceMatcher(None, na, nb).ratio()
    score_base = jaccard * 0.65 + sequence * 0.35
    return min(max(score_base, bonus_core), 1.0)


def encontrar_duplicata(assunto, historico, limite=0.72):
    melhor = None
    melhor_score = 0.0

    for item in historico:
        if isinstance(item, dict):
            existente = str(item.get("topic", ""))
        else:
            existente = str(item)
        if not existente:
            continue
        score = similaridade(assunto, existente)
        if score > melhor_score:
            melhor_score = score
            melhor = existente

    return {
        "duplicate": bool(melhor and melhor_score >= limite),
        "topic": melhor,
        "similarity": round(melhor_score, 3)
    }


if __name__ == "__main__":
    testes = [
        ("O Voo 370 da Malaysia Airlines", "MH370"),
        ("Malaysia Airlines Flight 370", "Voo MH370"),
        ("O desaparecimento da tripulação do Mary Celeste", "Mary Celeste"),
        ("O Caso Elisa Lam", "Morte de Elisa Lam"),
        ("Passo Dyatlov", "Incidente do Passo Dyatlov")
    ]
    print("\n==============================")
    print("TOPIC MEMORY TEST")
    print("==============================\n")
    for a, b in testes:
        print(a)
        print(b)
        print(f"similaridade={similaridade(a, b):.3f}\n")

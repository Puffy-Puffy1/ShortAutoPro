#!/usr/bin/env python3

import re
import unicodedata
from difflib import SequenceMatcher


STOPWORDS = {
    "o", "a", "os", "as",
    "um", "uma", "uns", "umas",
    "do", "da", "dos", "das",
    "de", "em", "no", "na",
    "nos", "nas",
    "e",
    "caso",
    "casos",
    "misterio",
    "misterios",
    "desaparecimento",
    "desaparecimentos",
    "morte",
    "mortes",
    "crime",
    "crimes",
    "incidente",
    "historia",
    "voo",
    "flight"
}


def remover_acentos(texto):

    texto = unicodedata.normalize(
        "NFKD",
        str(texto)
    )

    return "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )


def normalizar(texto):

    texto = remover_acentos(
        texto
    ).lower()

    texto = re.sub(
        r"\bmalaysia airlines flight\s*370\b",
        "mh370",
        texto
    )

    texto = re.sub(
        r"\bmalaysia airlines\s*370\b",
        "mh370",
        texto
    )

    texto = re.sub(
        r"\bflight\s*mh\s*370\b",
        "mh370",
        texto
    )

    texto = re.sub(
        r"\bvoo\s*mh\s*370\b",
        "mh370",
        texto
    )

    texto = re.sub(
        r"\bvoo\s*370\s*da\s*malaysia\s*airlines\b",
        "mh370",
        texto
    )

    texto = re.sub(
        r"\bmh[\s\-]*370\b",
        "mh370",
        texto
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    palavras = []

    for palavra in texto.split():

        if palavra in STOPWORDS:
            continue

        palavras.append(
            palavra
        )

    return " ".join(
        palavras
    ).strip()


def tokens(texto):

    return set(
        normalizar(
            texto
        ).split()
    )


def identificadores_especiais(tokens_):
    """Retorna IDs fortes sem considerar anos comuns como identidade única."""

    saida = set()

    for token in tokens_:

        if len(token) < 3:
            continue

        if not any(
            c.isdigit()
            for c in token
        ):
            continue

        if any(
            c.isalpha()
            for c in token
        ):
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

    ta = set(
        na.split()
    )

    tb = set(
        nb.split()
    )

    especiais_a = identificadores_especiais(
        ta
    )

    especiais_b = identificadores_especiais(
        tb
    )

    if (
        especiais_a
        and especiais_b
        and especiais_a.intersection(
            especiais_b
        )
    ):

        return 1.0

    intersecao = ta.intersection(tb)
    uniao = ta.union(tb)

    if uniao:

        jaccard = (
            len(intersecao)
            / len(uniao)
        )

    else:

        jaccard = 0.0

    menor = min(
        len(ta),
        len(tb)
    )

    if menor > 0:

        overlap = (
            len(intersecao)
            / menor
        )

    else:

        overlap = 0.0

    if (
        menor >= 2
        and overlap == 1.0
    ):

        return 0.96

    if (
        len(intersecao) >= 2
        and overlap >= 0.66
    ):

        bonus_core = 0.86

    else:

        bonus_core = 0.0

    sequence = SequenceMatcher(
        None,
        na,
        nb
    ).ratio()

    score_base = (
        jaccard * 0.65
        + sequence * 0.35
    )

    score = max(
        score_base,
        bonus_core
    )

    return min(
        score,
        1.0
    )


def encontrar_duplicata(
    assunto,
    historico,
    limite=0.72
):

    melhor = None
    melhor_score = 0.0

    for item in historico:

        if isinstance(
            item,
            dict
        ):

            existente = str(
                item.get(
                    "topic",
                    ""
                )
            )

        else:

            existente = str(
                item
            )

        if not existente:
            continue

        score = similaridade(
            assunto,
            existente
        )

        if score > melhor_score:

            melhor_score = score
            melhor = existente

    if (
        melhor
        and melhor_score >= limite
    ):

        return {
            "duplicate": True,
            "topic": melhor,
            "similarity": round(
                melhor_score,
                3
            )
        }

    return {
        "duplicate": False,
        "topic": melhor,
        "similarity": round(
            melhor_score,
            3
        )
    }


if __name__ == "__main__":

    testes = [
        (
            "O Voo 370 da Malaysia Airlines",
            "MH370"
        ),
        (
            "Malaysia Airlines Flight 370",
            "Voo MH370"
        ),
        (
            "O desaparecimento da tripulação do Mary Celeste",
            "Mary Celeste"
        ),
        (
            "O Caso Elisa Lam",
            "Morte de Elisa Lam"
        ),
        (
            "Passo Dyatlov",
            "Incidente do Passo Dyatlov"
        )
    ]

    print()
    print("==============================")
    print("TOPIC MEMORY TEST")
    print("==============================")
    print()

    for a, b in testes:

        score = similaridade(
            a,
            b
        )

        print(a)
        print(b)
        print(
            f"similaridade={score:.3f}"
        )
        print()

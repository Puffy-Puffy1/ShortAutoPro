#!/usr/bin/env python3

import re
import unicodedata
from difflib import SequenceMatcher


# Palavras genéricas que não ajudam muito
# a identificar um caso específico.

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


# =====================================================
# NORMALIZAÇÃO
# =====================================================

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

    # Normalizações conhecidas

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


# =====================================================
# TOKENS
# =====================================================

def tokens(texto):

    return set(
        normalizar(
            texto
        ).split()
    )


# =====================================================
# SIMILARIDADE
# =====================================================

def similaridade(a, b):

    na = normalizar(a)
    nb = normalizar(b)

    if not na or not nb:
        return 0.0

    # Correspondência exata depois
    # da normalização.

    if na == nb:
        return 1.0

    ta = set(
        na.split()
    )

    tb = set(
        nb.split()
    )

    # Se ambos contêm um identificador
    # muito específico como MH370.

    especiais_a = {
        x for x in ta
        if (
            any(
                c.isdigit()
                for c in x
            )
            and len(x) >= 3
        )
    }

    especiais_b = {
        x for x in tb
        if (
            any(
                c.isdigit()
                for c in x
            )
            and len(x) >= 3
        )
    }

    if (
        especiais_a
        and especiais_b
        and especiais_a.intersection(
            especiais_b
        )
    ):

        return 1.0

    # Jaccard dos tokens

    intersecao = ta.intersection(tb)
    uniao = ta.union(tb)

    if uniao:

        jaccard = (
            len(intersecao)
            / len(uniao)
        )

    else:

        jaccard = 0.0


    # =================================
    # OVERLAP DO NÚCLEO
    # =================================
    #
    # Exemplo:
    #
    # "Mary Celeste"
    # "tripulacao Mary Celeste"
    #
    # ou:
    #
    # "navio Mary Celeste"
    # "tripulacao Mary Celeste"
    #
    # compartilham o mesmo núcleo
    # específico do assunto.

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


    # Correspondência completa do
    # título menor dentro do maior.

    if (
        menor >= 2
        and overlap == 1.0
    ):

        return 0.96


    # Dois ou mais termos específicos em
    # comum e pelo menos 2/3 do título
    # menor coincidem.

    if (
        len(intersecao) >= 2
        and overlap >= 0.66
    ):

        bonus_core = 0.86

    else:

        bonus_core = 0.0


    # Similaridade textual

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


# =====================================================
# DETECTOR DE DUPLICATA
# =====================================================

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
            "similarity":
                round(
                    melhor_score,
                    3
                )
        }


    return {
        "duplicate": False,
        "topic": melhor,
        "similarity":
            round(
                melhor_score,
                3
            )
    }


# =====================================================
# TESTE MANUAL
# =====================================================

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

        print(
            f"{a}"
        )

        print(
            f"{b}"
        )

        print(
            f"similaridade={score:.3f}"
        )

        print()

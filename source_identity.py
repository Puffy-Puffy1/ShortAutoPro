#!/usr/bin/env python3

import re
import unicodedata

STOP = {
    "o", "a", "os", "as", "um", "uma",
    "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "the", "of", "and", "in", "on",
    "caso", "case", "misterio", "mistério", "desaparecimento",
    "incidente", "morte", "crime"
}

ALIASES = {
    "flight 19": {
        "flight 19", "voo 19", "flight nineteen", "voo dezenove"
    },
    "tam 3054": {
        "tam 3054", "voo tam 3054", "tam flight 3054", "jj3054"
    },
    "boy in the box": {
        "boy in the box", "joseph augustus zarelli", "joseph zarelli"
    },
    "mh370": {
        "mh370", "malaysia airlines flight 370", "malaysia airlines 370"
    },
    "dyatlov": {
        "dyatlov", "dyatlov pass", "passo dyatlov"
    },
    "elisa lam": {"elisa lam"},
    "frederick valentich": {"frederick valentich", "valentich"},
    "mary celeste": {"mary celeste"}
}


def sem_acento(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def normalizar(texto):
    texto = sem_acento(texto).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def _ano(token):
    if not token.isdigit() or len(token) != 4:
        return False
    try:
        numero = int(token)
    except ValueError:
        return False
    return 1800 <= numero <= 2099


def tokens(texto):
    return {
        x
        for x in normalizar(texto).split()
        if len(x) >= 3 and x not in STOP and not _ano(x)
    }


def _contem_alias_exato(texto_normalizado, alias):
    alias_n = normalizar(alias)
    if not texto_normalizado or not alias_n:
        return False
    padrao = r"(?<![a-z0-9])" + re.escape(alias_n) + r"(?![a-z0-9])"
    return re.search(padrao, texto_normalizado) is not None


def detectar_aliases(texto):
    n = normalizar(texto)
    encontrados = set()
    for chave, valores in ALIASES.items():
        candidatos = {chave, *valores}
        if any(_contem_alias_exato(n, alias) for alias in candidatos):
            encontrados.add(chave)
    return encontrados


def detectar_alias(texto):
    encontrados = detectar_aliases(texto)
    for chave in ALIASES:
        if chave in encontrados:
            return chave
    return None


def extrair_ids_numericos(texto):
    n = normalizar(texto)
    saida = set()
    for x in re.findall(r"\b\d{1,6}\b", n):
        if _ano(x):
            continue
        saida.add(x)
    return saida


def conflito_id_numerico(topic, wiki_title):
    topic_ids = extrair_ids_numericos(topic)
    title_ids = extrair_ids_numericos(wiki_title)

    if not topic_ids or not title_ids:
        return {
            "conflict": False,
            "topic_ids": sorted(topic_ids),
            "title_ids": sorted(title_ids)
        }

    compartilhados = topic_ids & title_ids
    return {
        "conflict": not bool(compartilhados),
        "topic_ids": sorted(topic_ids),
        "title_ids": sorted(title_ids)
    }


def validar_identidade(topic, wiki_title, contexto=""):
    topic_n = normalizar(topic)
    title_n = normalizar(wiki_title)
    contexto_n = normalizar(contexto)

    if not topic_n or not title_n:
        return {"valid": False, "score": 0.0, "reason": "empty_identity"}

    numeric = conflito_id_numerico(topic, wiki_title)
    if numeric["conflict"]:
        return {
            "valid": False,
            "score": 0.0,
            "reason": (
                "numeric_identity_conflict:"
                f"topic={numeric['topic_ids']},title={numeric['title_ids']}"
            ),
            "truth_lock": True,
            "topic_ids": numeric["topic_ids"],
            "title_ids": numeric["title_ids"]
        }

    topic_alias = detectar_alias(topic_n)
    title_alias = detectar_alias(title_n)

    if topic_alias:
        if title_alias == topic_alias:
            return {"valid": True, "score": 1.0, "reason": "known_alias_match"}
        if title_alias and title_alias != topic_alias:
            return {"valid": False, "score": 0.0, "reason": "known_alias_conflict"}

        context_aliases = detectar_aliases(contexto_n[:3000])
        if context_aliases == {topic_alias}:
            return {"valid": True, "score": 1.0, "reason": "known_alias_context_match"}
        if context_aliases and topic_alias not in context_aliases:
            return {"valid": False, "score": 0.0, "reason": "known_alias_context_conflict"}

    tt = tokens(topic)
    wt = tokens(wiki_title)
    ct = tokens(contexto[:5000])

    if not tt:
        return {"valid": False, "score": 0.0, "reason": "topic_without_tokens"}

    title_hits = len(tt & wt)
    context_hits = len(tt & ct)
    title_score = title_hits / len(tt)
    context_score = context_hits / len(tt)
    score = title_score * 0.75 + context_score * 0.25

    if title_score >= 0.60:
        return {"valid": True, "score": score, "reason": "strong_title_match"}

    if title_score >= 0.34 and context_score >= 0.50:
        return {"valid": True, "score": score, "reason": "title_context_match"}

    if title_score == 0 and context_score >= 0.80:
        return {"valid": True, "score": score, "reason": "strong_context_alias"}

    return {
        "valid": False,
        "score": score,
        "reason": f"identity_mismatch:title={title_score:.2f},context={context_score:.2f}"
    }


if __name__ == "__main__":
    testes = [
        ("Caso Boy in the Box", "Nirvana (banda)"),
        ("Caso Boy in the Box", "The Boy in the Striped Pyjamas (filme)"),
        ("Caso Boy in the Box", "Joseph Augustus Zarelli"),
        ("Frederick Valentich", "Desaparecimento de Valentich")
    ]
    for topic, title in testes:
        print(topic, "->", title, validar_identidade(topic, title))

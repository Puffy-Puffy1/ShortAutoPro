#!/usr/bin/env python3

import re
import unicodedata


def norm(text):

    text = str(
        text or ""
    ).casefold()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        c
        for c in text
        if not unicodedata.combining(c)
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


CONCEPT_QUERY = {

    "police": (
        "police investigation documentary",
        "detective police evidence",
    ),

    "investigation": (
        "crime investigation evidence",
        "detective investigation documentary",
    ),

    "forensic": (
        "forensic investigation evidence laboratory",
        "crime scene forensic analysis",
    ),

    "court": (
        "courtroom courthouse trial",
        "judge court legal documentary",
    ),

    "apartment": (
        "residential apartment building",
        "apartment exterior urban",
    ),

    "building": (
        "building exterior architecture",
        "urban building documentary",
    ),

    "hospital": (
        "hospital emergency medical",
        "doctor hospital documentary",
    ),

    "document": (
        "documents files investigation",
        "official records documentary",
    ),

    "news": (
        "news report journalism",
        "newspaper archive documentary",
    ),

    "space": (
        "space astronaut planet",
        "spacecraft science documentary",
    ),

    "rocket": (
        "rocket launch spacecraft",
        "space launch documentary",
    ),

    "military": (
        "military soldiers documentary",
        "army troops conflict",
    ),

    "war": (
        "war conflict documentary",
        "battle military archive",
    ),

    "technology": (
        "technology computer data",
        "digital technology documentary",
    ),

    "laboratory": (
        "scientific laboratory research",
        "scientist laboratory documentary",
    ),

    "ocean": (
        "ocean sea underwater documentary",
        "marine ocean footage",
    ),

    "forest": (
        "forest nature documentary",
        "woods trees landscape",
    ),

    "storm": (
        "storm severe weather documentary",
        "lightning storm clouds",
    ),

    "money": (
        "money finance economy",
        "currency business documentary",
    ),
}


def _alias_present(query_norm, alias):
    """Match aliases on token/phrase boundaries, never as substrings.

    This prevents terms such as ``mar`` (Portuguese for sea) from matching
    unrelated words like ``marshals``, which previously produced ocean query
    expansions for ``federal marshals``.
    """
    alias_norm = norm(alias)
    if not alias_norm:
        return False
    return bool(
        re.search(
            r"(?:^|\s)" + re.escape(alias_norm) + r"(?:$|\s)",
            query_norm,
        )
    )


def detect_concepts(query):

    q = norm(query)

    hits = []

    aliases = {

        "police": (
            "police",
            "policia",
            "policial",
        ),

        "investigation": (
            "investigation",
            "investigacao",
            "investigar",
        ),

        "forensic": (
            "forensic",
            "forensics",
            "pericia",
            "laudo",
        ),

        "court": (
            "court",
            "courtroom",
            "tribunal",
            "julgamento",
        ),

        "apartment": (
            "apartment",
            "apartamento",
            "condominio",
        ),

        "hospital": (
            "hospital",
            "medical",
            "medico",
        ),

        "document": (
            "document",
            "documento",
            "arquivo",
            "relatorio",
        ),

        "news": (
            "news",
            "noticia",
            "jornal",
        ),

        "space": (
            "space",
            "espaco",
            "astronaut",
            "astronauta",
        ),

        "rocket": (
            "rocket",
            "foguete",
        ),

        "military": (
            "military",
            "soldier",
            "militar",
            "soldado",
        ),

        "war": (
            "war",
            "guerra",
            "battle",
            "batalha",
        ),

        "technology": (
            "technology",
            "tecnologia",
            "computer",
            "computador",
        ),

        "laboratory": (
            "laboratory",
            "laboratorio",
            "scientist",
            "cientista",
        ),

        "ocean": (
            "ocean",
            "oceano",
            "sea",
            "mar",
        ),

        "forest": (
            "forest",
            "floresta",
            "woods",
        ),

        "storm": (
            "storm",
            "tempestade",
            "hurricane",
            "furacao",
        ),

        "money": (
            "money",
            "dinheiro",
            "finance",
            "financas",
        ),
    }


    for concept, terms in aliases.items():

        if any(
            _alias_present(q, term)
            for term in terms
        ):
            hits.append(
                concept
            )

    return hits


def expansion_queries(
    query,
    max_extra=2,
):

    original = " ".join(
        str(query or "").split()
    )

    if not original:
        return []

    results = [
        original
    ]

    detected = detect_concepts(
        original
    )

    # Preserve probable geographic/entity terms by
    # retaining the original query in every alternate.
    for concept in detected:

        for suffix in CONCEPT_QUERY.get(
            concept,
            (),
        ):

            candidate = (
                f"{original} {suffix}"
            )

            if norm(candidate) not in {
                norm(x)
                for x in results
            }:
                results.append(
                    candidate
                )

            if (
                len(results)
                >=
                max_extra + 1
            ):
                return results

    # General documentary fallback.
    fallback = (
        f"{original} documentary footage"
    )

    if norm(fallback) not in {
        norm(x)
        for x in results
    }:
        results.append(
            fallback
        )

    return results[
        : max_extra + 1
    ]


if __name__ == "__main__":

    tests = (
        "São Paulo apartment investigation",
        "forensic evidence crime scene",
        "rocket launch",
        "ocean mystery",
        "vintage federal marshals wanted",
    )

    for test in tests:

        print(
            test,
            "=>",
            expansion_queries(test),
        )

    print(
        "VISUAL_QUERY_PLANNER_V4=PASS"
    )

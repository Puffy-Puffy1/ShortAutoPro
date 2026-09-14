#!/usr/bin/env python3

import re
import unicodedata

# =====================================================
# SHORTAUTO PRO
# EVIDENCE PRIORITY ROUTER 3.7
# =====================================================

DOCUMENTARY_FIRST = {
    "document",
    "evidence",
    "location",
    "architecture",
    "map_context"
}

MIXED = {
    "transport"
}

STOCK_FIRST = {
    "human_context",
    "environment",
    "object",
    "abstract_context"
}


def _normalize(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(
        c for c in texto if not unicodedata.combining(c)
    ).lower()


def _tokens(texto):
    return set(
        re.findall(
            r"[a-z0-9]+",
            _normalize(texto)
        )
    )


def escolher_rota(
    visual_mode,
    must_have=None
):

    visual_mode = str(
        visual_mode or ""
    ).strip().lower()

    must_have = [
        str(x)
        for x in (
            must_have
            or []
        )
    ]

    if visual_mode in DOCUMENTARY_FIRST:

        return {
            "route": "documentary_first",
            "wikimedia": True,
            "stock": True,
            "wikimedia_bonus": 35.0,
            "stock_penalty": -8.0
        }

    if visual_mode in MIXED:

        return {
            "route": "mixed",
            "wikimedia": True,
            "stock": True,
            "wikimedia_bonus": 18.0,
            "stock_penalty": 0.0
        }

    if visual_mode in STOCK_FIRST:

        return {
            "route": "stock_first",
            "wikimedia": True,
            "stock": True,
            "wikimedia_bonus": 0.0,
            "stock_penalty": 0.0
        }

    documental = {
        # English
        "document",
        "report",
        "newspaper",
        "archive",
        "map",
        "building",
        "hotel",
        "house",
        "airplane",
        "plane",
        "ship",
        "train",
        "letter",
        "record",
        # Portuguese, normalized without accents
        "documento",
        "relatorio",
        "jornal",
        "arquivo",
        "mapa",
        "predio",
        "edificio",
        "hotel",
        "casa",
        "aviao",
        "aeronave",
        "navio",
        "trem",
        "carta",
        "registro",
    }

    if any(
        documental.intersection(
            _tokens(item)
        )
        for item in must_have
    ):

        return {
            "route": "mixed",
            "wikimedia": True,
            "stock": True,
            "wikimedia_bonus": 15.0,
            "stock_penalty": 0.0
        }

    return {
        "route": "stock_first",
        "wikimedia": True,
        "stock": True,
        "wikimedia_bonus": 0.0,
        "stock_penalty": 0.0
    }


if __name__ == "__main__":

    testes = [
        "document",
        "evidence",
        "transport",
        "environment",
        "human_context"
    ]

    for modo in testes:

        print(
            modo,
            "->",
            escolher_rota(modo)
        )

#!/usr/bin/env python3

import os
import re
import unicodedata

from urllib.parse import urlparse


def truth(name, default="1"):

    return (
        os.getenv(
            name,
            default,
        ).strip().lower()
        not in {
            "0",
            "false",
            "no",
            "off",
            "",
        }
    )


def norm(value):

    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        value = str(value)

    value = unicodedata.normalize(
        "NFKD",
        value.casefold(),
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(
            char
        )
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


STOP = {
    "a","an","and","as","at","by",
    "da","das","de","do","dos",
    "e","em","for","from","in",
    "is","na","nas","no","nos",
    "o","of","on","os","or",
    "para","por","que","the",
    "to","um","uma","with",
}


def tokens(value):

    return {
        token
        for token in norm(
            value
        ).split()
        if (
            len(token) > 1
            and token not in STOP
        )
    }


def objget(
    obj,
    keys,
    default=None,
):

    if not isinstance(
        keys,
        (
            list,
            tuple,
            set,
        ),
    ):
        keys = [keys]

    for key in keys:

        if isinstance(
            obj,
            dict,
        ):

            if (
                key in obj
                and obj[key] is not None
            ):
                return obj[key]

            wanted = norm(
                key
            )

            for real_key, value in obj.items():

                if not isinstance(
                    real_key,
                    str,
                ):
                    continue

                if (
                    norm(real_key)
                    ==
                    wanted
                    and value is not None
                ):
                    return value

        else:

            try:
                value = getattr(
                    obj,
                    str(key),
                    None,
                )

                if value is not None:
                    return value

            except Exception:
                pass

    return default


def flatten(value):

    if value is None:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        result = []

        for item in value:
            result.extend(
                flatten(
                    item
                )
            )

        return result

    return [value]


EVIDENCE_FIELDS = (
    "title",
    "name",
    "description",
    "caption",
    "alt",
    "alt_text",
    "tags",
    "keywords",
    "terms",
    "category",
    "filename",
    "provider",
    "source_group",
    "source_name",
)


NESTED_FIELDS = (
    "metadata",
    "meta",
    "source_metadata",
    "provenance",
)


def candidate_text(candidate):

    parts = []


    def add(value):

        if value is None:
            return

        if isinstance(
            value,
            dict,
        ):

            for field in EVIDENCE_FIELDS:

                if field in value:

                    add(
                        value.get(
                            field
                        )
                    )

            return


        for item in flatten(
            value
        ):

            text = str(
                item
            ).strip()

            if text:
                parts.append(
                    text
                )


    if isinstance(
        candidate,
        dict,
    ):

        for field in EVIDENCE_FIELDS:

            add(
                candidate.get(
                    field
                )
            )


        for field in NESTED_FIELDS:

            nested = candidate.get(
                field
            )

            if isinstance(
                nested,
                dict,
            ):

                add(
                    nested
                )

    else:

        for field in EVIDENCE_FIELDS:

            add(
                objget(
                    candidate,
                    field,
                )
            )


    # IMPORTANTE:
    # query/search_query NÃO entram como evidência.
    # Isso impede o candidato de "ganhar relevância"
    # apenas porque recebeu a própria consulta.

    clean = []
    seen = set()

    for part in parts:

        key = norm(
            part
        )

        if (
            key
            and key not in seen
        ):

            seen.add(
                key
            )

            clean.append(
                part
            )

    return " ".join(
        clean
    )


def scene_text(scene):

    if isinstance(
        scene,
        str,
    ):
        return scene

    if not isinstance(
        scene,
        dict,
    ):
        return str(
            scene or ""
        )

    parts = []

    for field in (
        "texto",
        "text",
        "narration",
        "visual_query",
        "query",
        "location",
        "local",
        "must_have",
    ):

        value = scene.get(
            field
        )

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            parts.extend(
                str(x)
                for x in value
            )

        elif value:

            parts.append(
                str(value)
            )

    return " ".join(
        parts
    )


def must_terms(scene):

    if not isinstance(
        scene,
        dict,
    ):
        return []

    value = (
        scene.get(
            "must_have"
        )
        or
        scene.get(
            "must"
        )
        or
        []
    )

    if isinstance(
        value,
        str,
    ):
        return [
            value
        ]

    return [
        str(x)
        for x in flatten(
            value
        )
        if str(x).strip()
    ]


def avoid_terms(scene):

    if not isinstance(
        scene,
        dict,
    ):
        return []

    value = (
        scene.get(
            "avoid"
        )
        or
        scene.get(
            "avoid_terms"
        )
        or
        []
    )

    if isinstance(
        value,
        str,
    ):
        return [
            value
        ]

    return [
        str(x)
        for x in flatten(
            value
        )
        if str(x).strip()
    ]


def provider(candidate):

    value = objget(
        candidate,
        (
            "provider",
            "source",
            "site",
            "platform",
            "origin",
        ),
        "",
    )

    if value:

        return norm(
            value
        )


    url = objget(
        candidate,
        (
            "source_url",
            "url",
            "download_url",
        ),
        "",
    )

    try:

        host = (
            urlparse(
                str(url)
            )
            .netloc
            .casefold()
            .removeprefix(
                "www."
            )
        )

        for name in (
            "pixabay",
            "pexels",
            "wikimedia",
            "coverr",
            "unsplash",
        ):

            if name in host:
                return name

        return (
            host
            or
            "unknown"
        )

    except Exception:

        return "unknown"


def source_group(candidate):

    value = objget(
        candidate,
        (
            "source_group",
            "group",
            "collection",
            "domain",
            "source_domain",
        ),
        "",
    )

    if value:

        return norm(
            value
        )


    url = objget(
        candidate,
        (
            "source_url",
            "url",
        ),
        "",
    )

    try:

        host = (
            urlparse(
                str(url)
            )
            .netloc
            .casefold()
            .removeprefix(
                "www."
            )
        )

        return (
            host
            or
            provider(
                candidate
            )
        )

    except Exception:

        return provider(
            candidate
        )


def media_type(candidate):

    value = norm(
        objget(
            candidate,
            (
                "media_type",
                "type",
                "tipo",
                "kind",
            ),
            "",
        )
    )

    if any(
        word in value
        for word in (
            "video",
            "movie",
            "motion",
            "clip",
        )
    ):

        return "video"


    if any(
        word in value
        for word in (
            "foto",
            "photo",
            "image",
            "imagem",
            "picture",
        )
    ):

        return "photo"


    path = str(
        objget(
            candidate,
            (
                "local_path",
                "path",
                "url",
            ),
            "",
        )
    ).casefold()


    if path.endswith(
        (
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
        )
    ):
        return "video"


    if path.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    ):
        return "photo"

    return (
        value
        or
        "unknown"
    )


def number(
    value,
    default=0.0,
):

    if value is None:
        return default

    try:
        return float(
            value
        )

    except Exception:
        pass


    match = re.search(
        r"-?\d+(?:[.,]\d+)?",
        str(value),
    )

    if not match:
        return default

    return float(
        match.group(0).replace(
            ",",
            ".",
        )
    )


def base_score(candidate):

    return number(
        objget(
            candidate,
            (
                "score",
                "base_score",
                "quality_score",
                "rank_score",
                "semantic_score",
                "relevance_score",
            ),
            0,
        ),
        0,
    )


def dimensions(candidate):

    width = int(
        number(
            objget(
                candidate,
                (
                    "width",
                    "largura",
                ),
                0,
            ),
            0,
        )
    )

    height = int(
        number(
            objget(
                candidate,
                (
                    "height",
                    "altura",
                ),
                0,
            ),
            0,
        )
    )

    return (
        width,
        height,
    )


def candidate_key(candidate):

    for field in (
        "sha256",
        "id",
        "video_id",
        "photo_id",
        "asset_id",
        "source_url",
        "url",
        "download_url",
        "local_path",
        "path",
    ):

        value = objget(
            candidate,
            field,
            None,
        )

        if value not in (
            None,
            "",
        ):

            return (
                provider(
                    candidate
                )
                +
                ":"
                +
                norm(
                    value
                )
            )


    return (
        provider(
            candidate
        )
        +
        ":"
        +
        media_type(
            candidate
        )
        +
        ":"
        +
        norm(
            candidate_text(
                candidate
            )
        )
    )


def must_tier(
    candidate,
    scene=None,
):

    value = objget(
        candidate,
        (
            "must_tier",
            "must_coverage",
            "must_score",
            "must",
            "must_hits",
        ),
        None,
    )


    if (
        isinstance(
            value,
            str,
        )
        and "/" in value
    ):

        try:

            have, total = value.split(
                "/",
                1,
            )

            ratio = (
                float(have)
                /
                float(total)
            )

            if ratio >= 0.90:
                return 2

            if ratio >= 0.45:
                return 1

            return 0

        except Exception:
            pass


    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        if len(value) >= 2:
            return 2

        if len(value) == 1:
            return 1

        return 0


    if value is not None:

        parsed = number(
            value,
            None,
        )

        if parsed is not None:

            if 0 <= parsed <= 1:

                if parsed >= 0.90:
                    return 2

                if parsed >= 0.45:
                    return 1

                return 0

            if parsed >= 2:
                return 2

            if parsed >= 1:
                return 1

            return 0


    required = must_terms(
        scene
    )

    if not required:
        return 0


    text = (
        " "
        +
        norm(
            candidate_text(
                candidate
            )
        )
        +
        " "
    )

    hits = 0

    for item in required:

        item = norm(
            item
        )

        if (
            item
            and
            f" {item} " in text
        ):

            hits += 1


    if hits >= min(
        2,
        len(required),
    ):
        return 2

    if hits:
        return 1

    return 0


def phrase_present(
    text,
    phrase,
):

    text = (
        " "
        +
        norm(
            text
        )
        +
        " "
    )

    phrase = norm(
        phrase
    )

    return (
        bool(
            phrase
        )
        and
        f" {phrase} "
        in text
    )


GEO = {

    "brazil": (
        "country",
        None,
        (
            "brazil",
            "brasil",
            "brazilian",
            "brasileiro",
            "brasileira",
        ),
    ),

    "sao_paulo": (
        "city",
        "brazil",
        (
            "sao paulo",
            "sp brazil",
            "sp brasil",
            "avenida paulista",
            "ibirapuera",
        ),
    ),

    "rio_de_janeiro": (
        "city",
        "brazil",
        (
            "rio de janeiro",
            "copacabana",
            "ipanema",
            "cristo redentor",
            "christ the redeemer",
            "pao de acucar",
            "sugarloaf",
        ),
    ),

    "brasilia": (
        "city",
        "brazil",
        (
            "brasilia",
            "distrito federal brazil",
        ),
    ),

    "usa": (
        "country",
        None,
        (
            "united states",
            "united states of america",
            "usa",
            "american",
        ),
    ),

    "new_york": (
        "city",
        "usa",
        (
            "new york",
            "new york city",
            "nyc",
            "manhattan",
            "brooklyn",
            "queens",
            "bronx",
            "times square",
            "central park",
            "empire state building",
            "statue of liberty",
        ),
    ),

    "los_angeles": (
        "city",
        "usa",
        (
            "los angeles",
            "hollywood",
            "beverly hills",
            "santa monica",
        ),
    ),

    "washington_dc": (
        "city",
        "usa",
        (
            "washington dc",
            "white house",
            "capitol hill",
            "us capitol",
        ),
    ),

    "united_kingdom": (
        "country",
        None,
        (
            "united kingdom",
            "great britain",
            "britain",
            "england",
            "british",
        ),
    ),

    "london": (
        "city",
        "united_kingdom",
        (
            "london",
            "big ben",
            "westminster",
            "tower bridge",
            "buckingham palace",
        ),
    ),

    "france": (
        "country",
        None,
        (
            "france",
            "french",
            "franca",
        ),
    ),

    "paris": (
        "city",
        "france",
        (
            "paris",
            "eiffel tower",
            "louvre",
            "champs elysees",
        ),
    ),

    "italy": (
        "country",
        None,
        (
            "italy",
            "italian",
            "italia",
        ),
    ),

    "rome": (
        "city",
        "italy",
        (
            "rome",
            "roma",
            "colosseum",
            "coliseu",
            "vatican",
            "vaticano",
        ),
    ),

    "japan": (
        "country",
        None,
        (
            "japan",
            "japanese",
            "japao",
        ),
    ),

    "tokyo": (
        "city",
        "japan",
        (
            "tokyo",
            "toquio",
            "shibuya",
            "shinjuku",
            "tokyo tower",
        ),
    ),

    "china": (
        "country",
        None,
        (
            "china",
            "chinese",
        ),
    ),

    "russia": (
        "country",
        None,
        (
            "russia",
            "russian",
            "moscow",
            "moscou",
        ),
    ),

    "ukraine": (
        "country",
        None,
        (
            "ukraine",
            "ukrainian",
            "ucrania",
            "kyiv",
            "kiev",
        ),
    ),

    "mexico": (
        "country",
        None,
        (
            "mexico",
            "mexican",
            "mexicano",
        ),
    ),

    "argentina": (
        "country",
        None,
        (
            "argentina",
            "argentinian",
            "buenos aires",
        ),
    ),

    "canada": (
        "country",
        None,
        (
            "canada",
            "canadian",
            "toronto",
            "vancouver",
            "montreal",
            "ottawa",
        ),
    ),

    "india": (
        "country",
        None,
        (
            "india",
            "indian",
            "new delhi",
            "delhi",
            "mumbai",
        ),
    ),

    "australia": (
        "country",
        None,
        (
            "australia",
            "australian",
            "sydney",
            "melbourne",
        ),
    ),
}


def geo_hits(text):

    result = set()

    for entity, data in GEO.items():

        aliases = data[2]

        if any(
            phrase_present(
                text,
                alias,
            )
            for alias in aliases
        ):

            result.add(
                entity
            )

    return result


def geo_countries(hits):

    result = set()

    for entity in hits:

        level, parent, _ = GEO[
            entity
        ]

        if level == "country":

            result.add(
                entity
            )

        elif parent:

            result.add(
                parent
            )

    return result


def geo_cities(hits):

    return {
        entity
        for entity in hits
        if GEO[
            entity
        ][0] == "city"
    }


def geo_conflict(
    scene_value,
    candidate_value,
):

    scene_geo = geo_hits(
        scene_value
    )

    candidate_geo = geo_hits(
        candidate_value
    )


    if (
        not scene_geo
        or not candidate_geo
    ):

        return (
            False,
            "",
        )


    scene_country = geo_countries(
        scene_geo
    )

    candidate_country = geo_countries(
        candidate_geo
    )


    if (
        scene_country
        and candidate_country
        and scene_country.isdisjoint(
            candidate_country
        )
    ):

        return (
            True,
            "COUNTRY:"
            +
            str(
                sorted(
                    scene_country
                )
            )
            +
            "!="
            +
            str(
                sorted(
                    candidate_country
                )
            ),
        )


    scene_city = geo_cities(
        scene_geo
    )

    candidate_city = geo_cities(
        candidate_geo
    )


    if (
        scene_city
        and candidate_city
        and scene_city.isdisjoint(
            candidate_city
        )
    ):

        return (
            True,
            "CITY:"
            +
            str(
                sorted(
                    scene_city
                )
            )
            +
            "!="
            +
            str(
                sorted(
                    candidate_city
                )
            ),
        )


    return (
        False,
        "",
    )


CONCEPTS = {

    "police":
        (
            "police",
            "policia",
            "policial",
            "detective",
            "detetive",
            "delegacia",
        ),

    "investigation":
        (
            "investigation",
            "investigacao",
            "investigator",
            "investigador",
            "inquiry",
            "apuracao",
        ),

    "crime_scene":
        (
            "crime scene",
            "cena do crime",
            "local do crime",
        ),

    "evidence":
        (
            "evidence",
            "evidencia",
            "indicio",
            "indicios",
            "clue",
            "vestigio",
            "proof",
            "prova",
        ),

    "forensics":
        (
            "forensic",
            "forensics",
            "pericia",
            "pericial",
            "laudo",
            "autopsy",
            "necropsia",
        ),

    "court":
        (
            "court",
            "courtroom",
            "courthouse",
            "tribunal",
            "forum",
            "julgamento",
            "judge",
            "juiz",
        ),

    "prison":
        (
            "prison",
            "jail",
            "prisao",
            "cadeia",
            "cela",
        ),

    "apartment":
        (
            "apartment",
            "apartamento",
            "condominium",
            "condominio",
        ),

    "building":
        (
            "building",
            "predio",
            "edificio",
            "facade",
            "fachada",
        ),

    "home":
        (
            "home",
            "house",
            "casa",
            "residence",
            "residencia",
        ),

    "room":
        (
            "room",
            "bedroom",
            "quarto",
            "sala",
            "interior",
        ),

    "document":
        (
            "document",
            "documento",
            "report",
            "relatorio",
            "file",
            "arquivo",
            "records",
        ),

    "news":
        (
            "news",
            "noticia",
            "newspaper",
            "jornal",
            "reporter",
            "jornalista",
            "headline",
            "manchete",
        ),

    "hospital":
        (
            "hospital",
            "ambulance",
            "ambulancia",
            "doctor",
            "medico",
            "emergency",
            "emergencia",
        ),

    "medicine":
        (
            "medicine",
            "medication",
            "pill",
            "pills",
            "tablet",
            "remedio",
            "medicamento",
            "comprimido",
        ),

    "fire":
        (
            "fire",
            "incendio",
            "flame",
            "chama",
            "smoke",
            "fumaca",
        ),

    "car":
        (
            "car",
            "vehicle",
            "carro",
            "veiculo",
            "automobile",
        ),

    "aircraft":
        (
            "aircraft",
            "airplane",
            "plane",
            "aviao",
            "aeronave",
            "aviation",
        ),

    "ship":
        (
            "ship",
            "boat",
            "navio",
            "barco",
            "vessel",
        ),

    "forest":
        (
            "forest",
            "floresta",
            "woods",
            "mata",
            "trees",
            "arvores",
        ),

    "ocean":
        (
            "ocean",
            "sea",
            "oceano",
            "mar",
            "underwater",
            "subaquatico",
        ),

    "storm":
        (
            "storm",
            "tempestade",
            "hurricane",
            "furacao",
            "tornado",
            "lightning",
            "raio",
        ),

    "computer":
        (
            "computer",
            "computador",
            "laptop",
            "notebook",
            "screen",
            "tela",
        ),

    "technology":
        (
            "technology",
            "tecnologia",
            "digital",
            "network",
            "rede",
            "data",
            "dados",
        ),

    "laboratory":
        (
            "laboratory",
            "laboratorio",
            "scientist",
            "cientista",
            "microscope",
            "microscopio",
            "research",
            "pesquisa",
        ),

    "space":
        (
            "space",
            "espaco",
            "planet",
            "planeta",
            "moon",
            "lua",
            "astronaut",
            "astronauta",
            "universe",
            "universo",
        ),

    "rocket":
        (
            "rocket",
            "foguete",
            "launch",
            "lancamento",
            "spacecraft",
            "nave espacial",
        ),

    "money":
        (
            "money",
            "dinheiro",
            "cash",
            "currency",
            "moeda",
            "banknote",
            "cedula",
        ),

    "business":
        (
            "business",
            "negocio",
            "office",
            "escritorio",
            "company",
            "empresa",
            "corporate",
        ),

    "military":
        (
            "military",
            "militar",
            "soldier",
            "soldado",
            "army",
            "exercito",
            "troops",
            "tropas",
        ),

    "war":
        (
            "war",
            "guerra",
            "battle",
            "batalha",
            "combat",
            "combate",
            "conflict",
            "conflito",
        ),
}


def concept_hits(text):

    result = set()

    for concept, aliases in CONCEPTS.items():

        if any(
            phrase_present(
                text,
                alias,
            )
            for alias in aliases
        ):

            result.add(
                concept
            )

    return result


GENERIC_LIFESTYLE = {
    "lifestyle",
    "relaxing",
    "relax",
    "smiling",
    "happy",
    "fashion",
    "beauty",
    "wellness",
    "leisure",
    "vacation",
    "coffee",
    "shopping",
    "selfie",
    "influencer",
    "posing",
    "portrait",
    "model",
    "romantic",
    "couple",
    "dating",
    "relaxando",
    "sorrindo",
    "feliz",
    "moda",
    "beleza",
    "lazer",
    "ferias",
    "compras",
    "retrato",
    "modelo",
    "casal",
}


MEDICINE_TERMS = set(
    CONCEPTS[
        "medicine"
    ]
)


CRITICAL_CONCEPTS = {
    "police",
    "investigation",
    "crime_scene",
    "evidence",
    "forensics",
    "court",
    "prison",
    "news",
    "hospital",
    "fire",
    "military",
    "war",
    "laboratory",
    "space",
}


def term_hits(
    text,
    terms,
):

    return {
        norm(
            term
        )
        for term in terms
        if phrase_present(
            text,
            term,
        )
    }


def score_candidate(
    candidate,
    scene,
    state=None,
):

    state = state or {}

    scene_value = scene_text(
        scene
    )

    candidate_value = candidate_text(
        candidate
    )


    scene_tokens = tokens(
        scene_value
    )

    candidate_tokens = tokens(
        candidate_value
    )


    scene_concepts = concept_hits(
        scene_value
    )

    candidate_concepts = concept_hits(
        candidate_value
    )


    concept_overlap = (
        scene_concepts
        &
        candidate_concepts
    )


    geo_bad, geo_reason = geo_conflict(
        scene_value,
        candidate_value,
    )


    tier = must_tier(
        candidate,
        scene,
    )


    base = base_score(
        candidate
    )

    bonus = 0.0
    penalty = 0.0
    reasons = []


    bonus += {
        0: 0,
        1: 45,
        2: 95,
    }.get(
        tier,
        0,
    )


    bonus += min(
        45,
        15
        *
        len(
            concept_overlap
        ),
    )


    token_overlap = len(
        scene_tokens
        &
        candidate_tokens
    )


    bonus += min(
        28,
        4
        *
        token_overlap,
    )


    if geo_bad:

        penalty += 500

        reasons.append(
            "GEO_CONTRADICTION:"
            +
            geo_reason
        )


    medicine_hits = term_hits(
        candidate_value,
        MEDICINE_TERMS,
    )


    if (
        medicine_hits
        and not (
            {
                "medicine",
                "hospital",
            }
            &
            scene_concepts
        )
        and (
            {
                "forensics",
                "evidence",
                "investigation",
                "crime_scene",
            }
            &
            scene_concepts
        )
    ):

        penalty += 120

        reasons.append(
            "FALSE_MEDICINE_ASSOCIATION"
        )


    generic_hits = term_hits(
        candidate_value,
        GENERIC_LIFESTYLE,
    )


    if (
        generic_hits
        and (
            scene_concepts
            &
            CRITICAL_CONCEPTS
        )
    ):

        penalty += 65

        reasons.append(
            "GENERIC_LIFESTYLE"
        )


    if (
        scene_concepts
        &
        CRITICAL_CONCEPTS
        and candidate_concepts
        and not concept_overlap
        and not geo_bad
    ):

        penalty += 28

        reasons.append(
            "CONCEPT_MISMATCH"
        )


    avoid_hits = term_hits(
        candidate_value,
        avoid_terms(
            scene
        ),
    )


    if avoid_hits:

        penalty += 140

        reasons.append(
            "AVOID_HIT"
        )


    width, height = dimensions(
        candidate
    )


    if (
        width
        and height
    ):

        minimum = min(
            width,
            height,
        )

        maximum = max(
            width,
            height,
        )


        if (
            minimum < 480
            or maximum < 720
        ):

            penalty += 80

            reasons.append(
                "LOW_RESOLUTION"
            )

        elif (
            minimum >= 720
            and maximum >= 1280
        ):

            bonus += 10


        if height > width:

            bonus += 4


    current_provider = provider(
        candidate
    )

    current_group = source_group(
        candidate
    )

    current_type = media_type(
        candidate
    )

    current_key = candidate_key(
        candidate
    )


    providers = list(
        state.get(
            "providers",
            [],
        )
        or []
    )

    groups = list(
        state.get(
            "groups",
            [],
        )
        or []
    )

    types = list(
        state.get(
            "types",
            [],
        )
        or []
    )

    keys = list(
        state.get(
            "keys",
            [],
        )
        or []
    )


    if current_key in keys:

        penalty += 180

        reasons.append(
            "EXACT_REPEAT"
        )


    if providers:

        repeat = sum(
            1
            for item in providers[
                -4:
            ]
            if norm(item)
            ==
            current_provider
        )

        penalty += min(
            60,
            repeat * 16,
        )


        if (
            norm(
                providers[-1]
            )
            ==
            current_provider
        ):

            penalty += 18


    if groups:

        repeat = sum(
            1
            for item in groups[
                -4:
            ]
            if norm(item)
            ==
            current_group
        )

        penalty += min(
            50,
            repeat * 12,
        )


    if (
        len(types) >= 2
        and current_type
        !=
        "unknown"
        and types[-1]
        ==
        current_type
        and types[-2]
        ==
        current_type
    ):

        penalty += 10


    if current_type == "video":

        bonus += 3


    effective = (
        base
        +
        bonus
        -
        penalty
    )


    return {

        "candidate":
            candidate,

        "base":
            base,

        "effective":
            effective,

        "bonus":
            bonus,

        "penalty":
            penalty,

        "must_tier":
            tier,

        "hard_mismatch":
            bool(
                geo_bad
            ),

        "hard_reason":
            (
                geo_reason
                if geo_bad
                else ""
            ),

        "semantic_overlap":
            sorted(
                concept_overlap
            ),

        "token_overlap":
            token_overlap,

        "geo_scene":
            sorted(
                geo_hits(
                    scene_value
                )
            ),

        "geo_candidate":
            sorted(
                geo_hits(
                    candidate_value
                )
            ),

        "provider":
            current_provider,

        "source_group":
            current_group,

        "media_type":
            current_type,

        "key":
            current_key,

        "reasons":
            reasons,
    }


def rerank(
    candidates,
    scene,
    state=None,
):

    scored = [
        score_candidate(
            candidate,
            scene,
            state,
        )
        for candidate in (
            candidates
            or []
        )
    ]


    scored.sort(
        key=lambda item: (
            not item[
                "hard_mismatch"
            ],
            item[
                "must_tier"
            ],
            item[
                "effective"
            ],
        ),
        reverse=True,
    )


    return [
        item[
            "candidate"
        ]
        for item in scored
    ]


def choose_best(
    candidates,
    scene,
    state=None,
):

    ranked = rerank(
        candidates,
        scene,
        state,
    )

    if not ranked:
        return None

    return ranked[
        0
    ]


def needs_rescue(
    candidate,
    scene,
    state=None,
):

    if candidate is None:
        return True

    result = score_candidate(
        candidate,
        scene,
        state,
    )

    return (
        result[
            "hard_mismatch"
        ]
        or
        result[
            "must_tier"
        ]
        <
        2
        or
        result[
            "effective"
        ]
        <
        75
    )


TRANSLATE = {

    "apartamento":
        "apartment",

    "predio":
        "building",

    "edificio":
        "building",

    "policia":
        "police",

    "policial":
        "police",

    "investigacao":
        "investigation",

    "laudo":
        "forensic report",

    "pericia":
        "forensic",

    "evidencia":
        "evidence",

    "indicio":
        "evidence",

    "tribunal":
        "courthouse",

    "julgamento":
        "trial",

    "prisao":
        "prison",

    "incendio":
        "fire",

    "aviao":
        "aircraft",

    "navio":
        "ship",

    "floresta":
        "forest",

    "oceano":
        "ocean",

    "tempestade":
        "storm",

    "computador":
        "computer",

    "tecnologia":
        "technology",

    "laboratorio":
        "laboratory",

    "espaco":
        "space",

    "foguete":
        "rocket",

    "dinheiro":
        "money",

    "guerra":
        "war",

    "militar":
        "military",

    "casa":
        "house",

    "quarto":
        "room",

    "documento":
        "document",

    "noticia":
        "news",
}


def translate_query(value):

    return " ".join(
        TRANSLATE.get(
            token,
            token,
        )
        for token in norm(
            value
        ).split()
    )


def rescue_queries(
    query,
    must_have=None,
    max_extra=2,
):

    query = norm(
        query
    )


    must = [
        norm(
            item
        )
        for item in flatten(
            must_have
            or []
        )
        if norm(
            item
        )
    ]


    base = translate_query(
        query
    )


    must_query = " ".join(
        translate_query(
            item
        )
        for item in must
    )


    variants = []


    proposals = (

        f"{must_query} {base}",

        (
            f"{base} "
            f"documentary evidence "
            f"{must_query}"
        ),

        (
            f"{must_query} "
            f"realistic location "
            f"{base}"
        ),
    )


    for proposal in proposals:

        proposal = " ".join(
            proposal.split()
        )

        if (
            proposal
            and norm(
                proposal
            )
            !=
            query
            and proposal
            not in variants
        ):

            variants.append(
                proposal
            )


    return variants[
        :max(
            0,
            int(
                max_extra
            ),
        )
    ]


def note_success(
    state,
    candidate,
):

    values = (

        (
            "providers",
            provider(
                candidate
            ),
        ),

        (
            "groups",
            source_group(
                candidate
            ),
        ),

        (
            "types",
            media_type(
                candidate
            ),
        ),

        (
            "keys",
            candidate_key(
                candidate
            ),
        ),
    )


    for field, value in values:

        state.setdefault(
            field,
            [],
        ).append(
            value
        )


        if len(
            state[
                field
            ]
        ) > 12:

            del state[
                field
            ][
                :-12
            ]


def self_test():

    state = {

        "providers": [
            "pixabay",
            "pixabay",
        ],

        "groups": [],

        "types": [],

        "keys": [],
    }


    scene = {

        "texto":
            (
                "Investigação em "
                "apartamento na cidade "
                "de São Paulo"
            ),

        "must_have": [
            "apartamento",
            "São Paulo",
        ],

        "location":
            "São Paulo Brazil",
    }


    wrong = {

        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "Empire State Building "
                "New York"
            ),

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }


    correct = {

        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "Apartment building "
                "Sao Paulo Brazil"
            ),

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    a = score_candidate(
        wrong,
        scene,
        state,
    )

    b = score_candidate(
        correct,
        scene,
        state,
    )


    assert (
        a[
            "hard_mismatch"
        ]
        is True
    ), a


    assert (
        b[
            "hard_mismatch"
        ]
        is False
    ), b


    assert (
        b[
            "effective"
        ]
        >
        a[
            "effective"
        ]
    ), (
        a,
        b,
    )


    forensic_scene = {

        "texto":
            (
                "Laudo pericial encontrou "
                "evidências na cena do crime"
            ),

        "must_have": [
            "forensic",
            "evidence",
        ],
    }


    pills = {

        "title":
            "pills medication on table",

        "provider":
            "pexels",

        "score":
            180,

        "must":
            "1/2",
    }


    forensic = {

        "title":
            (
                "forensic evidence "
                "report documents"
            ),

        "provider":
            "wikimedia",

        "score":
            120,

        "must":
            "1/2",
    }


    assert (
        score_candidate(
            forensic,
            forensic_scene,
            {},
        )[
            "effective"
        ]
        >
        score_candidate(
            pills,
            forensic_scene,
            {},
        )[
            "effective"
        ]
    )


    query_leak = {

        "title":
            "random smiling woman",

        "query":
            (
                "police investigation "
                "sao paulo"
            ),

        "provider":
            "pixabay",

        "score":
            150,
    }


    assert (
        "sao_paulo"
        not in
        geo_hits(
            candidate_text(
                query_leak
            )
        )
    )


    low = {

        "title":
            "police investigation",

        "width":
            320,

        "height":
            240,

        "score":
            150,
    }


    high = {

        "title":
            "police investigation",

        "width":
            1080,

        "height":
            1920,

        "score":
            150,
    }


    assert (
        score_candidate(
            high,
            {
                "texto":
                    "police investigation"
            },
            {},
        )[
            "effective"
        ]
        >
        score_candidate(
            low,
            {
                "texto":
                    "police investigation"
            },
            {},
        )[
            "effective"
        ]
    )


    print(
        "VQE5_SELF_TEST=PASS"
    )

    print(
        "GEO_HARD_MISMATCH=PASS"
    )

    print(
        "FALSE_MEDICINE_GUARD=PASS"
    )

    print(
        "QUERY_LEAK_GUARD=PASS"
    )

    print(
        "RESOLUTION_GUARD=PASS"
    )


if __name__ == "__main__":

    self_test()

#!/usr/bin/env python3

import math
import re
import unicodedata
from urllib.parse import urlparse


# ============================================================
# NORMALIZATION
# ============================================================

STOP = {
    "a","ao","aos","as","da","das","de","do","dos","e","em",
    "na","nas","no","nos","o","os","para","por","que","se",
    "um","uma","uns","umas","com","como","pela","pelo",
    "the","a","an","and","at","by","for","from","in","of",
    "on","or","to","with","is","was","were","this","that",
}


def norm(value):
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = value.casefold()

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def tokens(value):
    return {
        token
        for token in norm(value).split()
        if (
            token
            and token not in STOP
            and (
                len(token) >= 2
                or token.isdigit()
            )
        )
    }


def phrase_in(text, phrase):
    t = f" {norm(text)} "
    p = norm(phrase)

    if not p:
        return False

    return f" {p} " in t


# ============================================================
# GENERIC OBJECT ADAPTER
# ============================================================

def objget(obj, key, default=None):

    if obj is None:
        return default

    if isinstance(
        key,
        (list, tuple, set),
    ):
        for name in key:
            value = objget(
                obj,
                name,
                None,
            )

            if value is not None:
                return value

        return default

    if not isinstance(key, str):
        try:
            key = str(key)
        except Exception:
            return default

    if isinstance(obj, dict):

        if key in obj:
            return obj[key]

        wanted = key.casefold()

        for existing, value in obj.items():

            if (
                isinstance(existing, str)
                and existing.casefold() == wanted
            ):
                return value

        return default

    try:
        return getattr(
            obj,
            key,
            default,
        )
    except Exception:
        return default


def number(value, default=0.0):

    if value is None:
        return default

    try:
        return float(value)
    except Exception:
        pass

    try:
        match = re.search(
            r"-?\d+(?:[.,]\d+)?",
            str(value),
        )

        if match:
            return float(
                match.group(0).replace(",", ".")
            )
    except Exception:
        pass

    return default


# ============================================================
# CANDIDATE / SCENE TEXT
# ============================================================

CANDIDATE_FIELDS = (
    "title",
    "name",
    "description",
    "caption",
    "alt",
    "alt_text",
    "tags",
    "keywords",
    "filename",
    "provider",
    "source_group",
    "category",
)

SCENE_FIELDS = (
    "texto",
    "text",
    "scene_text",
    "visual_query",
    "busca",
    "query",
    "must_have",
    "location",
    "local",
    "visual_mode",
)


def _flatten_text(value):

    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(
        value,
        (list, tuple, set),
    ):
        out = []

        for item in value:
            out.extend(
                _flatten_text(item)
            )

        return out

    if isinstance(value, dict):
        out = []

        for item in value.values():
            out.extend(
                _flatten_text(item)
            )

        return out

    return [str(value)]


def candidate_text(candidate):

    if candidate is None:
        return ""

    if isinstance(candidate, str):
        return norm(candidate)

    parts = []

    for field in CANDIDATE_FIELDS:
        value = objget(
            candidate,
            field,
            None,
        )

        parts.extend(
            _flatten_text(value)
        )

    for nested_name in (
        "metadata",
        "meta",
        "source_metadata",
        "provenance",
    ):
        nested = objget(
            candidate,
            nested_name,
            None,
        )

        if isinstance(nested, dict):
            for field in CANDIDATE_FIELDS:
                parts.extend(
                    _flatten_text(
                        nested.get(field)
                    )
                )

    # IMPORTANTE:
    # query/search_query não entram como evidência do candidato.
    return norm(
        " ".join(parts)
    )


def scene_text(scene):

    if scene is None:
        return ""

    if isinstance(scene, str):
        return norm(scene)

    parts = []

    for field in SCENE_FIELDS:
        parts.extend(
            _flatten_text(
                objget(
                    scene,
                    field,
                    None,
                )
            )
        )

    return norm(
        " ".join(parts)
    )


# ============================================================
# PROVIDER / TYPE
# ============================================================

def provider(candidate):

    for key in (
        "provider",
        "source",
        "site",
        "origin",
        "platform",
    ):
        value = objget(
            candidate,
            key,
            None,
        )

        if value:
            p = norm(value)

            if "pixabay" in p:
                return "pixabay"

            if "pexels" in p:
                return "pexels"

            if "wikimedia" in p:
                return "wikimedia"

            if "coverr" in p:
                return "coverr"

            return p

    url = (
        objget(candidate, "source_url", "")
        or objget(candidate, "url", "")
    )

    if url:
        host = urlparse(
            str(url)
        ).netloc.casefold()

        for p in (
            "pixabay",
            "pexels",
            "wikimedia",
            "coverr",
        ):
            if p in host:
                return p

    return "unknown"


def source_group(candidate):

    value = objget(
        candidate,
        [
            "source_group",
            "group",
            "collection",
            "domain",
        ],
        None,
    )

    if value:
        return norm(value)

    url = (
        objget(candidate, "source_url", "")
        or objget(candidate, "url", "")
    )

    if url:
        host = urlparse(
            str(url)
        ).netloc.casefold()

        if host:
            return host.removeprefix("www.")

    return provider(candidate)


def media_type(candidate):

    value = norm(
        objget(
            candidate,
            [
                "media_type",
                "tipo",
                "type",
                "kind",
            ],
            "",
        )
    )

    if any(
        x in value
        for x in (
            "video",
            "movie",
            "motion",
            "clip",
        )
    ):
        return "video"

    if any(
        x in value
        for x in (
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
            [
                "local_path",
                "path",
                "url",
            ],
            "",
        )
    ).casefold()

    if path.endswith(
        (".mp4",".mov",".webm",".mkv")
    ):
        return "video"

    if path.endswith(
        (".jpg",".jpeg",".png",".webp")
    ):
        return "photo"

    return "unknown"


def candidate_key(candidate):

    for field in (
        "sha256",
        "id",
        "asset_id",
        "video_id",
        "photo_id",
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

        if value:
            return (
                f"{provider(candidate)}:"
                f"{norm(value)}"
            )

    return (
        f"{provider(candidate)}:"
        f"{media_type(candidate)}:"
        f"{candidate_text(candidate)}"
    )


def base_score(candidate):

    return number(
        objget(
            candidate,
            [
                "score",
                "base_score",
                "quality_score",
                "rank_score",
                "semantic_score",
                "relevance_score",
            ],
            0,
        ),
        0,
    )


# ============================================================
# SEMANTIC ONTOLOGY
# ============================================================

CONCEPTS = {

    "person": (
        "person","people","man","woman",
        "pessoa","pessoas","homem","mulher",
    ),

    "child": (
        "child","children","kid","girl","boy",
        "daughter","son","crianca","menina",
        "menino","filha","filho",
    ),

    "family": (
        "family","father","mother","parents",
        "familia","pai","mae",
    ),

    "apartment": (
        "apartment","condominium","condo",
        "apartamento","condominio",
    ),

    "building": (
        "building","facade","tower",
        "predio","edificio","fachada",
    ),

    "room": (
        "room","bedroom","interior",
        "quarto","sala",
    ),

    "city": (
        "city","urban","skyline","downtown",
        "cidade","urbano",
    ),

    "street": (
        "street","road","avenue","traffic",
        "rua","estrada","avenida","transito",
    ),

    "police": (
        "police","police officer","detective",
        "policia","policial","delegacia",
    ),

    "investigation": (
        "investigation","investigator",
        "detective","inquiry",
        "investigacao","investigador","apuracao",
    ),

    "crime_scene": (
        "crime scene","scene investigation",
        "cena do crime","local do crime",
    ),

    "evidence": (
        "evidence","clue","proof",
        "evidencia","indicio","indicios",
        "prova","vestigio",
    ),

    "forensics": (
        "forensic","forensics","autopsy",
        "pericia","pericial","laudo","necropsia",
    ),

    "court": (
        "court","courtroom","courthouse",
        "judge","trial",
        "tribunal","forum","juiz","julgamento",
    ),

    "prison": (
        "prison","jail","cell",
        "prisao","cadeia","cela",
    ),

    "document": (
        "document","report","records","file",
        "documento","relatorio","arquivo",
    ),

    "news": (
        "news","newspaper","reporter",
        "headline","journalist",
        "noticia","jornal","manchete",
    ),

    "hospital": (
        "hospital","ambulance","doctor",
        "emergency","medical",
        "ambulancia","medico","emergencia",
    ),

    "medicine": (
        "medicine","medication","pill","pills",
        "tablet","drug","pharmacy",
        "remedio","medicamento","comprimido",
    ),

    "laboratory": (
        "laboratory","scientist","microscope",
        "laboratorio","cientista","microscopio",
    ),

    "technology": (
        "technology","computer","digital","data",
        "tecnologia","computador","dados",
    ),

    "space": (
        "space","planet","moon","astronaut",
        "espaco","planeta","lua","astronauta",
    ),

    "aircraft": (
        "aircraft","airplane","plane",
        "aviation","aviao","aeronave",
    ),

    "car": (
        "car","vehicle","automobile",
        "carro","veiculo",
    ),

    "ship": (
        "ship","boat","vessel",
        "navio","barco","embarcacao",
    ),

    "forest": (
        "forest","woods","trees",
        "floresta","mata","arvores",
    ),

    "ocean": (
        "ocean","sea","underwater",
        "oceano","mar","subaquatico",
    ),

    "storm": (
        "storm","hurricane","tornado",
        "tempestade","furacao",
    ),

    "fire": (
        "fire","flame","smoke","burning",
        "incendio","chama","fumaca",
    ),

    "money": (
        "money","cash","currency","banknote",
        "dinheiro","moeda","cedula",
    ),

    "business": (
        "business","company","office",
        "empresa","negocio","escritorio",
    ),

    "military": (
        "military","soldier","army","troops",
        "militar","soldado","exercito",
    ),

    "war": (
        "war","battle","combat","conflict",
        "guerra","batalha","combate","conflito",
    ),

    "abstract": (
        "abstract","background","texture","pattern",
        "abstrato","fundo","textura","padrao",
    ),
}


def concept_hits(text):

    hits = set()

    for concept, aliases in CONCEPTS.items():

        for alias in aliases:

            if phrase_in(
                text,
                alias,
            ):
                hits.add(concept)
                break

    return hits


# ============================================================
# GEOGRAPHY
# ============================================================

GEO_ALIASES = {

    "brazil": (
        "brazil","brasil","brazilian","brasileiro",
    ),

    "sao_paulo": (
        "sao paulo","avenida paulista",
        "ibirapuera","paulista",
    ),

    "rio_de_janeiro": (
        "rio de janeiro","copacabana","ipanema",
        "cristo redentor","christ the redeemer",
        "pao de acucar","sugarloaf",
    ),

    "usa": (
        "united states","united states of america",
        "usa","american",
    ),

    "new_york": (
        "new york","new york city","nyc",
        "manhattan","brooklyn","queens",
        "empire state building","times square",
        "statue of liberty","central park",
    ),

    "los_angeles": (
        "los angeles","hollywood",
        "beverly hills","santa monica",
    ),

    "united_kingdom": (
        "united kingdom","great britain",
        "britain","england","british",
    ),

    "london": (
        "london","big ben","westminster",
        "tower bridge","buckingham palace",
    ),

    "france": (
        "france","french","franca",
    ),

    "paris": (
        "paris","eiffel tower","louvre",
    ),

    "italy": (
        "italy","italian","italia",
    ),

    "rome": (
        "rome","roma","colosseum","coliseu",
        "vatican","vaticano",
    ),

    "japan": (
        "japan","japanese","japao",
    ),

    "tokyo": (
        "tokyo","toquio","shibuya","shinjuku",
    ),

    "china": (
        "china","chinese","beijing","pequim",
        "shanghai","xangai",
    ),

    "russia": (
        "russia","russian","moscow","moscou",
    ),

    "ukraine": (
        "ukraine","ukrainian","ucrania","kyiv","kiev",
    ),

    "argentina": (
        "argentina","buenos aires",
    ),

    "mexico": (
        "mexico","mexico city","cidade do mexico",
    ),

    "canada": (
        "canada","toronto","vancouver","montreal",
    ),

    "australia": (
        "australia","sydney","melbourne",
    ),

    "india": (
        "india","new delhi","delhi","mumbai",
    ),

    "south_korea": (
        "south korea","coreia do sul","seoul","seul",
    ),

    "egypt": (
        "egypt","egito","cairo","giza",
        "pyramids of giza",
    ),
}


GEO_PARENT = {
    "sao_paulo": "brazil",
    "rio_de_janeiro": "brazil",

    "new_york": "usa",
    "los_angeles": "usa",

    "london": "united_kingdom",

    "paris": "france",

    "rome": "italy",

    "tokyo": "japan",
}


COUNTRY_GEO = {
    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "japan",
    "china",
    "russia",
    "ukraine",
    "argentina",
    "mexico",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}


SPECIFIC_GEO = set(
    GEO_PARENT
)


def geo_hits(text):

    result = set()

    for group, aliases in GEO_ALIASES.items():

        for alias in aliases:

            if phrase_in(
                text,
                alias,
            ):
                result.add(group)

                parent = GEO_PARENT.get(
                    group
                )

                if parent:
                    result.add(parent)

                break

    return result


def geo_conflict(scene_geo, candidate_geo):

    scene_geo = set(scene_geo or ())
    candidate_geo = set(candidate_geo or ())

    if not scene_geo or not candidate_geo:
        return False

    scene_countries = {
        GEO_PARENT.get(x, x)
        for x in scene_geo
        if (
            x in COUNTRY_GEO
            or x in GEO_PARENT
        )
    }

    candidate_countries = {
        GEO_PARENT.get(x, x)
        for x in candidate_geo
        if (
            x in COUNTRY_GEO
            or x in GEO_PARENT
        )
    }

    if (
        scene_countries
        and candidate_countries
        and scene_countries.isdisjoint(
            candidate_countries
        )
    ):
        return True

    scene_specific = (
        scene_geo & SPECIFIC_GEO
    )

    candidate_specific = (
        candidate_geo & SPECIFIC_GEO
    )

    if (
        scene_specific
        and candidate_specific
        and scene_specific.isdisjoint(
            candidate_specific
        )
    ):
        return True

    return False


# ============================================================
# FALSE ASSOCIATIONS / GENERIC STOCK
# ============================================================

GENERIC_LIFESTYLE = {
    "lifestyle","relaxing","relax","smiling",
    "happy","casual","fashion","beauty",
    "wellness","leisure","vacation","coffee",
    "cafe","shopping","selfie","influencer",
    "posing","portrait","model","romantic",
    "dating","relaxando","sorrindo","feliz",
    "moda","beleza","lazer","ferias",
    "compras","retrato","modelo",
}

MEDICINE_TERMS = {
    "pill","pills","medicine","medication",
    "drug","drugs","tablet","tablets",
    "capsule","capsules","pharmacy",
    "prescription","syringe","injection",
    "remedio","remedios","medicamento",
    "medicamentos","comprimido","comprimidos",
    "capsula","farmacia","seringa","injecao",
}

ABSTRACT_TERMS = {
    "abstract","background","texture",
    "pattern","wallpaper","static",
    "abstrato","fundo","textura","padrao",
}


def term_hits(text, vocabulary):

    return {
        term
        for term in vocabulary
        if phrase_in(
            text,
            term,
        )
    }


DOCUMENTARY_CONCEPTS = {
    "police",
    "investigation",
    "crime_scene",
    "evidence",
    "forensics",
    "court",
    "prison",
    "document",
    "news",
    "hospital",
    "laboratory",
    "military",
    "war",
}


# ============================================================
# MUST / AVOID
# ============================================================

def scene_must(scene):

    value = objget(
        scene,
        [
            "must_have",
            "must",
        ],
        [],
    )

    if value is None:
        return []

    if isinstance(value, str):
        return [
            value
        ]

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            str(x)
            for x in value
            if str(x).strip()
        ]

    return []


def scene_avoid(scene):

    value = objget(
        scene,
        [
            "avoid",
            "avoid_terms",
        ],
        [],
    )

    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            str(x)
            for x in value
            if str(x).strip()
        ]

    return []


def reported_must(candidate):

    value = objget(
        candidate,
        [
            "must",
            "must_coverage",
            "must_score",
            "must_tier",
        ],
        None,
    )

    if value is None:
        return None

    if isinstance(value, str):

        match = re.search(
            r"(\d+)\s*/\s*(\d+)",
            value,
        )

        if match:
            hit = int(match.group(1))
            total = max(
                1,
                int(match.group(2)),
            )

            ratio = hit / total

            if ratio >= 0.99:
                tier = 2
            elif ratio >= 0.45:
                tier = 1
            else:
                tier = 0

            return {
                "hits": hit,
                "total": total,
                "ratio": ratio,
                "tier": tier,
                "source": "reported",
            }

    n = number(
        value,
        None,
    )

    if n is None:
        return None

    if 0 <= n <= 1:

        if n >= 0.90:
            tier = 2
        elif n >= 0.45:
            tier = 1
        else:
            tier = 0

        return {
            "hits": tier,
            "total": 2,
            "ratio": n,
            "tier": tier,
            "source": "reported",
        }

    tier = (
        2 if n >= 2
        else 1 if n >= 1
        else 0
    )

    return {
        "hits": tier,
        "total": 2,
        "ratio": tier / 2,
        "tier": tier,
        "source": "reported",
    }


def semantic_must(candidate, scene):

    must = scene_must(
        scene
    )

    if not must:
        return {
            "hits": 0,
            "total": 0,
            "ratio": 0,
            "tier": 0,
            "source": "semantic",
        }

    ctext = candidate_text(
        candidate
    )

    cconcepts = concept_hits(
        ctext
    )

    cgeo = geo_hits(
        ctext
    )

    hits = 0

    for item in must:

        item_text = norm(
            item
        )

        direct = phrase_in(
            ctext,
            item_text,
        )

        concept_match = bool(
            concept_hits(
                item_text
            )
            &
            cconcepts
        )

        geo_match = bool(
            geo_hits(
                item_text
            )
            &
            cgeo
        )

        if (
            direct
            or concept_match
            or geo_match
        ):
            hits += 1

    total = len(must)

    ratio = (
        hits / total
        if total
        else 0
    )

    if ratio >= 0.99:
        tier = 2
    elif ratio >= 0.45:
        tier = 1
    else:
        tier = 0

    return {
        "hits": hits,
        "total": total,
        "ratio": ratio,
        "tier": tier,
        "source": "semantic",
    }


def must_info(candidate, scene):

    semantic = semantic_must(
        candidate,
        scene,
    )

    reported = reported_must(
        candidate
    )

    if reported is None:
        return semantic

    # Se temos MUST real da cena,
    # combinamos sem permitir que o metadata
    # apague uma evidência semântica melhor.
    if semantic["total"]:

        if semantic["tier"] >= reported["tier"]:
            return semantic

    return reported


def avoid_hits(candidate, scene):

    ctext = candidate_text(
        candidate
    )

    return [
        item
        for item in scene_avoid(scene)
        if phrase_in(
            ctext,
            item,
        )
    ]


# ============================================================
# RESOLUTION
# ============================================================

def resolution(candidate):

    width = int(
        number(
            objget(
                candidate,
                ["width","largura"],
                0,
            ),
            0,
        )
    )

    height = int(
        number(
            objget(
                candidate,
                ["height","altura"],
                0,
            ),
            0,
        )
    )

    return width, height


def resolution_bonus(candidate):

    width, height = resolution(
        candidate
    )

    if not width or not height:
        return 0.0

    smallest = min(
        width,
        height,
    )

    largest = max(
        width,
        height,
    )

    bonus = 0.0

    if largest >= 1920:
        bonus += 12

    elif largest >= 1280:
        bonus += 7

    elif largest >= 960:
        bonus += 2

    else:
        bonus -= 25

    if smallest < 480:
        bonus -= 30

    elif smallest < 720:
        bonus -= 10

    # Portrait é útil para Shorts,
    # mas landscape continua válido.
    if height > width:
        bonus += 5

    return bonus


# ============================================================
# FLATTEN / DEDUP
# ============================================================

def flatten_candidates(value):

    result = []

    def walk(item):

        if item is None:
            return

        if isinstance(
            item,
            (list, tuple, set),
        ):
            for child in item:
                walk(child)

            return

        if isinstance(item, dict):

            candidate_fields = {
                "url",
                "source_url",
                "title",
                "provider",
                "tipo",
                "type",
                "score",
                "id",
                "local_path",
            }

            if (
                candidate_fields
                &
                set(item.keys())
            ):
                result.append(item)
                return

            for child in item.values():
                walk(child)

            return

        result.append(item)

    walk(value)

    return result


def dedupe_candidates(items):

    out = []
    seen = set()

    for candidate in items:

        key = candidate_key(
            candidate
        )

        if key in seen:
            continue

        seen.add(key)
        out.append(candidate)

    return out

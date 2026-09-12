
# SHORTAUTOPRO VSE4 GLOBAL FOUNDATION V4.1.2
#
# Semantic safety foundation.
# Does not mutate candidates or execute network/render.


import os

import json

import inspect


ROOT = os.path.expanduser(
    "~/ShortAutoPro"
)


STOP = {

    # Português
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "entre",
    "era",
    "essa",
    "esse",
    "esta",
    "este",
    "foi",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "por",
    "que",
    "se",
    "sem",
    "um",
    "uma",
    "uns",
    "umas",

    # English
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


GENERIC_LIFESTYLE = {

    "lifestyle",
    "relaxing",
    "relax",
    "smiling",
    "happy",
    "casual",
    "fashion",
    "beauty",
    "wellness",
    "leisure",
    "vacation",
    "coffee",
    "cafe",
    "shopping",
    "bed",
    "bedroom",
    "sofa",
    "couch",
    "selfie",
    "influencer",
    "posing",
    "portrait",
    "model",
    "romantic",
    "couple",
    "dating",

    "estilo de vida",
    "relaxando",
    "sorrindo",
    "feliz",
    "casual",
    "moda",
    "beleza",
    "bem estar",
    "lazer",
    "ferias",
    "cafe",
    "compras",
    "cama",
    "quarto",
    "sofa",
    "retrato",
    "modelo",
    "casal",
}


MEDICINE_TERMS = {

    "pill",
    "pills",
    "medicine",
    "medication",
    "drug",
    "drugs",
    "tablet",
    "tablets",
    "capsule",
    "capsules",
    "pharmacy",
    "pharmaceutical",
    "prescription",
    "syringe",
    "injection",

    "remedio",
    "remedios",
    "medicamento",
    "medicamentos",
    "comprimido",
    "comprimidos",
    "capsula",
    "capsulas",
    "farmacia",
    "farmaceutico",
    "receita",
    "seringa",
    "injecao",
}


GEO_GROUPS = {

    # ========================================================
    # BRAZIL
    # ========================================================

    "brazil": (
        "brazil",
        "brasil",
        "brazilian",
        "brasileiro",
        "brasileira",
        "sao paulo",
        "rio de janeiro",
        "brasilia",
        "salvador",
        "fortaleza",
        "recife",
        "belo horizonte",
        "porto alegre",
        "curitiba",
        "manaus",
        "belem",
        "goiania",
        "imperatriz",
        "maranhao",
    ),

    "sao_paulo": (
        "sao paulo",
        "sp brazil",
        "sp brasil",
        "paulista",
        "avenida paulista",
        "ibirapuera",
    ),

    "rio_de_janeiro": (
        "rio de janeiro",
        "rio brazil",
        "rio brasil",
        "copacabana",
        "ipanema",
        "cristo redentor",
        "christ the redeemer",
        "sugarloaf",
        "pao de acucar",
    ),

    "brasilia": (
        "brasilia",
        "distrito federal",
        "federal district brazil",
    ),


    # ========================================================
    # UNITED STATES
    # ========================================================

    "usa": (
        "united states",
        "united states of america",
        "usa",
        "u s a",
        "american",
        "new york",
        "los angeles",
        "california",
        "florida",
        "texas",
        "chicago",
        "washington dc",
        "miami",
        "boston",
        "las vegas",
        "san francisco",
    ),

    "new_york": (
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
        "liberty island",
    ),

    "los_angeles": (
        "los angeles",
        "hollywood",
        "beverly hills",
        "santa monica",
        "california",
    ),

    "washington_dc": (
        "washington dc",
        "washington d c",
        "white house",
        "capitol hill",
        "us capitol",
    ),


    # ========================================================
    # UNITED KINGDOM
    # ========================================================

    "united_kingdom": (
        "united kingdom",
        "uk",
        "britain",
        "great britain",
        "england",
        "scotland",
        "wales",
        "london",
        "british",
    ),

    "london": (
        "london",
        "big ben",
        "westminster",
        "tower bridge",
        "buckingham palace",
    ),


    # ========================================================
    # FRANCE
    # ========================================================

    "france": (
        "france",
        "french",
        "paris",
        "franca",
        "frances",
    ),

    "paris": (
        "paris",
        "eiffel tower",
        "tour eiffel",
        "louvre",
        "champs elysees",
    ),


    # ========================================================
    # ITALY
    # ========================================================

    "italy": (
        "italy",
        "italian",
        "italia",
        "rome",
        "roma",
        "milan",
        "milano",
        "venice",
        "veneza",
    ),

    "rome": (
        "rome",
        "roma",
        "colosseum",
        "coliseu",
        "vatican",
        "vaticano",
    ),


    # ========================================================
    # GERMANY
    # ========================================================

    "germany": (
        "germany",
        "german",
        "alemanha",
        "berlin",
        "berlim",
        "munich",
        "munique",
    ),


    # ========================================================
    # SPAIN
    # ========================================================

    "spain": (
        "spain",
        "spanish",
        "espanha",
        "madrid",
        "barcelona",
    ),


    # ========================================================
    # PORTUGAL
    # ========================================================

    "portugal": (
        "portugal",
        "portuguese",
        "lisbon",
        "lisboa",
        "porto portugal",
    ),


    # ========================================================
    # JAPAN
    # ========================================================

    "japan": (
        "japan",
        "japanese",
        "japao",
        "tokyo",
        "toquio",
        "osaka",
        "kyoto",
        "quioto",
    ),

    "tokyo": (
        "tokyo",
        "toquio",
        "shibuya",
        "shinjuku",
        "tokyo tower",
    ),


    # ========================================================
    # CHINA
    # ========================================================

    "china": (
        "china",
        "chinese",
        "beijing",
        "pequim",
        "shanghai",
        "xangai",
        "hong kong",
    ),


    # ========================================================
    # RUSSIA
    # ========================================================

    "russia": (
        "russia",
        "russian",
        "russia federation",
        "moscow",
        "moscou",
        "saint petersburg",
    ),


    # ========================================================
    # UKRAINE
    # ========================================================

    "ukraine": (
        "ukraine",
        "ukrainian",
        "ucrania",
        "kyiv",
        "kiev",
    ),


    # ========================================================
    # MEXICO
    # ========================================================

    "mexico": (
        "mexico",
        "mexican",
        "mexicano",
        "mexico city",
        "cidade do mexico",
    ),


    # ========================================================
    # ARGENTINA
    # ========================================================

    "argentina": (
        "argentina",
        "argentinian",
        "buenos aires",
    ),


    # ========================================================
    # CANADA
    # ========================================================

    "canada": (
        "canada",
        "canadian",
        "toronto",
        "vancouver",
        "montreal",
        "ottawa",
    ),


    # ========================================================
    # AUSTRALIA
    # ========================================================

    "australia": (
        "australia",
        "australian",
        "sydney",
        "melbourne",
        "canberra",
    ),


    # ========================================================
    # INDIA
    # ========================================================

    "india": (
        "india",
        "indian",
        "new delhi",
        "delhi",
        "mumbai",
        "bombay",
    ),


    # ========================================================
    # SOUTH KOREA
    # ========================================================

    "south_korea": (
        "south korea",
        "korea",
        "korean",
        "coreia do sul",
        "seoul",
        "seul",
    ),


    # ========================================================
    # EGYPT
    # ========================================================

    "egypt": (
        "egypt",
        "egyptian",
        "egito",
        "cairo",
        "giza",
        "pyramids of giza",
        "piramides de gize",
    ),
}


# SHORTAUTOPRO VSE4 FOUNDATION V4.1
#
# Compatibility + semantic foundation.
# Fail-open and read-only toward candidate objects.

import re as _vse4_re
import unicodedata as _vse4_unicode
from urllib.parse import urlparse as _vse4_urlparse


CONCEPTS = {

    # ========================================================
    # PEOPLE / HUMAN CONTEXT
    # ========================================================

    "person": (
        "person",
        "people",
        "man",
        "woman",
        "human",
        "pessoa",
        "pessoas",
        "homem",
        "mulher",
    ),

    "child": (
        "child",
        "children",
        "kid",
        "girl",
        "boy",
        "daughter",
        "son",
        "crianca",
        "criancas",
        "menina",
        "menino",
        "filha",
        "filho",
    ),

    "family": (
        "family",
        "father",
        "mother",
        "parents",
        "parent",
        "familia",
        "pai",
        "mae",
        "pais",
    ),

    "crowd": (
        "crowd",
        "audience",
        "protest",
        "protesters",
        "multidao",
        "publico",
        "manifestacao",
    ),


    # ========================================================
    # HOME / BUILDINGS
    # ========================================================

    "home": (
        "home",
        "house",
        "residence",
        "residential",
        "casa",
        "residencia",
    ),

    "apartment": (
        "apartment",
        "flat",
        "condominium",
        "condo",
        "apartamento",
        "condominio",
        "predio residencial",
    ),

    "building": (
        "building",
        "tower",
        "facade",
        "architecture",
        "predio",
        "edificio",
        "fachada",
        "arquitetura",
    ),

    "room": (
        "room",
        "bedroom",
        "living room",
        "interior",
        "quarto",
        "sala",
        "interior",
    ),

    "door": (
        "door",
        "entrance",
        "gate",
        "porta",
        "entrada",
        "portao",
    ),


    # ========================================================
    # CITY / GEOGRAPHY
    # ========================================================

    "city": (
        "city",
        "urban",
        "skyline",
        "downtown",
        "cidade",
        "urbano",
        "centro",
    ),

    "street": (
        "street",
        "road",
        "avenue",
        "traffic",
        "rua",
        "estrada",
        "avenida",
        "transito",
    ),

    "map": (
        "map",
        "location",
        "geography",
        "satellite",
        "mapa",
        "localizacao",
        "geografia",
        "satelite",
    ),


    # ========================================================
    # CRIME / INVESTIGATION
    # ========================================================

    "police": (
        "police",
        "officer",
        "detective",
        "patrol",
        "policia",
        "policial",
        "delegacia",
        "detetive",
    ),

    "investigation": (
        "investigation",
        "investigator",
        "detective",
        "case",
        "inquiry",
        "investigacao",
        "investigador",
        "caso",
        "apuracao",
    ),

    "crime_scene": (
        "crime scene",
        "crime",
        "scene investigation",
        "cena do crime",
        "local do crime",
    ),

    "evidence": (
        "evidence",
        "clue",
        "proof",
        "indicio",
        "indicios",
        "evidencia",
        "prova",
        "vestigio",
    ),

    "forensics": (
        "forensic",
        "forensics",
        "laboratory",
        "analysis",
        "autopsy",
        "pericia",
        "pericial",
        "laudo",
        "laboratorio",
        "necropsia",
    ),

    "crime_tape": (
        "crime tape",
        "police tape",
        "caution tape",
        "fita policial",
        "isolamento policial",
    ),


    # ========================================================
    # JUSTICE
    # ========================================================

    "court": (
        "court",
        "courtroom",
        "courthouse",
        "judge",
        "trial",
        "tribunal",
        "forum",
        "juiz",
        "julgamento",
    ),

    "gavel": (
        "gavel",
        "judge hammer",
        "martelo judicial",
        "martelo do juiz",
    ),

    "prison": (
        "prison",
        "jail",
        "cell",
        "bars",
        "prisao",
        "cadeia",
        "cela",
    ),

    "law": (
        "law",
        "legal",
        "justice",
        "lawsuit",
        "lei",
        "juridico",
        "justica",
        "processo",
    ),


    # ========================================================
    # DOCUMENTARY / INFORMATION
    # ========================================================

    "document": (
        "document",
        "paper",
        "file",
        "report",
        "records",
        "documento",
        "papel",
        "arquivo",
        "relatorio",
    ),

    "news": (
        "news",
        "newspaper",
        "journalist",
        "reporter",
        "headline",
        "noticia",
        "jornal",
        "jornalista",
        "reporter",
        "manchete",
    ),

    "archive": (
        "archive",
        "archival",
        "historic footage",
        "old footage",
        "arquivo historico",
        "imagem de arquivo",
    ),

    "camera": (
        "camera",
        "cctv",
        "security camera",
        "surveillance",
        "camera de seguranca",
        "vigilancia",
    ),

    "phone": (
        "phone",
        "smartphone",
        "telephone",
        "cellphone",
        "celular",
        "telefone",
    ),


    # ========================================================
    # HEALTH / EMERGENCY
    # ========================================================

    "hospital": (
        "hospital",
        "emergency",
        "ambulance",
        "doctor",
        "medical",
        "hospital",
        "emergencia",
        "ambulancia",
        "medico",
    ),

    "medicine": (
        "medicine",
        "medication",
        "pill",
        "pills",
        "tablet",
        "drug",
        "remedio",
        "medicamento",
        "comprimido",
    ),

    "fire": (
        "fire",
        "flame",
        "smoke",
        "burning",
        "incendio",
        "chama",
        "fumaca",
        "queimando",
    ),

    "rescue": (
        "rescue",
        "firefighter",
        "emergency team",
        "salvamento",
        "bombeiro",
        "resgate",
    ),


    # ========================================================
    # VEHICLES / TRANSPORT
    # ========================================================

    "car": (
        "car",
        "vehicle",
        "automobile",
        "carro",
        "veiculo",
        "automovel",
    ),

    "motorcycle": (
        "motorcycle",
        "motorbike",
        "bike",
        "moto",
        "motocicleta",
    ),

    "aircraft": (
        "aircraft",
        "airplane",
        "plane",
        "aviation",
        "aviao",
        "aeronave",
        "aviacao",
    ),

    "ship": (
        "ship",
        "boat",
        "vessel",
        "naval",
        "navio",
        "barco",
        "embarcacao",
    ),

    "train": (
        "train",
        "railway",
        "railroad",
        "trem",
        "ferrovia",
    ),


    # ========================================================
    # NATURE / DISASTER
    # ========================================================

    "forest": (
        "forest",
        "woods",
        "trees",
        "floresta",
        "mata",
        "arvores",
    ),

    "ocean": (
        "ocean",
        "sea",
        "underwater",
        "water",
        "oceano",
        "mar",
        "subaquatico",
        "agua",
    ),

    "storm": (
        "storm",
        "hurricane",
        "tornado",
        "lightning",
        "tempestade",
        "furacao",
        "tornado",
        "raio",
    ),

    "flood": (
        "flood",
        "flooding",
        "enchente",
        "inundacao",
    ),

    "earthquake": (
        "earthquake",
        "seismic",
        "terremoto",
        "sismico",
    ),

    "mountain": (
        "mountain",
        "mountains",
        "cliff",
        "montanha",
        "montanhas",
        "penhasco",
    ),


    # ========================================================
    # TECHNOLOGY / SCIENCE
    # ========================================================

    "computer": (
        "computer",
        "laptop",
        "monitor",
        "screen",
        "computador",
        "notebook",
        "tela",
    ),

    "technology": (
        "technology",
        "digital",
        "network",
        "data",
        "tecnologia",
        "digital",
        "rede",
        "dados",
    ),

    "laboratory": (
        "laboratory",
        "scientist",
        "microscope",
        "research",
        "laboratorio",
        "cientista",
        "microscopio",
        "pesquisa",
    ),

    "space": (
        "space",
        "planet",
        "earth",
        "moon",
        "astronaut",
        "universe",
        "espaco",
        "planeta",
        "terra",
        "lua",
        "astronauta",
        "universo",
    ),

    "rocket": (
        "rocket",
        "launch",
        "spacecraft",
        "foguete",
        "lancamento",
        "nave espacial",
    ),


    # ========================================================
    # MONEY / BUSINESS
    # ========================================================

    "money": (
        "money",
        "cash",
        "currency",
        "banknote",
        "dinheiro",
        "cedula",
        "moeda",
    ),

    "business": (
        "business",
        "office",
        "company",
        "corporate",
        "negocio",
        "empresa",
        "escritorio",
    ),

    "market": (
        "market",
        "stock market",
        "trading",
        "finance",
        "mercado",
        "bolsa",
        "financas",
    ),


    # ========================================================
    # WAR / MILITARY
    # ========================================================

    "military": (
        "military",
        "soldier",
        "army",
        "troops",
        "militar",
        "soldado",
        "exercito",
        "tropas",
    ),

    "war": (
        "war",
        "battle",
        "combat",
        "conflict",
        "guerra",
        "batalha",
        "combate",
        "conflito",
    ),


    # ========================================================
    # MEDIA / GENERIC VISUAL FORMS
    # ========================================================

    "television": (
        "television",
        "tv",
        "broadcast",
        "televisao",
    ),

    "abstract": (
        "abstract",
        "background",
        "texture",
        "pattern",
        "abstrato",
        "fundo",
        "textura",
        "padrao",
    ),
}


def norm(value):

    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = value.casefold()

    value = _vse4_unicode.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        ch
        for ch in value
        if not _vse4_unicode.combining(ch)
    )

    value = _vse4_re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def objget(obj, key, default=None):
    """
    Leitor tolerante para candidatos VSE4.

    Aceita:

        objget(candidate, "width", 0)

    e também aliases:

        objget(
            candidate,
            ["width", "largura"],
            0,
        )

    Para aliases, retorna o primeiro valor encontrado
    que não seja None.

    Funciona com:
    - dict
    - objetos Python
    - list/tuple/set de chaves

    Não modifica o objeto original.
    """

    if obj is None:
        return default


    # --------------------------------------------------------
    # MULTI-KEY / ALIAS MODE
    # --------------------------------------------------------

    if isinstance(
        key,
        (
            list,
            tuple,
            set,
        ),
    ):

        for candidate_key_name in key:

            value = objget(
                obj,
                candidate_key_name,
                None,
            )

            if value is not None:
                return value

        return default


    # --------------------------------------------------------
    # INVALID KEY SAFETY
    # --------------------------------------------------------

    if key is None:
        return default


    # Garante chave utilizável sem quebrar dict.get().
    if not isinstance(
        key,
        str,
    ):

        try:
            key = str(key)
        except Exception:
            return default


    # --------------------------------------------------------
    # DICT
    # --------------------------------------------------------

    if isinstance(
        obj,
        dict,
    ):

        if key in obj:
            return obj[
                key
            ]


        # Compatibilidade case-insensitive.
        wanted = key.casefold()

        for existing_key, value in obj.items():

            if not isinstance(
                existing_key,
                str,
            ):
                continue

            if existing_key.casefold() == wanted:
                return value


        return default


    # --------------------------------------------------------
    # OBJECT ATTRIBUTE
    # --------------------------------------------------------

    try:

        value = getattr(
            obj,
            key,
            default,
        )

        return value

    except Exception:

        return default



def number(value, default=0.0):

    if value is None:
        return default

    if isinstance(value, bool):
        return float(value)

    try:
        return float(value)
    except Exception:
        pass

    try:
        text = str(value).strip().replace(
            ",",
            ".",
        )

        match = _vse4_re.search(
            r"-?\d+(?:\.\d+)?",
            text,
        )

        if match:
            return float(
                match.group(0)
            )

    except Exception:
        pass

    return default


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
            return norm(value)

    url = objget(
        candidate,
        "url",
        "",
    ) or objget(
        candidate,
        "source_url",
        "",
    )

    if url:

        try:
            host = _vse4_urlparse(
                str(url)
            ).netloc.casefold()

            if "pixabay" in host:
                return "pixabay"

            if "pexels" in host:
                return "pexels"

            if "wikimedia" in host:
                return "wikimedia"

            if "coverr" in host:
                return "coverr"

            if "unsplash" in host:
                return "unsplash"

            if host:
                return host

        except Exception:
            pass

    return "unknown"


def source_group(candidate):

    for key in (
        "source_group",
        "group",
        "collection",
        "domain",
        "source_domain",
    ):

        value = objget(
            candidate,
            key,
            None,
        )

        if value:
            return norm(value)

    url = (
        objget(
            candidate,
            "source_url",
            "",
        )
        or
        objget(
            candidate,
            "url",
            "",
        )
    )

    if url:

        try:
            host = _vse4_urlparse(
                str(url)
            ).netloc.casefold()

            host = host.removeprefix(
                "www."
            )

            if host:
                return host

        except Exception:
            pass

    return provider(
        candidate
    )


def media_type(candidate):

    value = ""

    for key in (
        "media_type",
        "type",
        "tipo",
        "kind",
    ):

        candidate_value = objget(
            candidate,
            key,
            None,
        )

        if candidate_value:

            value = norm(
                candidate_value
            )

            break


    if any(
        term in value
        for term in (
            "video",
            "movie",
            "motion",
            "clip",
        )
    ):
        return "video"


    if any(
        term in value
        for term in (
            "foto",
            "photo",
            "image",
            "imagem",
            "picture",
        )
    ):
        return "photo"


    path = (
        objget(
            candidate,
            "local_path",
            "",
        )
        or
        objget(
            candidate,
            "path",
            "",
        )
        or
        objget(
            candidate,
            "url",
            "",
        )
    )

    suffix = str(path).casefold()

    if suffix.endswith(
        (
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
        )
    ):
        return "video"

    if suffix.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    ):
        return "photo"

    return value or "unknown"


def candidate_key(candidate):

    for key in (
        "id",
        "video_id",
        "photo_id",
        "asset_id",
        "sha256",
        "source_url",
        "url",
        "download_url",
        "local_path",
        "path",
    ):

        value = objget(
            candidate,
            key,
            None,
        )

        if value:
            return (
                provider(candidate)
                + ":"
                + norm(value)
            )


    title = (
        objget(
            candidate,
            "title",
            "",
        )
        or
        objget(
            candidate,
            "name",
            "",
        )
        or
        candidate_text(
            candidate
        )
    )

    return (
        provider(candidate)
        + ":"
        + media_type(candidate)
        + ":"
        + norm(title)
    )


def base_score(candidate):

    for key in (
        "score",
        "base_score",
        "quality_score",
        "rank_score",
        "semantic_score",
        "relevance_score",
    ):

        value = objget(
            candidate,
            key,
            None,
        )

        if value is not None:

            result = number(
                value,
                None,
            )

            if result is not None:
                return result

    return 0.0


def must_tier(candidate, scene=None):
    """
    Converte evidência MUST em tier visual:

        0 = nenhum MUST atendido
        1 = cobertura parcial
        2 = cobertura forte/completa

    Entende corretamente:

        "2/2" -> 2
        "1/2" -> 1
        "0/2" -> 0

        "100%" -> 2
        "50%"  -> 1

        must=2 -> 2
        must=1 -> 1
        must=0 -> 0

        must_coverage=1.0 -> 2
        must_coverage=0.5 -> 1

    Nunca promove automaticamente 1/2 para 2/2.
    """

    import re


    def ratio_to_tier(
        numerator,
        denominator,
    ):

        try:
            numerator = float(
                numerator
            )

            denominator = float(
                denominator
            )

        except Exception:
            return None


        if denominator <= 0:
            return None


        ratio = (
            numerator
            /
            denominator
        )


        if ratio >= 0.90:
            return 2

        if ratio >= 0.45:
            return 1

        return 0


    def direct_count_to_tier(
        value
    ):

        try:
            n = float(
                value
            )
        except Exception:
            return None


        if n >= 2:
            return 2

        if n >= 1:
            return 1

        return 0


    fields = (
        "must_tier",
        "must_coverage",
        "must_score",
        "must",
        "must_hits",
    )


    for key in fields:

        value = objget(
            candidate,
            key,
            None,
        )


        if value is None:
            continue


        # ----------------------------------------------------
        # COLLECTION OF HITS
        # ----------------------------------------------------

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            count = len(
                value
            )

            if count >= 2:
                return 2

            if count == 1:
                return 1

            return 0


        # ----------------------------------------------------
        # STRINGS
        # ----------------------------------------------------

        if isinstance(
            value,
            str,
        ):

            text = value.strip().casefold()


            # "1/2", "2 / 2", "2 of 2"
            ratio_match = re.fullmatch(
                r"\s*(\d+(?:\.\d+)?)\s*"
                r"(?:/|of)\s*"
                r"(\d+(?:\.\d+)?)\s*",
                text,
            )


            if ratio_match:

                tier = ratio_to_tier(
                    ratio_match.group(1),
                    ratio_match.group(2),
                )

                if tier is not None:
                    return tier


            # "50%", "100%"
            percent_match = re.fullmatch(
                r"\s*(\d+(?:\.\d+)?)\s*%\s*",
                text,
            )


            if percent_match:

                percentage = float(
                    percent_match.group(1)
                )

                return ratio_to_tier(
                    percentage,
                    100.0,
                )


            # Numeric string.
            try:
                numeric = float(
                    text.replace(
                        ",",
                        ".",
                    )
                )

            except Exception:
                numeric = None


            if numeric is not None:

                # Explicit tier/count fields.
                if key in (
                    "must_tier",
                    "must",
                    "must_hits",
                ):

                    return direct_count_to_tier(
                        numeric
                    )


                # Coverage fields use 0..1 semantics.
                if key in (
                    "must_coverage",
                    "must_score",
                ):

                    if 0.0 <= numeric <= 1.0:

                        if numeric >= 0.90:
                            return 2

                        if numeric >= 0.45:
                            return 1

                        return 0


                    return direct_count_to_tier(
                        numeric
                    )


        # ----------------------------------------------------
        # NUMERIC VALUES
        # ----------------------------------------------------

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ) and not isinstance(
            value,
            bool,
        ):

            numeric = float(
                value
            )


            if key in (
                "must_tier",
                "must",
                "must_hits",
            ):

                return direct_count_to_tier(
                    numeric
                )


            if key in (
                "must_coverage",
                "must_score",
            ):

                if 0.0 <= numeric <= 1.0:

                    if numeric >= 0.90:
                        return 2

                    if numeric >= 0.45:
                        return 1

                    return 0


                return direct_count_to_tier(
                    numeric
                )


    # ========================================================
    # SEMANTIC FALLBACK
    # ========================================================

    if scene is not None:

        scene_text = candidate_text(
            scene
        )

        candidate_txt = candidate_text(
            candidate
        )

        scene_set = tokens(
            scene_text
        )

        candidate_set = tokens(
            candidate_txt
        )

        overlap = (
            scene_set
            &
            candidate_set
        )


        if len(overlap) >= 2:
            return 2


        if len(overlap) == 1:
            return 1


    return 0



def flatten_candidates(value):

    result = []


    def walk(item):

        if item is None:
            return


        if isinstance(
            item,
            (
                list,
                tuple,
                set,
            ),
        ):

            for child in item:
                walk(child)

            return


        if isinstance(
            item,
            dict,
        ):

            candidate_keys = {
                "url",
                "source_url",
                "download_url",
                "title",
                "provider",
                "type",
                "media_type",
                "score",
                "id",
                "local_path",
            }

            if candidate_keys.intersection(
                item.keys()
            ):

                result.append(
                    item
                )

                return


            for child in item.values():
                walk(child)

            return


        result.append(
            item
        )


    walk(value)

    return result




def concept_hits(text):

    t = tokens(text)

    found = set()

    for concept, words in CONCEPTS.items():

        if t & {
            norm(x)
            for x in words
        }:
            found.add(concept)

    return found




def geo_hits(text):

    normalized_text = norm(
        text
    )

    padded = (
        " "
        +
        normalized_text
        +
        " "
    )

    result = set()

    for group, aliases in GEO_GROUPS.items():

        for alias in aliases:

            normalized_alias = norm(
                alias
            )

            if not normalized_alias:
                continue

            needle = (
                " "
                +
                normalized_alias
                +
                " "
            )

            if needle in padded:

                result.add(
                    group
                )

                break

    return result



def context_text(local_ns):

    parts = []

    priority = [
        "busca",
        "query",
        "search_query",
        "termo_busca",
        "must_have",
        "must",
        "texto",
        "text",
        "narracao",
        "narração",
        "descricao",
        "description",
        "cena",
        "scene",
    ]

    for key in priority:

        if key not in local_ns:
            continue

        value = local_ns.get(key)

        if isinstance(value, dict):

            for sub in [
                "texto",
                "text",
                "description",
                "descricao",
                "query",
                "busca",
                "must_have",
            ]:

                if sub in value:
                    parts.append(
                        str(value[sub])
                    )

        elif isinstance(
            value,
            (list, tuple, set),
        ):

            parts.extend(
                str(x)
                for x in value
            )

        elif value is not None:
            parts.append(
                str(value)
            )

    return " ".join(parts)


def scene_number(local_ns):

    for key in [
        "numero",
        "numero_cena",
        "scene_number",
        "scene_idx",
        "idx",
    ]:

        value = local_ns.get(key)

        try:
            n = int(value)

            if 0 <= n <= 99:
                return n

        except Exception:
            pass

    return 0


def resolution_bonus(candidate):

    width = number(
        objget(
            candidate,
            ["width","largura"],
            0,
        ),
        0,
    )

    height = number(
        objget(
            candidate,
            ["height","altura"],
            0,
        ),
        0,
    )

    if not width or not height:
        return 0.0

    pixels = width * height

    if pixels >= 1920 * 1080:
        return 10.0

    if pixels >= 1280 * 720:
        return 5.0

    if pixels < 640 * 360:
        return -20.0

    return 0.0


def load_state(short_id):

    path = (
        ROOT
        / "temp"
        / f"vse4_state_{short_id}.json"
    )

    if not path.exists():
        return {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
            "scenes": {},
        }

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
            "scenes": {},
        }


def save_state(short_id, state):

    path = (
        ROOT
        / "temp"
        / f"vse4_state_{short_id}.json"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        ".tmp"
    )

    tmp.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    tmp.replace(path)




# ============================================================
# SHORTAUTOPRO VSE4
# Candidate semantic text adapter
# ============================================================


def candidate_text(candidate):
    """
    Converte cena/candidato em texto semântico estável.

    Aceita:
    - str
    - bytes
    - dict
    - list/tuple/set
    - objetos Python
    - metadata aninhado

    Não modifica o objeto de origem.
    """

    if candidate is None:
        return ""


    # ========================================================
    # DIRECT STRING
    # ========================================================

    if isinstance(candidate, str):

        return " ".join(
            candidate
            .casefold()
            .strip()
            .split()
        )


    if isinstance(
        candidate,
        bytes,
    ):

        try:

            return " ".join(
                candidate
                .decode(
                    "utf-8",
                    errors="ignore",
                )
                .casefold()
                .strip()
                .split()
            )

        except Exception:

            return ""


    # ========================================================
    # COLLECTION
    # ========================================================

    if isinstance(
        candidate,
        (
            list,
            tuple,
            set,
        ),
    ):

        parts = []

        for item in candidate:

            text = candidate_text(
                item
            )

            if text:
                parts.append(
                    text
                )

        return " ".join(
            parts
        )


    fields = (
        "texto",
        "text",
        "title",
        "name",
        "description",
        "caption",
        "alt",
        "alt_text",
        "visual_query",
        "query",
        "search_query",
        "subject",
        "topic",
        "location",
        "place",
        "city",
        "country",
        "must_have",
        "avoid",
        "tags",
        "keywords",
        "terms",
        "category",
        "provider",
        "source_group",
        "media_type",
        "type",
        "tipo",
        "filename",
    )


    nested_fields = (
        "metadata",
        "meta",
        "source_metadata",
        "provenance",
        "scene",
        "context",
    )


    parts = []


    def add(value):

        if value is None:
            return


        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                parts.append(
                    value
                )

            return


        if isinstance(
            value,
            bytes,
        ):

            try:
                add(
                    value.decode(
                        "utf-8",
                        errors="ignore",
                    )
                )
            except Exception:
                pass

            return


        if isinstance(
            value,
            (
                int,
                float,
                bool,
            ),
        ):

            parts.append(
                str(value)
            )

            return


        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            for item in value:
                add(item)

            return


        if isinstance(
            value,
            dict,
        ):

            for field in fields:

                if field in value:
                    add(
                        value.get(
                            field
                        )
                    )

            for nested in nested_fields:

                if nested in value:
                    add(
                        value.get(
                            nested
                        )
                    )

            return


    # ========================================================
    # DICT
    # ========================================================

    if isinstance(
        candidate,
        dict,
    ):

        for field in fields:

            if field in candidate:
                add(
                    candidate.get(
                        field
                    )
                )


        for nested in nested_fields:

            if nested in candidate:

                add(
                    candidate.get(
                        nested
                    )
                )


    # ========================================================
    # OBJECT
    # ========================================================

    else:

        for field in fields:

            try:

                add(
                    getattr(
                        candidate,
                        field,
                        None,
                    )
                )

            except Exception:

                pass


        for nested in nested_fields:

            try:

                add(
                    getattr(
                        candidate,
                        nested,
                        None,
                    )
                )

            except Exception:

                pass


    # ========================================================
    # DEDUP
    # ========================================================

    clean = []
    seen = set()


    for part in parts:

        part = " ".join(
            str(part)
            .strip()
            .split()
        )

        if not part:
            continue


        key = part.casefold()


        if key in seen:
            continue


        seen.add(
            key
        )

        clean.append(
            part
        )


    return " ".join(
        clean
    ).casefold()











# ============================================================
# SHORTAUTOPRO VSE4
# Semantic Token Engine
# ============================================================

def tokens(value):
    """
    Produz tokens semânticos normalizados para comparação visual.

    Objetivos:
    - português + inglês
    - tolerância a acentos
    - strings, listas, sets e valores simples
    - adequado para interseção de conjuntos
    - preserva nomes, lugares, objetos e números relevantes
    """

    import re
    import unicodedata


    def flatten(obj):

        if obj is None:
            return []

        if isinstance(obj, str):
            return [obj]

        if isinstance(
            obj,
            (
                list,
                tuple,
                set,
            ),
        ):

            out = []

            for item in obj:
                out.extend(
                    flatten(item)
                )

            return out

        if isinstance(obj, dict):

            out = []

            for item in obj.values():
                out.extend(
                    flatten(item)
                )

            return out

        return [
            str(obj)
        ]


    text = " ".join(
        flatten(value)
    ).casefold()


    # Remove acentos:
    # São Paulo -> sao paulo
    normalized = unicodedata.normalize(
        "NFKD",
        text,
    )

    normalized = "".join(
        ch
        for ch in normalized
        if not unicodedata.combining(ch)
    )


    # Mantém letras e números.
    raw = re.findall(
        r"[a-z0-9]+",
        normalized,
    )


    # Stopwords pequenas.
    # Não removemos palavras documentais/importantes.
    stop = {
        # Português
        "a",
        "ao",
        "aos",
        "as",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "para",
        "por",
        "que",
        "se",
        "um",
        "uma",
        "uns",
        "umas",
        "com",
        "como",

        # Inglês
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }


    result = set()

    for token in raw:

        if not token:
            continue

        if token in stop:
            continue

        # Mantém números e palavras >= 2 caracteres.
        if (
            len(token) >= 2
            or token.isdigit()
        ):
            result.add(token)


    return result



def _score_candidate_stage_01(
    candidate,
    scene_text,
    state,
):

    ctext = candidate_text(
        candidate
    )

    scene_tokens = tokens(
        scene_text
    )

    cand_tokens = tokens(
        ctext
    )

    scene_concepts = concept_hits(
        scene_text
    )

    cand_concepts = concept_hits(
        ctext
    )

    direct_overlap = len(
        scene_tokens & cand_tokens
    )

    concept_overlap = len(
        scene_concepts & cand_concepts
    )

    semantic_hits = (
        direct_overlap
        +
        concept_overlap * 2
    )

    # --------------------------------------------------
    # TRUSTED MUST_HAVE VERIFICATION
    # --------------------------------------------------
    # Never trust candidate["must"] as ranking evidence.
    #
    # When the structured scene exposes explicit must_have
    # requirements, verify EACH requirement independently
    # against the candidate itself.
    #
    # Geographic requirements use geo_hits().
    # Semantic requirements use concept_hits().
    # Plain textual requirements require their complete
    # normalized token set to be present.
    #
    # Only when no explicit must_have exists do we use the
    # legacy semantic fallback, with declared "must" removed.

    declared_must = (
        candidate.get("must")
        if isinstance(candidate, dict)
        else None
    )

    explicit_must = []

    if isinstance(scene_text, dict):
        raw_must = scene_text.get(
            "must_have",
            [],
        )

        if isinstance(raw_must, str):
            explicit_must = [
                raw_must
            ]

        elif isinstance(
            raw_must,
            (list, tuple, set),
        ):
            explicit_must = [
                item
                for item in raw_must
                if item is not None
                and str(item).strip()
            ]

    if explicit_must:

        verified_must_hits = 0

        candidate_geo_for_must = geo_hits(
            ctext
        )

        for requirement in explicit_must:

            requirement_text = norm(
                requirement
            )

            if not requirement_text:
                continue

            requirement_geo = geo_hits(
                requirement_text
            )

            matched = False

            # ------------------------------
            # Geographic requirement
            # ------------------------------
            if requirement_geo:

                matched = bool(
                    requirement_geo
                    &
                    candidate_geo_for_must
                )

            # ------------------------------
            # Semantic/textual requirement
            # ------------------------------
            else:

                requirement_concepts = concept_hits(
                    requirement_text
                )

                if (
                    requirement_concepts
                    and
                    (
                        requirement_concepts
                        &
                        cand_concepts
                    )
                ):
                    matched = True

                else:

                    requirement_tokens = tokens(
                        requirement_text
                    )

                    if (
                        requirement_tokens
                        and
                        requirement_tokens.issubset(
                            cand_tokens
                        )
                    ):
                        matched = True

            if matched:
                verified_must_hits += 1

        must = min(
            2,
            verified_must_hits,
        )

    else:

        # Backward-compatible fallback for callers/scenes
        # that do not expose explicit must_have.
        if isinstance(candidate, dict):
            must_candidate = dict(
                candidate
            )
            must_candidate.pop(
                "must",
                None,
            )
        else:
            must_candidate = candidate

        must = must_tier(
            must_candidate,
            scene_text,
        )

    base = base_score(
        candidate
    )

    prov = provider(
        candidate
    )

    mtype = media_type(
        candidate
    )

    group = source_group(
        candidate
    )

    key = candidate_key(
        candidate
    )

    penalty = 0.0
    bonus = 0.0
    hard_mismatch = False
    mismatch_reasons = []


    # -------------------------------------
    # GEOGRAPHIC TRUTH GUARD
    # -------------------------------------

    sg = geo_hits(
        scene_text
    )

    cg = geo_hits(
        ctext
    )

    if (
        len(sg) == 1
        and
        len(cg) == 1
        and
        sg != cg
    ):

        hard_mismatch = True
        penalty += 180.0

        mismatch_reasons.append(
            "GEOGRAPHIC_CONTRADICTION"
        )


    # -------------------------------------
    # SEMANTIC CONTRADICTIONS
    # -------------------------------------

    normalized_candidate = norm(
        ctext
    )

    investigative = bool(
        scene_concepts
        &
        {
            "investigation",
            "forensic",
            "evidence",
            "police",
            "court",
            "death",
        }
    )

    if investigative:

        generic_hits = sum(
            1
            for term in GENERIC_LIFESTYLE
            if norm(term)
            in normalized_candidate
        )

        if generic_hits:
            penalty += (
                generic_hits
                * 22.0
            )

            mismatch_reasons.append(
                "GENERIC_LIFESTYLE"
            )


    if (
        (
            "forensic" in scene_concepts
            or
            "evidence" in scene_concepts
        )
        and
        not (
            tokens(scene_text)
            &
            {
                "medicamento",
                "remedio",
                "droga",
                "toxicologia",
                "medicine",
                "drug",
                "toxicology",
            }
        )
    ):

        if any(
            norm(term)
            in normalized_candidate
            for term in MEDICINE_TERMS
        ):

            penalty += 80.0

            mismatch_reasons.append(
                "UNSUPPORTED_MEDICINE_VISUAL"
            )


    # -------------------------------------
    # DOCUMENTARY / REAL-WORLD VALUE
    # -------------------------------------

    if investigative:

        if (
            "wikimedia" in prov
            and
            semantic_hits >= 1
        ):
            bonus += 28.0

        if "coverr" in prov:
            bonus += 3.0


    # -------------------------------------
    # PROVIDER DIVERSITY
    # -------------------------------------

    providers = list(
        state.get(
            "providers",
            [],
        )
    )

    if providers:

        if providers[-1] == prov:
            penalty += 7.0

        if (
            len(providers) >= 2
            and
            providers[-1] == prov
            and
            providers[-2] == prov
        ):
            penalty += 12.0


    groups = list(
        state.get(
            "groups",
            [],
        )
    )

    if (
        group
        and
        group in groups[-4:]
    ):
        penalty += 15.0


    keys = list(
        state.get(
            "keys",
            [],
        )
    )

    if (
        key
        and
        key in keys
    ):
        penalty += 250.0

        mismatch_reasons.append(
            "EXACT_REPEAT"
        )


    # -------------------------------------
    # MEDIA-TYPE RHYTHM
    # -------------------------------------

    types = list(
        state.get(
            "types",
            [],
        )
    )

    if (
        len(types) >= 3
        and
        types[-3:]
        ==
        [mtype, mtype, mtype]
    ):
        penalty += 8.0


    # Documentary stills work well for
    # evidence/court/document scenes.
    if (
        mtype == "photo"
        and
        scene_concepts
        &
        {
            "document",
            "forensic",
            "court",
            "evidence",
        }
    ):
        bonus += 5.0


    # Motion is useful for generic environment/
    # city/building transitions.
    if (
        mtype == "video"
        and
        scene_concepts
        &
        {
            "building",
            "city",
            "home",
        }
    ):
        bonus += 5.0


    bonus += resolution_bonus(
        candidate
    )


    effective = (
        must * 115.0
        +
        min(
            base,
            300.0,
        ) * 0.22
        +
        semantic_hits * 14.0
        +
        bonus
        -
        penalty
    )


    return {
        "candidate":
            candidate,

        "effective":
            round(
                effective,
                3,
            ),

        "must":
            must,

        "base":
            round(
                base,
                3,
            ),

        "semantic_hits":
            semantic_hits,

        "provider":
            prov,

        "type":
            mtype,

        "group":
            group,

        "key":
            key,

        "hard_mismatch":
            hard_mismatch,

        "mismatch_reasons":
            mismatch_reasons,

        "bonus":
            round(
                bonus,
                3,
            ),

        "penalty":
            round(
                penalty,
                3,
            ),
    }


# SHORTAUTOPRO VSE4 GEO HARD GUARD V4.1.6
#
# Hard mismatch apenas quando existe evidência geográfica
# explícita e contraditória nos dois lados.
#
# Não usa search_query do candidato como prova geográfica,
# porque a query pode descrever o que procuramos e não o
# conteúdo que realmente foi retornado.


_VSE416_COUNTRIES = {
    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "germany",
    "spain",
    "portugal",
    "japan",
    "china",
    "russia",
    "ukraine",
    "mexico",
    "argentina",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}


_VSE416_CITY_PARENT = {

    "sao_paulo":
        "brazil",

    "rio_de_janeiro":
        "brazil",

    "brasilia":
        "brazil",

    "new_york":
        "usa",

    "los_angeles":
        "usa",

    "washington_dc":
        "usa",

    "london":
        "united_kingdom",

    "paris":
        "france",

    "rome":
        "italy",

    "tokyo":
        "japan",
}


def _vse416_add_text(parts, value):

    if value is None:
        return


    if isinstance(
        value,
        str,
    ):

        value = value.strip()

        if value:
            parts.append(
                value
            )

        return


    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        for item in value:

            _vse416_add_text(
                parts,
                item,
            )

        return


    if isinstance(
        value,
        dict,
    ):

        for item in value.values():

            _vse416_add_text(
                parts,
                item,
            )

        return


def _vse416_candidate_geo_text(candidate):
    """
    Extrai somente evidência geográfica forte do asset.

    Deliberadamente NÃO inclui:
    - query
    - search_query
    - visual_query

    Essas informações descrevem a pesquisa, não
    necessariamente a mídia encontrada.
    """

    if candidate is None:
        return ""


    if isinstance(
        candidate,
        str,
    ):

        return candidate


    fields = (
        "title",
        "name",
        "description",
        "caption",
        "alt",
        "alt_text",
        "tags",
        "keywords",
        "subject",
        "topic",
        "category",

        "location",
        "local",
        "city",
        "cidade",
        "country",
        "pais",
        "place",
        "geo",
    )


    parts = []


    if isinstance(
        candidate,
        dict,
    ):

        for field in fields:

            if field in candidate:

                _vse416_add_text(
                    parts,
                    candidate.get(
                        field
                    ),
                )


        # Metadata descritiva pode conter cidade/país.
        for nested_name in (
            "metadata",
            "meta",
            "source_metadata",
            "provenance",
        ):

            nested = candidate.get(
                nested_name
            )

            if not isinstance(
                nested,
                dict,
            ):
                continue


            for field in (
                "title",
                "description",
                "caption",
                "location",
                "city",
                "cidade",
                "country",
                "pais",
                "place",
                "geo",
            ):

                if field in nested:

                    _vse416_add_text(
                        parts,
                        nested.get(
                            field
                        ),
                    )


    else:

        for field in fields:

            try:

                value = getattr(
                    candidate,
                    field,
                    None,
                )

            except Exception:

                value = None


            _vse416_add_text(
                parts,
                value,
            )


    return " ".join(
        parts
    )


def _vse416_scene_geo_text(scene):
    """
    Para a cena podemos usar narrativa + localização +
    consulta visual, pois todos descrevem o alvo desejado.
    """

    if scene is None:
        return ""


    if isinstance(
        scene,
        str,
    ):

        return scene


    fields = (
        "texto",
        "text",
        "scene_text",
        "narration",
        "narrativa",
        "roteiro",
        "frase",

        "visual_query",
        "query",
        "search_query",
        "busca",

        "must_have",
        "required",
        "requirements",

        "location",
        "local",
        "city",
        "cidade",
        "country",
        "pais",
        "place",
        "geo",
    )


    parts = []


    if isinstance(
        scene,
        dict,
    ):

        for field in fields:

            if field in scene:

                _vse416_add_text(
                    parts,
                    scene.get(
                        field
                    ),
                )

    else:

        for field in fields:

            try:

                value = getattr(
                    scene,
                    field,
                    None,
                )

            except Exception:

                value = None


            _vse416_add_text(
                parts,
                value,
            )


    if not parts:

        return candidate_text(
            scene
        )


    return " ".join(
        parts
    )


def _vse416_country_set(geo):

    result = set()


    for group in geo:

        if group in _VSE416_COUNTRIES:

            result.add(
                group
            )

            continue


        parent = _VSE416_CITY_PARENT.get(
            group
        )

        if parent:

            result.add(
                parent
            )


    return result


def _vse416_city_set(geo):

    return {
        group
        for group in geo
        if group in _VSE416_CITY_PARENT
    }


def geo_contradiction_v416(
    scene_geo,
    candidate_geo,
):
    """
    Returns:
        (hard_mismatch, reason)

    Regras:

    Brazil x USA
        HARD

    São Paulo x New York
        HARD

    São Paulo x Rio de Janeiro
        HARD

    Brazil x São Paulo
        OK

    São Paulo x Brazil
        OK

    sem geografia de um dos lados
        FAIL OPEN
    """

    scene_geo = set(
        scene_geo or ()
    )

    candidate_geo = set(
        candidate_geo or ()
    )


    if not scene_geo:

        return (
            False,
            "SCENE_GEO_UNKNOWN",
        )


    if not candidate_geo:

        return (
            False,
            "CANDIDATE_GEO_UNKNOWN",
        )


    scene_countries = _vse416_country_set(
        scene_geo
    )

    candidate_countries = _vse416_country_set(
        candidate_geo
    )


    # --------------------------------------------------------
    # COUNTRY CONTRADICTION
    # --------------------------------------------------------

    if (
        scene_countries
        and
        candidate_countries
        and
        scene_countries.isdisjoint(
            candidate_countries
        )
    ):

        return (
            True,
            (
                "COUNTRY_CONTRADICTION:"
                f"{sorted(scene_countries)}"
                "!="
                f"{sorted(candidate_countries)}"
            ),
        )


    scene_cities = _vse416_city_set(
        scene_geo
    )

    candidate_cities = _vse416_city_set(
        candidate_geo
    )


    # --------------------------------------------------------
    # CITY CONTRADICTION
    #
    # Só é hard quando ambos especificam cidades concretas.
    # --------------------------------------------------------

    if (
        scene_cities
        and
        candidate_cities
        and
        scene_cities.isdisjoint(
            candidate_cities
        )
    ):

        return (
            True,
            (
                "CITY_CONTRADICTION:"
                f"{sorted(scene_cities)}"
                "!="
                f"{sorted(candidate_cities)}"
            ),
        )


    return (
        False,
        "GEO_COMPATIBLE",
    )


# Guarda a implementação anterior integralmente.
_score_candidate_pre_v416 = _score_candidate_stage_01


def _score_candidate_stage_02(
    *args,
    **kwargs
):

    result = _score_candidate_pre_v416(
        *args,
        **kwargs
    )


    # Mantém comportamento original em retornos inesperados.
    if not isinstance(
        result,
        dict,
    ):

        return result


    candidate = None
    scene = None


    if len(args) >= 1:

        candidate = args[0]

    elif "candidate" in kwargs:

        candidate = kwargs.get(
            "candidate"
        )


    if len(args) >= 2:

        scene = args[1]

    elif "scene" in kwargs:

        scene = kwargs.get(
            "scene"
        )


    scene_geo_text = (
        _vse416_scene_geo_text(
            scene
        )
    )

    candidate_geo_text = (
        _vse416_candidate_geo_text(
            candidate
        )
    )


    scene_geo = geo_hits(
        scene_geo_text
    )

    candidate_geo = geo_hits(
        candidate_geo_text
    )


    geo_hard, geo_reason = (
        geo_contradiction_v416(
            scene_geo,
            candidate_geo,
        )
    )


    # Não altera dict retornado pelo motor anterior.
    upgraded = dict(
        result
    )


    upgraded[
        "geo_scene"
    ] = sorted(
        scene_geo
    )

    upgraded[
        "geo_candidate"
    ] = sorted(
        candidate_geo
    )

    upgraded[
        "geo_hard_mismatch"
    ] = bool(
        geo_hard
    )

    upgraded[
        "geo_reason"
    ] = geo_reason


    if geo_hard:

        upgraded[
            "hard_mismatch"
        ] = True


        old_reason = str(
            upgraded.get(
                "hard_reason",
                "",
            )
            or
            ""
        ).strip()


        if old_reason:

            upgraded[
                "hard_reason"
            ] = (
                old_reason
                +
                ";"
                +
                geo_reason
            )

        else:

            upgraded[
                "hard_reason"
            ] = geo_reason


        # ----------------------------------------------------
        # Ranking safety
        #
        # Mesmo que algum consumidor futuro esqueça de
        # filtrar hard_mismatch, um asset geograficamente
        # contraditório não deve ganhar por score-base.
        # ----------------------------------------------------

        try:

            old_effective = float(
                upgraded.get(
                    "effective",
                    0.0,
                )
            )

        except Exception:

            old_effective = 0.0


        upgraded[
            "effective_pre_geo_guard"
        ] = old_effective


        upgraded[
            "effective"
        ] = min(
            old_effective,
            -10000.0,
        )


    return upgraded




RESCUE_TERMS = {
    "investigation":
        "police investigation evidence",

    "forensic":
        "forensic evidence investigation",

    "court":
        "courtroom courthouse justice",

    "building":
        "apartment building exterior",

    "family":
        "family parent child",

    "document":
        "archive documents case file",

    "police":
        "police investigation station",

    "death":
        "crime investigation memorial",

    "fall":
        "apartment window building",

    "city":
        "city urban street",

    "hospital":
        "hospital emergency medical",

    "home":
        "apartment interior residential",

    "evidence":
        "forensic evidence crime scene",
}


def rescue_queries(scene_text):

    original = norm(
        scene_text
    )

    concepts = concept_hits(
        scene_text
    )

    extras = []

    for concept in sorted(
        concepts
    ):

        term = RESCUE_TERMS.get(
            concept
        )

        if term:
            extras.append(
                term
            )

    extra = " ".join(
        extras[:3]
    )

    if not extra:
        return []

    base_tokens = [
        t
        for t in original.split()
        if t not in STOP
    ][:10]

    query = " ".join(
        base_tokens
        +
        extra.split()
    )

    return [
        query.strip()
    ]


def invoke_search(
    fn,
    query,
    local_ns,
):

    try:
        signature = inspect.signature(
            fn
        )
    except Exception:
        return []

    args = []
    kwargs = {}

    query_names = {
        "busca",
        "query",
        "q",
        "termo",
        "termo_busca",
        "search",
        "search_query",
    }

    for name, parameter in signature.parameters.items():

        lname = norm(name)

        has_value = False
        value = None

        if lname in query_names:
            value = query
            has_value = True

        elif name in local_ns:
            value = local_ns[name]
            has_value = True

        else:

            for alias in [
                "numero",
                "numero_cena",
                "scene_number",
                "must_have",
                "must",
                "cena",
                "scene",
            ]:

                if (
                    lname == norm(alias)
                    and
                    alias in local_ns
                ):
                    value = local_ns[
                        alias
                    ]

                    has_value = True
                    break


        if not has_value:

            if (
                parameter.default
                is
                inspect.Parameter.empty
            ):
                return []

            continue


        if (
            parameter.kind
            ==
            inspect.Parameter.POSITIONAL_ONLY
        ):
            args.append(
                value
            )

        elif (
            parameter.kind
            !=
            inspect.Parameter.VAR_POSITIONAL
            and
            parameter.kind
            !=
            inspect.Parameter.VAR_KEYWORD
        ):
            kwargs[name] = value


    try:
        result = fn(
            *args,
            **kwargs,
        )

    except Exception as exc:

        print(
            "VSE4_RESCUE_ERROR="
            f"{type(exc).__name__}:"
            f"{exc}"
        )

        return []


    return flatten_candidates(
        result
    )


def unique_candidates(candidates):

    result = []
    seen = set()

    for candidate in candidates:

        key = candidate_key(
            candidate
        )

        if not key:
            key = str(
                id(candidate)
            )

        if key in seen:
            continue

        seen.add(key)
        result.append(
            candidate
        )

    return result


def snapshot(info):

    return {
        "provider":
            info["provider"],

        "type":
            info["type"],

        "must":
            info["must"],

        "base":
            info["base"],

        "effective":
            info["effective"],

        "semantic_hits":
            info["semantic_hits"],

        "hard_mismatch":
            info["hard_mismatch"],

        "mismatch_reasons":
            info["mismatch_reasons"],

        "bonus":
            info["bonus"],

        "penalty":
            info["penalty"],

        "key":
            info["key"][:180],
    }


def write_audit(
    short_id,
    scene_no,
    data,
):

    directory = (
        ROOT
        / "manifests"
        / "vse4"
        / short_id
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        directory
        / f"scene_{scene_no:02d}.json"
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def truth_allowed(
    candidate,
    reference,
    global_ns,
):

    fn = global_ns.get(
        "fallback_preserva_5_2"
    )

    if not callable(fn):
        return True

    try:
        return bool(
            fn(
                candidate,
                reference,
            )
        )

    except Exception:
        return False


def choose_from_context(
    local_ns,
    global_ns,
    chosen,
):

    if os.getenv(
        "SAP_VSE4",
        "1",
    ) == "0":
        return chosen


    sid = os.getenv(
        "SHORT_ID",
        "unknown",
    ).strip() or "unknown"

    scene_no = scene_number(
        local_ns
    )

    text = context_text(
        local_ns
    )


    pool = []

    for value in local_ns.values():
        flatten_candidates(
            value,
            pool,
        )

    if isinstance(
        chosen,
        dict,
    ):
        pool.append(
            chosen
        )

    pool = unique_candidates(
        pool
    )


    if not pool:

        print(
            "VSE4_GATE=NO_CANDIDATE_POOL"
        )

        return chosen


    state = load_state(
        sid
    )


    chosen_info = score_candidate(
        chosen,
        text,
        state,
    )


    rescue_count = 0
    rescue_used = False


    weak = (
        chosen_info["must"] < 2
        or
        chosen_info["hard_mismatch"]
        or
        chosen_info["semantic_hits"] == 0
    )


    if (
        weak
        and
        os.getenv(
            "SAP_VSE4_RESCUE",
            "1",
        ) != "0"
    ):

        search_fn = global_ns.get(
            "buscar_todos_candidatos"
        )

        if callable(
            search_fn
        ):

            try:
                limit = int(
                    os.getenv(
                        "SAP_VSE4_RESCUE_QUERIES",
                        "1",
                    )
                )

            except Exception:
                limit = 1

            limit = max(
                0,
                min(
                    limit,
                    2,
                ),
            )


            for query in rescue_queries(
                text
            )[:limit]:

                print(
                    "VSE4_RESCUE_QUERY="
                    f"{query}"
                )

                extra = invoke_search(
                    search_fn,
                    query,
                    local_ns,
                )

                if extra:
                    rescue_used = True
                    rescue_count += len(
                        extra
                    )

                    pool.extend(
                        extra
                    )


            pool = unique_candidates(
                pool
            )


    scored = [
        score_candidate(
            candidate,
            text,
            state,
        )
        for candidate in pool
    ]


    allowed = []

    for info in scored:

        candidate = info[
            "candidate"
        ]

        if (
            candidate is not chosen
            and
            not truth_allowed(
                candidate,
                chosen,
                global_ns,
            )
        ):
            continue

        allowed.append(
            info
        )


    if not allowed:
        return chosen


    safe = [
        info
        for info in allowed
        if not info[
            "hard_mismatch"
        ]
    ]


    best_pool = (
        safe
        if safe
        else allowed
    )


    best = max(
        best_pool,
        key=lambda x: (
            x["must"],
            x["effective"],
        ),
    )


    reason = (
        "REFERENCE_STILL_BEST"
    )

    winner = chosen
    override = False


    if chosen_info[
        "hard_mismatch"
    ]:

        if (
            not best["hard_mismatch"]
            and
            best["must"]
            >=
            max(
                0,
                chosen_info["must"] - 1,
            )
        ):
            winner = best[
                "candidate"
            ]

            override = (
                winner is not chosen
            )

            reason = (
                "HARD_MISMATCH_RESCUE"
            )


    elif best["must"] > chosen_info[
        "must"
    ]:

        winner = best[
            "candidate"
        ]

        override = (
            winner is not chosen
        )

        reason = (
            "HIGHER_MUST_TIER"
        )


    elif (
        best["must"]
        ==
        chosen_info["must"]
        and
        best["effective"]
        >=
        chosen_info["effective"]
        + 12.0
    ):

        winner = best[
            "candidate"
        ]

        override = (
            winner is not chosen
        )

        reason = (
            "SEMANTIC_QUALITY_UPGRADE"
        )


    winner_info = score_candidate(
        winner,
        text,
        state,
    )


    print()
    print(
        "  VSE4 FINAL DECISION:"
    )

    print(
        "    VSE4_SCENE="
        f"{scene_no:02d}"
    )

    print(
        "    VSE4_POOL="
        f"{len(pool)}"
    )

    print(
        "    VSE4_RESCUE_USED="
        f"{'YES' if rescue_used else 'NO'}"
    )

    print(
        "    VSE4_RESCUE_CANDIDATES="
        f"{rescue_count}"
    )

    print(
        "    VSE4_BEFORE="
        f"{chosen_info['provider']}/"
        f"{chosen_info['type']} "
        f"must={chosen_info['must']}/2 "
        f"semantic={chosen_info['semantic_hits']} "
        f"effective={chosen_info['effective']} "
        f"hard={chosen_info['hard_mismatch']}"
    )

    print(
        "    VSE4_AFTER="
        f"{winner_info['provider']}/"
        f"{winner_info['type']} "
        f"must={winner_info['must']}/2 "
        f"semantic={winner_info['semantic_hits']} "
        f"effective={winner_info['effective']} "
        f"hard={winner_info['hard_mismatch']}"
    )

    print(
        "    VSE4_OVERRIDE="
        f"{'YES' if override else 'NO'}"
    )

    print(
        "    VSE4_REASON="
        f"{reason}"
    )


    state.setdefault(
        "providers",
        [],
    ).append(
        winner_info["provider"]
    )

    state.setdefault(
        "groups",
        [],
    ).append(
        winner_info["group"]
    )

    state.setdefault(
        "types",
        [],
    ).append(
        winner_info["type"]
    )

    state.setdefault(
        "keys",
        [],
    ).append(
        winner_info["key"]
    )

    state.setdefault(
        "scenes",
        {},
    )[
        f"{scene_no:02d}"
    ] = {
        "provider":
            winner_info["provider"],

        "type":
            winner_info["type"],

        "must":
            winner_info["must"],

        "effective":
            winner_info["effective"],

        "reason":
            reason,
    }


    for field in [
        "providers",
        "groups",
        "types",
        "keys",
    ]:
        state[field] = state[
            field
        ][-30:]


    save_state(
        sid,
        state,
    )


    write_audit(
        sid,
        scene_no,
        {
            "short_id":
                sid,

            "scene":
                scene_no,

            "context":
                text[:1000],

            "pool_count":
                len(pool),

            "rescue_used":
                rescue_used,

            "rescue_candidates":
                rescue_count,

            "override":
                override,

            "reason":
                reason,

            "before":
                snapshot(
                    chosen_info
                ),

            "after":
                snapshot(
                    winner_info
                ),

            "top_candidates": [
                snapshot(x)
                for x in sorted(
                    allowed,
                    key=lambda z:
                        z["effective"],
                    reverse=True,
                )[:8]
            ],
        },
    )


    return winner



# SHORTAUTOPRO VSE4.1.4 SEMANTIC SAFETY

_vse414_score_candidate_core = _score_candidate_stage_02


def _vse414_flat_text(value):

    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, (int, float, bool)):
        return [str(value)]

    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_vse414_flat_text(item))
        return out

    return []




def _vse414_geo_conflict(
    scene_text,
    candidate_txt,
):

    scene_geo = set(
        geo_hits(scene_text)
    )

    candidate_geo = set(
        geo_hits(candidate_txt)
    )

    # Unknown geography is not automatically wrong.
    if not scene_geo or not candidate_geo:
        return False, scene_geo, candidate_geo

    # Shared country/city hierarchy = compatible.
    if scene_geo & candidate_geo:
        return False, scene_geo, candidate_geo

    return True, scene_geo, candidate_geo


_VSE414_MEDICINE_STRONG = {
    "pill",
    "pills",
    "medicine",
    "medication",
    "drug",
    "drugs",
    "capsule",
    "capsules",
    "pharmacy",
    "prescription",
    "remedio",
    "remedios",
    "medicamento",
    "medicamentos",
    "comprimido",
    "comprimidos",
    "capsula",
    "capsulas",
    "farmacia",
    "seringa",
    "syringe",
}


_VSE414_MEDICAL_CONTEXT = {
    "medicine",
    "medical",
    "medication",
    "hospital",
    "doctor",
    "patient",
    "health",
    "pharmacy",
    "drug",
    "remedio",
    "medicamento",
    "hospital",
    "medico",
    "paciente",
    "saude",
    "farmacia",
}


def _vse414_false_medical(
    scene_text,
    candidate_txt,
):

    st = tokens(scene_text)
    ct = tokens(candidate_txt)

    candidate_medical = bool(
        ct & _VSE414_MEDICINE_STRONG
    )

    scene_medical = bool(
        st & _VSE414_MEDICAL_CONTEXT
    )

    return (
        candidate_medical
        and not scene_medical
    )


_VSE414_STRONG_DOCUMENTARY = {
    "police",
    "investigation",
    "crime_scene",
    "evidence",
    "forensics",
    "court",
    "law",
    "prison",
    "news",
    "document",
    "archive",
    "hospital",
    "laboratory",
    "military",
    "war",
}


_VSE414_STRONG_LIFESTYLE = (
    "relaxing",
    "smiling",
    "selfie",
    "fashion",
    "beauty",
    "vacation",
    "shopping",
    "posing",
    "influencer",
    "romantic couple",
    "happy woman",
    "happy man",
    "woman relaxing",
    "man relaxing",
    "modelo sorrindo",
    "mulher relaxando",
    "homem relaxando",
)




def _vse414_abstract_penalty(
    scene_text,
    candidate_txt,
):

    sc = set(
        concept_hits(scene_text)
    )

    cc = set(
        concept_hits(candidate_txt)
    )

    if not (
        sc
        &
        _VSE414_STRONG_DOCUMENTARY
    ):
        return 0.0

    if "abstract" not in cc:
        return 0.0

    if sc & cc:
        return -8.0

    return -34.0


def _vse414_number(
    value,
    default=0.0,
):

    try:
        return float(value)
    except Exception:
        return default


def _score_candidate_stage_03(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):

    result = _vse414_score_candidate_core(
        candidate,
        scene,
        state,
        *args,
        **kwargs
    )

    if not isinstance(result, dict):
        return result

    result = dict(result)

    scene_text = candidate_text(scene)
    candidate_txt = candidate_text(candidate)

    geo_bad, scene_geo, candidate_geo = (
        _vse414_geo_conflict(
            scene_text,
            candidate_txt,
        )
    )

    medical_bad = _vse414_false_medical(
        scene_text,
        candidate_txt,
    )

    lifestyle_penalty = (
        _vse414_lifestyle_penalty(
            scene_text,
            candidate_txt,
        )
    )

    abstract_penalty = (
        _vse414_abstract_penalty(
            scene_text,
            candidate_txt,
        )
    )

    hard = bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )

    reasons = []

    old_reason = result.get(
        "hard_reason"
    )

    if old_reason:
        reasons.append(
            str(old_reason)
        )

    if geo_bad:
        hard = True
        reasons.append(
            "GEO_CONTRADICTION"
        )

    if medical_bad:
        hard = True
        reasons.append(
            "FALSE_MEDICAL_ASSOCIATION"
        )

    adjustment = (
        lifestyle_penalty
        +
        abstract_penalty
    )

    effective = _vse414_number(
        result.get(
            "effective",
            result.get(
                "effective_score",
                result.get(
                    "score",
                    0,
                ),
            ),
        )
    )

    effective += adjustment

    if hard:
        # Truth/factual mismatch dominates MUST and stock score.
        effective = min(
            effective,
            -1000000.0,
        )

    result[
        "hard_mismatch"
    ] = hard

    result[
        "hard_reason"
    ] = (
        "|".join(
            dict.fromkeys(reasons)
        )
        if reasons
        else ""
    )

    result[
        "scene_geo"
    ] = sorted(scene_geo)

    result[
        "candidate_geo"
    ] = sorted(candidate_geo)

    result[
        "vse414_adjustment"
    ] = adjustment

    result[
        "vse414_lifestyle_penalty"
    ] = lifestyle_penalty

    result[
        "vse414_abstract_penalty"
    ] = abstract_penalty

    result[
        "effective"
    ] = effective

    if "effective_score" in result:
        result[
            "effective_score"
        ] = effective

    return result



# SHORTAUTOPRO VSE4 SEMANTIC SAFETY V4.1.4
#
# Final semantic safety layer.
#
# Objetivos:
# - geografia incompatível domina score/MUST
# - compatibilidade cidade/pais é preservada
# - lifestyle stock genérico sofre penalidade contextual
# - associação médica falsa sofre penalidade contextual
# - fail-open quando não há evidência suficiente


_VSE414_COUNTRY_ROOT = {

    "brazil":
        "brazil",

    "sao_paulo":
        "brazil",

    "rio_de_janeiro":
        "brazil",

    "brasilia":
        "brazil",


    "usa":
        "usa",

    "new_york":
        "usa",

    "los_angeles":
        "usa",

    "washington_dc":
        "usa",


    "united_kingdom":
        "united_kingdom",

    "london":
        "united_kingdom",


    "france":
        "france",

    "paris":
        "france",


    "italy":
        "italy",

    "rome":
        "italy",


    "germany":
        "germany",

    "spain":
        "spain",

    "portugal":
        "portugal",


    "japan":
        "japan",

    "tokyo":
        "japan",


    "china":
        "china",

    "russia":
        "russia",

    "ukraine":
        "ukraine",

    "mexico":
        "mexico",

    "argentina":
        "argentina",

    "canada":
        "canada",

    "australia":
        "australia",

    "india":
        "india",

    "south_korea":
        "south_korea",

    "egypt":
        "egypt",
}


def vse414_geo_roots(groups):

    roots = set()

    for group in groups or ():

        root = _VSE414_COUNTRY_ROOT.get(
            group,
            group,
        )

        if root:
            roots.add(
                root
            )

    return roots


def vse414_geo_conflict(
    scene_text,
    candidate_txt,
):

    scene_geo = set(
        geo_hits(
            scene_text
        )
    )

    candidate_geo = set(
        geo_hits(
            candidate_txt
        )
    )


    # Sem evidência dos dois lados:
    # não inventa conflito.
    if not scene_geo:
        return False

    if not candidate_geo:
        return False


    # Mesmo grupo explícito.
    if (
        scene_geo
        &
        candidate_geo
    ):
        return False


    scene_roots = vse414_geo_roots(
        scene_geo
    )

    candidate_roots = vse414_geo_roots(
        candidate_geo
    )


    # Mesmo país/root.
    if (
        scene_roots
        &
        candidate_roots
    ):
        return False


    # Há geografia explícita dos dois lados,
    # porém em países incompatíveis.
    return True


def vse414_word_hits(
    text,
    vocabulary,
):

    normalized = norm(
        text
    )

    hits = set()

    for term in vocabulary:

        normalized_term = norm(
            term
        )

        if not normalized_term:
            continue

        if normalized_term in normalized:
            hits.add(
                normalized_term
            )

    return hits


def vse414_serious_documentary_context(
    scene_text,
):

    concepts = set(
        concept_hits(
            scene_text
        )
    )

    serious = {
        "police",
        "investigation",
        "crime_scene",
        "evidence",
        "forensics",
        "court",
        "gavel",
        "prison",
        "law",
        "document",
        "news",
        "archive",
        "hospital",
        "fire",
        "rescue",
        "military",
        "war",
        "laboratory",
    }

    return bool(
        concepts
        &
        serious
    )


def vse414_context_penalty(
    scene_text,
    candidate_txt,
):

    penalty = 0.0

    reasons = []


    # ========================================================
    # FALSE MEDICINE ASSOCIATION
    # ========================================================

    candidate_medicine = vse414_word_hits(
        candidate_txt,
        MEDICINE_TERMS,
    )

    scene_medicine = vse414_word_hits(
        scene_text,
        MEDICINE_TERMS,
    )


    if (
        candidate_medicine
        and
        not scene_medicine
        and
        vse414_serious_documentary_context(
            scene_text
        )
    ):

        penalty += 85.0

        reasons.append(
            "UNSUPPORTED_MEDICINE_VISUAL"
        )


    # ========================================================
    # GENERIC STOCK / LIFESTYLE
    # ========================================================

    candidate_generic = vse414_word_hits(
        candidate_txt,
        GENERIC_LIFESTYLE,
    )

    scene_generic = vse414_word_hits(
        scene_text,
        GENERIC_LIFESTYLE,
    )


    if (
        candidate_generic
        and
        not scene_generic
        and
        vse414_serious_documentary_context(
            scene_text
        )
    ):

        penalty += 55.0

        reasons.append(
            "GENERIC_LIFESTYLE_IN_DOCUMENTARY_CONTEXT"
        )


    return (
        penalty,
        reasons,
    )


_vse414_score_candidate_base = (
    _score_candidate_stage_03
)


def _score_candidate_stage_04(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):

    result = (
        _vse414_score_candidate_base(
            candidate,
            scene,
            state,
            *args,
            **kwargs
        )
    )


    # Mantém compatibilidade caso uma versão futura
    # mude o formato.
    if not isinstance(
        result,
        dict,
    ):
        return result


    scene_text = candidate_text(
        scene
    )

    candidate_txt = candidate_text(
        candidate
    )


    geo_conflict = (
        vse414_geo_conflict(
            scene_text,
            candidate_txt,
        )
    )


    contextual_penalty, reasons = (
        vse414_context_penalty(
            scene_text,
            candidate_txt,
        )
    )


    # Trabalha em cópia para não alterar estruturas
    # que possam estar reutilizadas em outro ranking.
    result = dict(
        result
    )


    result[
        "vse414_geo_conflict"
    ] = bool(
        geo_conflict
    )

    result[
        "vse414_context_penalty"
    ] = float(
        contextual_penalty
    )

    result[
        "vse414_reasons"
    ] = list(
        reasons
    )


    effective_key = None

    for key in (
        "effective",
        "effective_score",
        "score_final",
        "final_score",
    ):

        if key in result:

            try:
                float(
                    result[
                        key
                    ]
                )

                effective_key = key
                break

            except Exception:
                pass


    # Penalidades contextuais são fortes,
    # mas não necessariamente hard-block.
    if (
        contextual_penalty
        >
        0.0
        and
        effective_key
        is not None
    ):

        result[
            effective_key
        ] = (
            float(
                result[
                    effective_key
                ]
            )
            -
            contextual_penalty
        )


    # ========================================================
    # GEOGRAPHY HARD SAFETY
    #
    # MUST 2/2 ou score alto NUNCA podem fazer
    # Empire State Building vencer São Paulo.
    # ========================================================

    if geo_conflict:

        result[
            "hard_mismatch"
        ] = True


        existing_reason = (
            result.get(
                "hard_reason"
            )
            or
            result.get(
                "mismatch_reason"
            )
            or
            ""
        )


        reason = (
            "GEOGRAPHIC_CONTRADICTION"
        )


        if existing_reason:

            result[
                "hard_reason"
            ] = (
                f"{existing_reason}|"
                f"{reason}"
            )

        else:

            result[
                "hard_reason"
            ] = reason


        if effective_key is not None:

            # Hard mismatch precisa ser impossível de
            # superar apenas com score/MUST.
            result[
                effective_key
            ] = min(
                float(
                    result[
                        effective_key
                    ]
                ),
                -10000.0,
            )


        result[
            "vse414_reasons"
        ].append(
            reason
        )


    return result


def vse414_self_test():

    state = {
        "providers": [
            "pixabay",
            "pixabay",
        ],
        "groups": [],
        "types": [],
        "keys": [],
    }


    # ========================================================
    # TEST 1
    # São Paulo x Nova York
    # ========================================================

    scene = (
        "Investigação em apartamento "
        "na cidade de São Paulo"
    )


    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Empire State Building New York",

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
            "Apartment building Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    bad = score_candidate(
        wrong,
        scene,
        state,
    )


    good = score_candidate(
        correct,
        scene,
        state,
    )


    print(
        "TEST_GEO_WRONG_HARD=",
        bad.get(
            "hard_mismatch"
        ),
    )

    print(
        "TEST_GEO_WRONG_REASON=",
        bad.get(
            "hard_reason"
        ),
    )

    print(
        "TEST_GEO_GOOD_HARD=",
        good.get(
            "hard_mismatch"
        ),
    )

    print(
        "TEST_GEO_BAD_EFFECTIVE=",
        bad.get(
            "effective"
        ),
    )

    print(
        "TEST_GEO_GOOD_EFFECTIVE=",
        good.get(
            "effective"
        ),
    )


    assert (
        bad.get(
            "hard_mismatch"
        )
        is True
    )


    assert (
        good.get(
            "hard_mismatch"
        )
        is False
    )


    assert (
        float(
            good.get(
                "effective",
                -999999,
            )
        )
        >
        float(
            bad.get(
                "effective",
                999999,
            )
        )
    )


    # ========================================================
    # TEST 2
    # São Paulo x Brasil genérico
    #
    # NÃO deve bloquear.
    # ========================================================

    brazil_generic = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Residential building Brazil",

        "score":
            100,

        "width":
            1080,

        "height":
            1920,
    }


    compatible = score_candidate(
        brazil_generic,
        scene,
        {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        },
    )


    assert (
        compatible.get(
            "vse414_geo_conflict"
        )
        is False
    )


    # ========================================================
    # TEST 3
    # Investigação x pills
    # ========================================================

    forensic_scene = (
        "A perícia analisou os indícios "
        "encontrados na cena do crime."
    )


    pills = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Pills medicine tablets on desk",

        "score":
            180,

        "width":
            1920,

        "height":
            1080,
    }


    forensic = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Forensic evidence crime scene investigation",

        "score":
            150,

        "width":
            1920,

        "height":
            1080,
    }


    p = score_candidate(
        pills,
        forensic_scene,
        {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        },
    )


    f = score_candidate(
        forensic,
        forensic_scene,
        {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        },
    )


    print(
        "TEST_MEDICINE_PENALTY=",
        p.get(
            "vse414_context_penalty"
        ),
    )


    assert (
        float(
            p.get(
                "vse414_context_penalty",
                0,
            )
        )
        >
        0
    )


    assert (
        float(
            f.get(
                "vse414_context_penalty",
                0,
            )
        )
        ==
        0
    )


    # ========================================================
    # TEST 4
    # Investigation x relaxing lifestyle
    # ========================================================

    lifestyle = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Relaxing smiling woman in bedroom lifestyle",

        "score":
            190,

        "width":
            1920,

        "height":
            1080,
    }


    l = score_candidate(
        lifestyle,
        forensic_scene,
        {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        },
    )


    print(
        "TEST_LIFESTYLE_PENALTY=",
        l.get(
            "vse414_context_penalty"
        ),
    )


    assert (
        float(
            l.get(
                "vse414_context_penalty",
                0,
            )
        )
        >
        0
    )


    print(
        "VSE414_SELF_TEST=PASS"
    )



# SHORTAUTOPRO VSE4.17 SEMANTIC HARD MISMATCH
#
# Final semantic safety layer.
#
# Goals:
# - direct string scene semantics
# - geography contradiction blocking
# - medicine false-association blocking
# - generic lifestyle suppression
# - preserve all previous VSE4 scoring

_vse417_candidate_text_base = candidate_text





_VSE417_GEO_PARENT = {

    "sao_paulo":
        "brazil",

    "rio_de_janeiro":
        "brazil",

    "brasilia":
        "brazil",


    "new_york":
        "usa",

    "los_angeles":
        "usa",

    "washington_dc":
        "usa",


    "london":
        "united_kingdom",


    "paris":
        "france",


    "rome":
        "italy",


    "tokyo":
        "japan",
}


_VSE417_GEO_ROOTS = {

    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "germany",
    "spain",
    "portugal",
    "japan",
    "china",
    "russia",
    "ukraine",
    "mexico",
    "argentina",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}



def _vse417_geo_root(group):

    return _VSE417_GEO_PARENT.get(
        group,
        group,
    )



def _vse417_geo_conflict(
    scene_groups,
    candidate_groups,
):

    scene_groups = set(
        scene_groups or []
    )

    candidate_groups = set(
        candidate_groups or []
    )


    # If either side has no explicit geography,
    # do not invent a contradiction.
    if not scene_groups:
        return False

    if not candidate_groups:
        return False


    scene_roots = {
        _vse417_geo_root(g)
        for g in scene_groups
        if (
            g in _VSE417_GEO_ROOTS
            or
            g in _VSE417_GEO_PARENT
        )
    }


    candidate_roots = {
        _vse417_geo_root(g)
        for g in candidate_groups
        if (
            g in _VSE417_GEO_ROOTS
            or
            g in _VSE417_GEO_PARENT
        )
    }


    # Explicit countries disagree.
    if (
        scene_roots
        and
        candidate_roots
        and
        scene_roots.isdisjoint(
            candidate_roots
        )
    ):

        return True


    # Same country but two explicitly different cities.
    scene_specific = {
        g
        for g in scene_groups
        if g in _VSE417_GEO_PARENT
    }


    candidate_specific = {
        g
        for g in candidate_groups
        if g in _VSE417_GEO_PARENT
    }


    if (
        scene_specific
        and
        candidate_specific
        and
        scene_specific.isdisjoint(
            candidate_specific
        )
    ):

        # Only treat it as contradiction if
        # both belong to the same country root.
        shared_root = (
            {
                _vse417_geo_root(g)
                for g in scene_specific
            }
            &
            {
                _vse417_geo_root(g)
                for g in candidate_specific
            }
        )

        if shared_root:
            return True


    return False



def _vse417_token_set(value):

    try:
        return set(
            tokens(value)
        )

    except Exception:
        return set()



def _vse417_concepts(value):
    """
    Tri-state concept extraction.

    set({...}) -> successful extraction with concepts
    set()      -> successful extraction with zero concepts
    None       -> concept engine failure
    """
    try:
        return set(
            concept_hits(value)
        )

    except Exception:
        return None



_vse417_score_candidate_base = _score_candidate_stage_04



def _score_candidate_stage_05(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):

    info = _vse417_score_candidate_base(
        candidate,
        scene,
        state,
        *args,
        **kwargs
    )


    # Preserve unknown return shapes.
    if not isinstance(
        info,
        dict,
    ):
        return info


    info = dict(
        info
    )


    scene_text = candidate_text(
        scene
    )

    candidate_txt = candidate_text(
        candidate
    )


    try:

        scene_geo = set(
            geo_hits(
                scene_text
            )
        )

    except Exception:

        scene_geo = set()


    try:

        candidate_geo = set(
            geo_hits(
                candidate_txt
            )
        )

    except Exception:

        candidate_geo = set()


    geo_conflict = _vse417_geo_conflict(
        scene_geo,
        candidate_geo,
    )


    scene_tokens = _vse417_token_set(
        scene_text
    )

    candidate_tokens = _vse417_token_set(
        candidate_txt
    )


    scene_concepts = _vse417_concepts(
        scene_text
    )

    candidate_concepts = _vse417_concepts(
        candidate_txt
    )

    # ========================================================
    # VSE417_CONCEPT_FAIL_CLOSED_FINAL
    # ========================================================

    scene_concept_error = (
        scene_concepts is None
    )

    candidate_concept_error = (
        candidate_concepts is None
    )

    if (
        scene_concept_error
        or
        candidate_concept_error
    ):

        if not isinstance(
            info,
            dict,
        ):
            return info

        info = dict(
            info
        )

        concept_error_fields = []

        if scene_concept_error:
            concept_error_fields.append(
                "scene"
            )

        if candidate_concept_error:
            concept_error_fields.append(
                "candidate"
            )

        info[
            "vse417_concept_error"
        ] = True

        info[
            "vse417_concept_error_fields"
        ] = concept_error_fields

        info[
            "semantic_validation_status"
        ] = "ERROR"

        info[
            "technical_reject"
        ] = True

        info[
            "technical_reject_reason"
        ] = "CONCEPT_VALIDATION_ERROR"

        penalties = info.get(
            "vse417_penalties",
            [],
        )

        if not isinstance(
            penalties,
            list,
        ):
            penalties = []

        penalties = list(
            penalties
        )

        if (
            "CONCEPT_VALIDATION_ERROR"
            not in penalties
        ):
            penalties.append(
                "CONCEPT_VALIDATION_ERROR"
            )

        info[
            "vse417_penalties"
        ] = penalties

        try:
            old_effective = float(
                info.get(
                    "effective",
                    0.0,
                )
            )
        except Exception:
            old_effective = 0.0

        info[
            "effective_before_concept_error"
        ] = old_effective

        info[
            "effective"
        ] = min(
            old_effective,
            -10000000.0,
        )

        if "effective_score" in info:

            try:
                old_effective_score = float(
                    info.get(
                        "effective_score",
                        0.0,
                    )
                )
            except Exception:
                old_effective_score = 0.0

            info[
                "effective_score_before_concept_error"
            ] = old_effective_score

            info[
                "effective_score"
            ] = min(
                old_effective_score,
                -10000000.0,
            )

        info[
            "concept_error_score_ceiling"
        ] = -10000000.0

        return info



    try:

        medicine_tokens = {
            norm(x)
            for x in MEDICINE_TERMS
        }

    except Exception:

        medicine_tokens = set()


    try:

        lifestyle_tokens = {
            norm(x)
            for x in GENERIC_LIFESTYLE
        }

    except Exception:

        lifestyle_tokens = set()


    medicine_hits = (
        candidate_tokens
        &
        medicine_tokens
    )


    scene_medicine_hits = (
        scene_tokens
        &
        medicine_tokens
    )


    generic_hits = (
        candidate_tokens
        &
        lifestyle_tokens
    )


    documentary_scene = bool(

        scene_concepts
        &
        {
            "police",
            "investigation",
            "crime_scene",
            "evidence",
            "forensics",
            "court",
            "law",
            "prison",
            "military",
            "war",
            "news",
            "archive",
        }
    )


    concept_overlap = (
        scene_concepts
        &
        candidate_concepts
    )


    medicine_false_association = bool(
        medicine_hits
        and
        not scene_medicine_hits
        and
        (
            scene_concepts
            &
            {
                "investigation",
                "crime_scene",
                "evidence",
                "forensics",
            }
        )
    )


    # --------------------------------------------------------
    # EFFECTIVE SCORE
    # --------------------------------------------------------

    try:

        effective = float(
            info.get(
                "effective",
                info.get(
                    "score",
                    0.0,
                ),
            )
        )

    except Exception:

        effective = 0.0


    penalties = []


    # Geography contradiction is decisive.
    if geo_conflict:

        effective -= 1000.0

        penalties.append(
            "GEO_CONTRADICTION"
        )


    # Pills/medication must not illustrate generic forensic
    # evidence unless medicine actually belongs to the scene.
    if medicine_false_association:

        effective -= 650.0

        penalties.append(
            "MEDICINE_FALSE_ASSOCIATION"
        )


    # Generic lifestyle stock footage should lose against
    # documentary-specific media.
    generic_penalty = 0.0

    if (
        documentary_scene
        and
        generic_hits
        and
        not concept_overlap
    ):

        generic_penalty = 70.0

        effective -= generic_penalty

        penalties.append(
            "GENERIC_LIFESTYLE"
        )


    # Concrete documentary scene + zero semantic concept
    # overlap receives an additional soft penalty.
    semantic_void_penalty = 0.0

    if (
        documentary_scene
        and
        scene_concepts
        and
        not concept_overlap
    ):

        semantic_void_penalty = 28.0

        effective -= semantic_void_penalty

        penalties.append(
            "DOCUMENTARY_SEMANTIC_VOID"
        )


    previous_hard = bool(
        info.get(
            "hard_mismatch",
            False,
        )
    )


    hard = bool(
        previous_hard
        or
        geo_conflict
        or
        medicine_false_association
    )


    info[
        "hard_mismatch"
    ] = hard


    info[
        "effective"
    ] = round(
        effective,
        3,
    )


    info[
        "geo_conflict"
    ] = geo_conflict


    info[
        "scene_geo"
    ] = sorted(
        scene_geo
    )


    info[
        "candidate_geo"
    ] = sorted(
        candidate_geo
    )


    info[
        "medicine_false_association"
    ] = medicine_false_association


    info[
        "generic_penalty"
    ] = generic_penalty


    info[
        "semantic_void_penalty"
    ] = semantic_void_penalty


    info[
        "vse417_penalties"
    ] = penalties


    if hard and penalties:

        info[
            "hard_reason"
        ] = "|".join(
            penalties
        )


    return info






# SHORTAUTOPRO VSE4 HARD MISMATCH V4.1.4

_vse414_score_candidate_original = _score_candidate_stage_05


def _vse414_geo_contradiction(
    scene_text,
    candidate_text_value,
):
    """
    Conflito geográfico explícito.

    A ontologia GEO_GROUPS é hierárquica:
      Sao Paulo -> {brazil, sao_paulo}
      New York  -> {usa, new_york}

    Se ambos possuem geografia identificável e não existe
    interseção, consideramos incompatibilidade explícita.
    """

    scene_geo = set(
        geo_hits(
            scene_text
        )
    )

    candidate_geo = set(
        geo_hits(
            candidate_text_value
        )
    )


    if not scene_geo:
        return False, scene_geo, candidate_geo


    if not candidate_geo:
        return False, scene_geo, candidate_geo


    compatible = bool(
        scene_geo
        &
        candidate_geo
    )


    return (
        not compatible,
        scene_geo,
        candidate_geo,
    )



def _vse414_documentary_scene(
    scene_text,
):
    """
    Detecta contexto em que mídia stock lifestyle
    deve receber penalidade forte.
    """

    concepts = set(
        concept_hits(
            scene_text
        )
    )


    documentary = {
        "police",
        "investigation",
        "crime_scene",
        "evidence",
        "forensics",
        "court",
        "gavel",
        "prison",
        "law",
        "document",
        "news",
        "archive",
        "camera",
        "hospital",
        "fire",
        "rescue",
        "military",
        "war",
        "laboratory",
        "space",
        "rocket",
    }


    return bool(
        concepts
        &
        documentary
    )



def _vse414_lifestyle_penalty(
    scene_text,
    candidate_text_value,
):
    """
    Rebaixa stock lifestyle quando a cena pede
    conteúdo factual/documental.

    Não é hard-block porque em alguns contextos
    uma pessoa/quarto pode ser semanticamente válida.
    """

    if not _vse414_documentary_scene(
        scene_text
    ):
        return 0.0


    ctokens = set(
        tokens(
            candidate_text_value
        )
    )


    lifestyle = {
        norm(x)
        for x in GENERIC_LIFESTYLE
    }


    hits = (
        ctokens
        &
        lifestyle
    )


    if not hits:
        return 0.0


    scene_concepts = set(
        concept_hits(
            scene_text
        )
    )

    candidate_concepts = set(
        concept_hits(
            candidate_text_value
        )
    )


    overlap = (
        scene_concepts
        &
        candidate_concepts
    )


    if overlap:
        return -18.0


    return -42.0



def _vse414_medicine_penalty(
    scene_text,
    candidate_text_value,
):
    """
    Evita associação visual falsa:
    laudo/evidência -> comprimidos

    Se roteiro não fala de medicamento e candidato
    é explicitamente farmacêutico, recebe penalidade.
    """

    scene_tokens = set(
        tokens(
            scene_text
        )
    )

    candidate_tokens = set(
        tokens(
            candidate_text_value
        )
    )


    med = {
        norm(x)
        for x in MEDICINE_TERMS
    }


    candidate_med = (
        candidate_tokens
        &
        med
    )


    if not candidate_med:
        return 0.0


    scene_med = (
        scene_tokens
        &
        med
    )


    if scene_med:
        return 0.0


    scene_concepts = set(
        concept_hits(
            scene_text
        )
    )


    # Se o próprio contexto é explicitamente medicina,
    # não penaliza.
    if (
        "medicine" in scene_concepts
        or
        "hospital" in scene_concepts
    ):
        return 0.0


    return -55.0



def _score_candidate_stage_06(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):
    """
    VSE4.1.4 post-ranking safety layer.

    Mantém integralmente o score original e adiciona:
      - contradição geográfica explícita
      - anti-lifestyle documental
      - anti-associação médica enganosa
    """

    result = _vse414_score_candidate_original(
        candidate,
        scene,
        state,
        *args,
        **kwargs
    )


    if not isinstance(
        result,
        dict,
    ):
        return result


    # Copia para não modificar um objeto compartilhado.
    result = dict(
        result
    )


    scene_text = candidate_text(
        scene
    )

    candidate_text_value = candidate_text(
        candidate
    )


    geo_bad, scene_geo, candidate_geo = (
        _vse414_geo_contradiction(
            scene_text,
            candidate_text_value,
        )
    )


    extra_penalty = 0.0

    reasons = []


    if geo_bad:

        # Contradição geográfica explícita é hard mismatch.
        result[
            "hard_mismatch"
        ] = True

        result[
            "geo_mismatch"
        ] = True

        reasons.append(
            "GEO_CONTRADICTION"
        )

        extra_penalty -= 1000.0


    lifestyle = _vse414_lifestyle_penalty(
        scene_text,
        candidate_text_value,
    )


    if lifestyle:

        extra_penalty += lifestyle

        reasons.append(
            "GENERIC_LIFESTYLE"
        )


    medicine = _vse414_medicine_penalty(
        scene_text,
        candidate_text_value,
    )


    if medicine:

        extra_penalty += medicine

        reasons.append(
            "FALSE_MEDICINE_ASSOCIATION"
        )


    # --------------------------------------------------------
    # Ajusta apenas os campos de score que já existem.
    # --------------------------------------------------------

    if extra_penalty:

        if "effective" in result:

            try:
                result[
                    "effective"
                ] = (
                    float(
                        result[
                            "effective"
                        ]
                    )
                    +
                    extra_penalty
                )
            except Exception:

                # Do not silently lose the penalty when the
                # primary score field is malformed.
                #
                # effective_score has not been adjusted yet at
                # this point, so it can be used as the baseline.
                try:

                    recovered_value = (
                        float(
                            result[
                                "effective_score"
                            ]
                        )
                        +
                        extra_penalty
                    )

                    result[
                        "effective"
                    ] = recovered_value

                    recovered_fields = result.get(
                        "score_state_recovered_fields",
                        [],
                    )

                    if not isinstance(
                        recovered_fields,
                        list,
                    ):
                        recovered_fields = []

                    recovered_fields = list(
                        recovered_fields
                    )

                    if "effective" not in recovered_fields:
                        recovered_fields.append(
                            "effective"
                        )

                    result[
                        "score_state_recovered_fields"
                    ] = recovered_fields

                    result[
                        "score_state_recovered"
                    ] = True

                except Exception:

                    # Both numeric paths are unavailable.
                    # Never allow malformed score state to remain
                    # rankable as if penalty application succeeded.
                    result[
                        "effective"
                    ] = -500000.0

                    result[
                        "score_state_error"
                    ] = True

                    error_fields = result.get(
                        "score_state_error_fields",
                        [],
                    )

                    if not isinstance(
                        error_fields,
                        list,
                    ):
                        error_fields = []

                    error_fields = list(
                        error_fields
                    )

                    if "effective" not in error_fields:
                        error_fields.append(
                            "effective"
                        )

                    result[
                        "score_state_error_fields"
                    ] = error_fields


        if "effective_score" in result:

            try:
                result[
                    "effective_score"
                ] = (
                    float(
                        result[
                            "effective_score"
                        ]
                    )
                    +
                    extra_penalty
                )
            except Exception:

                # effective has already received extra_penalty
                # above, therefore copying it is the correct
                # synchronized recovery and must NOT add the
                # penalty a second time.
                try:

                    result[
                        "effective_score"
                    ] = float(
                        result[
                            "effective"
                        ]
                    )

                    recovered_fields = result.get(
                        "score_state_recovered_fields",
                        [],
                    )

                    if not isinstance(
                        recovered_fields,
                        list,
                    ):
                        recovered_fields = []

                    recovered_fields = list(
                        recovered_fields
                    )

                    if (
                        "effective_score"
                        not in recovered_fields
                    ):
                        recovered_fields.append(
                            "effective_score"
                        )

                    result[
                        "score_state_recovered_fields"
                    ] = recovered_fields

                    result[
                        "score_state_recovered"
                    ] = True

                except Exception:

                    result[
                        "effective_score"
                    ] = -500000.0

                    result[
                        "score_state_error"
                    ] = True

                    error_fields = result.get(
                        "score_state_error_fields",
                        [],
                    )

                    if not isinstance(
                        error_fields,
                        list,
                    ):
                        error_fields = []

                    error_fields = list(
                        error_fields
                    )

                    if (
                        "effective_score"
                        not in error_fields
                    ):
                        error_fields.append(
                            "effective_score"
                        )

                    result[
                        "score_state_error_fields"
                    ] = error_fields


        old_penalty = result.get(
            "vse414_penalty",
            0.0,
        )

        try:
            old_penalty = float(
                old_penalty
            )
        except Exception:
            old_penalty = 0.0


        result[
            "vse414_penalty"
        ] = (
            old_penalty
            +
            extra_penalty
        )


    if reasons:

        result[
            "vse414_reasons"
        ] = reasons


    result[
        "vse414_scene_geo"
    ] = sorted(
        scene_geo
    )

    result[
        "vse414_candidate_geo"
    ] = sorted(
        candidate_geo
    )


    return result




# ============================================================
# SHORTAUTOPRO VSE4
# Rank Pool Compatibility API V1
# ============================================================

def rank_pool(
    candidates,
    scene,
    state=None,
    *,
    with_scores=False,
):
    """
    Ranking oficial compatível do VSE4.

    Entrada:
        candidates:
            lista, tupla, set ou estrutura aninhada
            de candidatos.

        scene:
            cena/string/dict usada por score_candidate().

        state:
            histórico visual opcional.

        with_scores:
            False -> retorna candidatos ordenados.
            True  -> retorna registros com candidato + score.

    Ordem:
        1. nunca prioriza hard mismatch
        2. maior MUST
        3. maior effective score
        4. maior base score

    Não altera os candidatos originais.
    """

    if state is None:

        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }


    pool = flatten_candidates(
        candidates
    )


    ranked = []


    for index, candidate in enumerate(
        pool
    ):

        try:

            details = score_candidate(
                candidate,
                scene,
                state,
            )

        except Exception as exc:

            details = {
                "hard_mismatch": True,
                "effective": float("-inf"),
                "base": 0.0,
                "must": 0,
                "rank_error":
                    f"{type(exc).__name__}: {exc}",
            }


        if not isinstance(
            details,
            dict,
        ):

            details = {
                "hard_mismatch": True,
                "effective": float("-inf"),
                "base": 0.0,
                "must": 0,
                "rank_error":
                    "score_candidate_return_not_dict",
            }


        hard = bool(
            details.get(
                "hard_mismatch",
                False,
            )
        )


        effective = details.get(
            "effective",
            details.get(
                "effective_score",
                details.get(
                    "score",
                    0.0,
                ),
            ),
        )


        try:
            effective = float(
                effective
            )
        except Exception:
            effective = 0.0


        base = details.get(
            "base",
            details.get(
                "base_score",
                0.0,
            ),
        )


        try:
            base = float(
                base
            )
        except Exception:
            base = 0.0


        must = details.get(
            "must_tier",
            details.get(
                "must",
                0,
            ),
        )


        if isinstance(
            must,
            str,
        ):

            if "/" in must:

                try:
                    must = int(
                        must.split(
                            "/",
                            1,
                        )[0]
                    )
                except Exception:
                    must = 0


        try:
            must = float(
                must
            )
        except Exception:
            must = 0.0


        sort_key = (
            0 if hard else 1,
            must,
            effective,
            base,
            -index,
        )


        ranked.append(
            {
                "candidate":
                    candidate,

                "score":
                    details,

                "_sort_key":
                    sort_key,
            }
        )


    ranked.sort(
        key=lambda item:
            item[
                "_sort_key"
            ],
        reverse=True,
    )


    for item in ranked:

        item.pop(
            "_sort_key",
            None,
        )


    if with_scores:

        return ranked


    return [
        item[
            "candidate"
        ]
        for item in ranked
    ]





# ============================================================
# SHORTAUTOPRO VSE4.2.3 ASSOCIATION GATE
# ============================================================
#
# Último gate semântico antes do ranking final.
#
# Objetivos:
#
# - não permitir lifestyle genérico em contexto sério
# - não permitir office stock para crime scene
# - preservar imagens genericamente úteis quando têm suporte
# - reconhecer associação explícita de medicamento
# - não quebrar hard mismatch geográfico existente
# - não modificar o objeto candidato
#
# ============================================================


_vse423_score_candidate_base = _score_candidate_stage_06


_VSE423_SERIOUS_CONCEPTS = {

    "police",
    "investigation",
    "crime_scene",
    "evidence",
    "forensics",
    "court",
    "law",
    "prison",
    "hospital",
    "fire",
    "rescue",
    "military",
    "war",
}


_VSE423_SERIOUS_WORDS = {

    "police",
    "policia",
    "policial",

    "investigation",
    "investigacao",
    "investigador",

    "crime",
    "crime scene",
    "cena do crime",
    "local do crime",

    "forensic",
    "forensics",
    "pericia",
    "pericial",
    "laudo",

    "evidence",
    "evidencia",
    "prova",
    "indicio",
    "indicios",
    "vestigio",

    "court",
    "courtroom",
    "trial",
    "tribunal",
    "forum",
    "julgamento",

    "prison",
    "jail",
    "prisao",

    "war",
    "battle",
    "guerra",
    "batalha",

    "hospital",
    "emergency",
    "hospital",
    "emergencia",
}


_VSE423_MEDICINE_WORDS = set(
    MEDICINE_TERMS
) | {

    "medicine",
    "medicines",

    "medication",
    "medications",

    "pill",
    "pills",

    "tablet",
    "tablets",

    "capsule",
    "capsules",

    "drug",
    "drugs",

    "pharmacy",
    "prescription",

    "remedio",
    "remedios",

    "medicamento",
    "medicamentos",

    "comprimido",
    "comprimidos",

    "capsula",
    "capsulas",

    "farmacia",

    "receita medica",
}


def _vse423_text(value):
    """
    Extrai texto de cena/candidato sem depender
    do formato exato do objeto.
    """

    if value is None:
        return ""


    if isinstance(
        value,
        str,
    ):

        return norm(
            value
        )


    parts = []


    def add(item):

        if item is None:
            return


        if isinstance(
            item,
            str,
        ):

            item = item.strip()

            if item:
                parts.append(
                    item
                )

            return


        if isinstance(
            item,
            (
                list,
                tuple,
                set,
            ),
        ):

            for child in item:
                add(
                    child
                )

            return


        if isinstance(
            item,
            dict,
        ):

            for child in item.values():
                add(
                    child
                )

            return


    fields = (

        "texto",
        "text",
        "scene_text",

        "narration",
        "narracao",

        "visual_query",
        "query",
        "search_query",

        "must_have",
        "avoid",

        "location",
        "local",

        "title",
        "name",
        "description",
        "caption",

        "tags",
        "keywords",
        "terms",
        "subject",
        "topic",
        "category",
    )


    for field in fields:

        add(
            objget(
                value,
                field,
                None,
            )
        )


    try:

        add(
            candidate_text(
                value
            )
        )

    except Exception:

        pass


    return norm(
        " ".join(
            parts
        )
    )


def _vse423_has_any(
    text,
    terms,
):
    """
    Match semântico tolerante a plurais
    e frases compostas.
    """

    text = norm(
        text
    )

    if not text:
        return False


    padded = (
        " "
        +
        text
        +
        " "
    )


    for term in terms:

        term = norm(
            term
        )

        if not term:
            continue


        # Match de palavra/frase completa.
        if (
            " "
            +
            term
            +
            " "
        ) in padded:

            return True


        # Termos longos também aceitam
        # pequenas variações morfológicas.
        if (
            len(term) >= 7
            and
            term in text
        ):

            return True


    return False


def _vse423_reason_set(value):

    result = set()


    if not value:
        return result


    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        values = value

    else:

        values = (
            str(value)
            .replace(
                ",",
                "|",
            )
            .split("|")
        )


    for item in values:

        item = str(
            item
        ).strip()

        if item:
            result.add(
                item
            )


    return result


def _vse423_number(
    value,
    default=0.0,
):

    try:
        return float(
            value
        )
    except Exception:
        return float(
            default
        )


def _vse423_soft_effective(
    result,
):
    """
    Reconstitui um score seguro quando um
    hard mismatch falso é removido.

    Não tenta substituir o ranking principal.
    É usado somente na recuperação de uma
    associação explicitamente suportada.
    """

    base = _vse423_number(
        result.get(
            "base",
            0.0,
        )
    )

    bonus = _vse423_number(
        result.get(
            "bonus",
            0.0,
        )
    )

    penalty = _vse423_number(
        result.get(
            "penalty",
            0.0,
        )
    )

    generic_penalty = _vse423_number(
        result.get(
            "generic_penalty",
            0.0,
        )
    )

    semantic_void_penalty = _vse423_number(
        result.get(
            "semantic_void_penalty",
            0.0,
        )
    )

    adjustment = _vse423_number(
        result.get(
            "vse414_adjustment",
            0.0,
        )
    )


    return (
        base
        +
        bonus
        -
        penalty
        -
        generic_penalty
        -
        semantic_void_penalty
        +
        adjustment
    )


def _vse423_set_hard(
    result,
    reason,
):

    reasons = _vse423_reason_set(
        result.get(
            "hard_reason",
            "",
        )
    )

    reasons.add(
        reason
    )

    result[
        "hard_mismatch"
    ] = True

    result[
        "hard_reason"
    ] = "|".join(
        sorted(
            reasons
        )
    )


    current = _vse423_number(
        result.get(
            "effective",
            0.0,
        )
    )


    # Hard floor suficientemente baixo para
    # não vencer nenhum candidato normal.
    hard_value = (
        -1000000.0
        -
        abs(
            min(
                current,
                0.0,
            )
        )
    )


    result[
        "effective"
    ] = min(
        current,
        hard_value,
    )


    if "effective_score" in result:

        result[
            "effective_score"
        ] = result[
            "effective"
        ]


def _score_candidate_stage_07(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):

    result = _vse423_score_candidate_base(
        candidate,
        scene,
        state,
        *args,
        **kwargs
    )


    if not isinstance(
        result,
        dict,
    ):

        return result


    scene_text = _vse423_text(
        scene
    )

    candidate_txt = _vse423_text(
        candidate
    )


    try:

        scene_concepts = set(
            concept_hits(
                scene_text
            )
        )

    except Exception:

        scene_concepts = set()


    try:

        candidate_concepts = set(
            concept_hits(
                candidate_txt
            )
        )

    except Exception:

        candidate_concepts = set()


    concept_overlap = (
        scene_concepts
        &
        candidate_concepts
    )


    existing_semantic_hits = int(
        max(
            0.0,
            _vse423_number(
                result.get(
                    "semantic_hits",
                    0,
                )
            )
        )
    )


    semantic_support = max(
        existing_semantic_hits,
        len(
            concept_overlap
        ),
    )


    # --------------------------------------------------------
    # GEOGRAPHY
    # --------------------------------------------------------

    geo_hard = bool(
        result.get(
            "geo_hard_mismatch",
            False,
        )
        or
        result.get(
            "vse414_geo_conflict",
            False,
        )
    )


    # --------------------------------------------------------
    # MEDICINE BRIDGE
    # --------------------------------------------------------

    scene_has_medicine = _vse423_has_any(
        scene_text,
        _VSE423_MEDICINE_WORDS,
    )

    candidate_has_medicine = _vse423_has_any(
        candidate_txt,
        _VSE423_MEDICINE_WORDS,
    )


    medicine_supported = (
        scene_has_medicine
        and
        candidate_has_medicine
    )


    # --------------------------------------------------------
    # GENERIC LIFESTYLE
    # --------------------------------------------------------

    candidate_generic = _vse423_has_any(
        candidate_txt,
        GENERIC_LIFESTYLE,
    )


    serious_scene = bool(
        scene_concepts
        &
        _VSE423_SERIOUS_CONCEPTS
    ) or _vse423_has_any(
        scene_text,
        _VSE423_SERIOUS_WORDS,
    )


    # --------------------------------------------------------
    # SUPPORTED ASSOCIATION RECOVERY
    # --------------------------------------------------------

    association_supported = bool(
        concept_overlap
    ) or medicine_supported


    if (
        association_supported
        and
        not geo_hard
    ):

        hard_reasons = _vse423_reason_set(
            result.get(
                "hard_reason",
                "",
            )
        )


        removable = {
            "DOCUMENTARY_SEMANTIC_VOID",
        }


        if medicine_supported:

            removable.add(
                "MEDICINE_FALSE_ASSOCIATION"
            )


        remaining = (
            hard_reasons
            -
            removable
        )


        if medicine_supported:

            result[
                "medicine_false_association"
            ] = False


            mismatch = list(
                result.get(
                    "mismatch_reasons",
                    []
                )
                or
                []
            )

            mismatch = [
                reason
                for reason in mismatch
                if reason
                not in {
                    "UNSUPPORTED_MEDICINE_VISUAL",
                    "MEDICINE_FALSE_ASSOCIATION",
                }
            ]

            result[
                "mismatch_reasons"
            ] = mismatch


        penalties = list(
            result.get(
                "vse417_penalties",
                []
            )
            or
            []
        )

        penalties = [
            reason
            for reason in penalties
            if reason
            not in removable
        ]

        result[
            "vse417_penalties"
        ] = penalties


        # Semantic void não é válido quando
        # existe correspondência explícita.
        result[
            "semantic_void_penalty"
        ] = 0.0

        result[
            "semantic_hits"
        ] = max(
            1,
            semantic_support,
        )


        was_hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        )


        if (
            was_hard
            and
            hard_reasons
            and
            not remaining
        ):

            result[
                "hard_mismatch"
            ] = False

            result[
                "hard_reason"
            ] = ""


            current = _vse423_number(
                result.get(
                    "effective",
                    0.0,
                )
            )


            # Hard mismatch normalmente empurra
            # score para próximo de -1 milhão.
            if current < -100000.0:

                result[
                    "effective"
                ] = _vse423_soft_effective(
                    result
                )


                if "effective_score" in result:

                    result[
                        "effective_score"
                    ] = result[
                        "effective"
                    ]


    # --------------------------------------------------------
    # GENERIC STOCK HARD REJECTION
    # --------------------------------------------------------

    #
    # Contexto sério + mídia lifestyle sem nenhuma
    # ligação semântica real = rejeição forte.
    #
    # Ex:
    #
    # investigação -> mulher relaxando
    # crime scene   -> escritório lifestyle
    #
    # Mas:
    #
    # perícia em quarto -> bedroom crime investigation
    #
    # continua permitido porque há suporte semântico.
    #

    if (
        serious_scene
        and
        candidate_generic
        and
        semantic_support <= 0
        and
        not medicine_supported
    ):

        _vse423_set_hard(
            result,
            "SERIOUS_CONTEXT_GENERIC_VISUAL",
        )


    # --------------------------------------------------------
    # TELEMETRY
    # --------------------------------------------------------

    result[
        "vse423_scene_concepts"
    ] = sorted(
        scene_concepts
    )

    result[
        "vse423_candidate_concepts"
    ] = sorted(
        candidate_concepts
    )

    result[
        "vse423_concept_overlap"
    ] = sorted(
        concept_overlap
    )

    result[
        "vse423_semantic_support"
    ] = semantic_support

    result[
        "vse423_serious_scene"
    ] = serious_scene

    result[
        "vse423_generic_candidate"
    ] = candidate_generic

    result[
        "vse423_scene_medicine"
    ] = scene_has_medicine

    result[
        "vse423_candidate_medicine"
    ] = candidate_has_medicine

    result[
        "vse423_medicine_supported"
    ] = medicine_supported

    result[
        "vse423_association_supported"
    ] = association_supported


    return result




# SHORTAUTOPRO VSE4 GEO HARD MISMATCH V4.1.4

_VSE4_SCORE_CANDIDATE_BEFORE_GEO_HARD = (
    _score_candidate_stage_07
)


_VSE4_COUNTRY_GROUPS = {
    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "germany",
    "spain",
    "portugal",
    "japan",
    "china",
    "russia",
    "ukraine",
    "mexico",
    "argentina",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}


_VSE4_CITY_PARENT = {
    "sao_paulo": "brazil",
    "rio_de_janeiro": "brazil",
    "brasilia": "brazil",

    "new_york": "usa",
    "los_angeles": "usa",
    "washington_dc": "usa",

    "london": "united_kingdom",
    "paris": "france",
    "rome": "italy",
    "tokyo": "japan",
}


def _vse4_geo_conflict(
    scene,
    candidate,
):

    try:

        scene_text = candidate_text(
            scene
        )

        candidate_txt = candidate_text(
            candidate
        )

        scene_geo = set(
            geo_hits(
                scene_text
            )
        )

        candidate_geo = set(
            geo_hits(
                candidate_txt
            )
        )


        # Sem geografia explícita dos dois lados:
        # não fazemos hard block.
        if not scene_geo or not candidate_geo:

            return (
                False,
                "",
            )


        scene_countries = (
            scene_geo
            &
            _VSE4_COUNTRY_GROUPS
        )

        candidate_countries = (
            candidate_geo
            &
            _VSE4_COUNTRY_GROUPS
        )


        # País explicitamente diferente.
        if (
            scene_countries
            and
            candidate_countries
            and
            scene_countries.isdisjoint(
                candidate_countries
            )
        ):

            return (
                True,
                "GEO_COUNTRY_CONTRADICTION",
            )


        scene_cities = {
            item
            for item in scene_geo
            if item in _VSE4_CITY_PARENT
        }

        candidate_cities = {
            item
            for item in candidate_geo
            if item in _VSE4_CITY_PARENT
        }


        # Cena explicitamente cita uma cidade
        # e candidato explicitamente identifica outra.
        if (
            scene_cities
            and
            candidate_cities
            and
            scene_cities.isdisjoint(
                candidate_cities
            )
        ):

            return (
                True,
                "GEO_CITY_CONTRADICTION",
            )


        return (
            False,
            "",
        )


    except Exception:

        # Detector failure is NOT equivalent to a validated
        # "no conflict" result.
        #
        # None creates an explicit third state:
        #   False -> checked, no conflict
        #   True  -> checked, contradiction found
        #   None  -> detector could not validate
        return (
            None,
            "GEO_DETECTOR_ERROR",
        )


def _score_candidate_stage_08(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs,
):

    result = (
        _VSE4_SCORE_CANDIDATE_BEFORE_GEO_HARD(
            candidate,
            scene,
            state,
            *args,
            **kwargs,
        )
    )


    if not isinstance(
        result,
        dict,
    ):

        return result


    conflict, reason = (
        _vse4_geo_conflict(
            scene,
            candidate,
        )
    )


    # --------------------------------------------------
    # TRI-STATE GEO GUARD
    # --------------------------------------------------
    #
    # False:
    # detector executou normalmente e não encontrou
    # contradição.
    if conflict is False:

        return result


    # None:
    # detector falhou. Isso não é uma contradição
    # comprovada, mas também NÃO é validação segura.
    #
    # Fail closed for release/ranking while preserving
    # a distinct diagnostic state from GEO_CONFLICT.
    if conflict is None:

        result = dict(
            result
        )

        result[
            "hard_mismatch"
        ] = True

        result[
            "hard_reason"
        ] = (
            reason
            or
            "GEO_DETECTOR_ERROR"
        )

        result[
            "geo_conflict"
        ] = None

        result[
            "geo_detector_error"
        ] = True

        result[
            "geo_validation_status"
        ] = "ERROR"

        try:

            old_effective = float(
                result.get(
                    "effective",
                    0.0,
                )
            )

        except Exception:

            old_effective = 0.0

        result[
            "effective_before_geo_guard_error"
        ] = old_effective

        # Mantém distinção entre:
        #
        # detector error    -> -500000
        # conflict proven   -> -1000000
        #
        # Ambos ficam abaixo de candidatos validados,
        # mas preservamos a causa correta.
        result[
            "effective"
        ] = min(
            old_effective,
            -500000.0,
        )

        return result


    # conflict is True:
    # contradição geográfica comprovada.

    # Copia para não modificar estrutura compartilhada.
    result = dict(
        result
    )


    result[
        "hard_mismatch"
    ] = True

    result[
        "hard_reason"
    ] = reason

    result[
        "geo_conflict"
    ] = True


    # Hard contradiction deve ficar abaixo de
    # qualquer candidato semanticamente plausível,
    # mesmo quando o score bruto do stock provider é alto.
    try:

        old_effective = float(
            result.get(
                "effective",
                0.0,
            )
        )

    except Exception:

        old_effective = 0.0


    result[
        "effective_before_geo_hard"
    ] = old_effective


    result[
        "effective"
    ] = min(
        old_effective,
        -1000000.0,
    )


    return result



# SHORTAUTOPRO SEMANTIC SAFETY V5

_VSE5_SCORE_CORE = _score_candidate_stage_08


_VSE5_GEO_PARENT = {

    "sao_paulo": "brazil",
    "rio_de_janeiro": "brazil",
    "brasilia": "brazil",

    "new_york": "usa",
    "los_angeles": "usa",
    "washington_dc": "usa",

    "london": "united_kingdom",

    "paris": "france",

    "rome": "italy",

    "tokyo": "japan",
}


_VSE5_COUNTRIES = {

    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "germany",
    "spain",
    "portugal",
    "japan",
    "china",
    "russia",
    "ukraine",
    "mexico",
    "argentina",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}


_VSE5_DOCUMENTARY = {

    "police",
    "investigation",
    "crime_scene",
    "evidence",
    "forensics",
    "court",
    "law",
    "prison",
    "news",
    "archive",
    "military",
    "war",
    "laboratory",
    "hospital",
    "space",
    "rocket",
}


def _vse5_geo_roots(groups):

    roots = set()

    for group in groups:

        if group in _VSE5_COUNTRIES:

            roots.add(group)

            continue


        parent = _VSE5_GEO_PARENT.get(
            group
        )

        if parent:
            roots.add(parent)


    return roots


def _vse5_geo_conflict(
    scene_groups,
    candidate_groups,
):

    if (
        not scene_groups
        or
        not candidate_groups
    ):

        return False


    sr = _vse5_geo_roots(
        scene_groups
    )

    cr = _vse5_geo_roots(
        candidate_groups
    )


    if (
        sr
        and
        cr
        and
        sr.isdisjoint(cr)
    ):

        return True


    scene_specific = {
        x
        for x in scene_groups
        if x in _VSE5_GEO_PARENT
    }

    candidate_specific = {
        x
        for x in candidate_groups
        if x in _VSE5_GEO_PARENT
    }


    if (
        scene_specific
        and
        candidate_specific
    ):

        scene_parents = {
            _VSE5_GEO_PARENT[x]
            for x in scene_specific
        }

        candidate_parents = {
            _VSE5_GEO_PARENT[x]
            for x in candidate_specific
        }

        if scene_parents.isdisjoint(
            candidate_parents
        ):
            return True


    return False


def score_candidate(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):

    result = _VSE5_SCORE_CORE(
        candidate,
        scene,
        state,
        *args,
        **kwargs
    )


    if not isinstance(
        result,
        dict,
    ):
        return result


    scene_text = candidate_text(
        scene
    )

    media_text = candidate_text(
        candidate
    )


    scene_geo = set(
        geo_hits(
            scene_text
        )
    )

    media_geo = set(
        geo_hits(
            media_text
        )
    )


    scene_tokens = set(
        tokens(
            scene_text
        )
    )

    media_tokens = set(
        tokens(
            media_text
        )
    )


    scene_concepts = set(
        concept_hits(
            scene_text
        )
    )


    reasons = list(
        result.get(
            "safety_reasons",
            [],
        )
        or
        []
    )


    hard = bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )


    penalty = 0.0


    # --------------------------------------------------------
    # Geografia incompatível.
    # --------------------------------------------------------

    if _vse5_geo_conflict(
        scene_geo,
        media_geo,
    ):

        hard = True

        reasons.append(
            "GEO_CONTRADICTION"
        )


    # --------------------------------------------------------
    # Medicamento sem contexto médico.
    # --------------------------------------------------------

    medicine = {
        norm(x)
        for x in MEDICINE_TERMS
    }

    medicine_hits = (
        media_tokens
        &
        medicine
    )

    scene_medicine = (
        scene_tokens
        &
        medicine
    )


    if (
        medicine_hits
        and
        not scene_medicine
        and
        (
            scene_concepts
            &
            _VSE5_DOCUMENTARY
        )
    ):

        hard = True

        reasons.append(
            "FALSE_MEDICAL_ASSOCIATION"
        )


    # --------------------------------------------------------
    # Stock lifestyle genérico.
    # Soft penalty, não bloqueio absoluto.
    # --------------------------------------------------------

    lifestyle = {
        norm(x)
        for x in GENERIC_LIFESTYLE
    }

    lifestyle_hits = (
        media_tokens
        &
        lifestyle
    )


    if (
        lifestyle_hits
        and
        (
            scene_concepts
            &
            _VSE5_DOCUMENTARY
        )
    ):

        penalty += (
            85.0
            +
            min(
                45.0,
                12.0
                *
                len(
                    lifestyle_hits
                ),
            )
        )

        reasons.append(
            "GENERIC_LIFESTYLE"
        )


    result[
        "hard_mismatch"
    ] = hard


    result[
        "safety_reasons"
    ] = sorted(
        set(reasons)
    )


    current_effective = result.get(
        "effective",
        result.get(
            "score",
            0.0,
        ),
    )


    try:
        current_effective = float(
            current_effective
        )

    except Exception:
        current_effective = 0.0


    current_effective -= penalty


    if hard:

        current_effective -= 10000.0


    result[
        "effective"
    ] = current_effective


    result[
        "safety_penalty"
    ] = penalty


    return result




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

    scene = (
        "Investigação em apartamento "
        "na cidade de São Paulo"
    )

    wrong = {
        "provider": "Pixabay",
        "tipo": "foto",
        "title": "Empire State Building New York",
        "must": "2/2",
        "score": 220,
        "width": 1920,
        "height": 1080,
    }

    correct = {
        "provider": "Wikimedia",
        "tipo": "foto",
        "title": "Apartment building Sao Paulo Brazil",
        "must": "1/2",
        "score": 120,
        "width": 1920,
        "height": 1080,
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

    assert a[
        "hard_mismatch"
    ] is True

    assert b[
        "hard_mismatch"
    ] is False

    assert b[
        "effective"
    ] > a[
        "effective"
    ]

    print(
        "VSE4_SELF_TEST=PASS"
    )

    print(
        "GEO_CONTRADICTION_TEST=PASS"
    )

    print(
        "SEMANTIC_SCORING_TEST=PASS"
    )


if __name__ == "__main__":
    self_test()

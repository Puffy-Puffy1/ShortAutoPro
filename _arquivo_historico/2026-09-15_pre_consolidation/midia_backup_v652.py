#!/usr/bin/env python3

import os
import sys
import time
import random
import shutil
import re
import json
import requests
from datetime import date


# ==================================================
# CONFIG
# ==================================================

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "")
COVERR_KEY = os.getenv("COVERR_API_KEY", "")

USAR_PEXELS = os.getenv(
    "SHORT_USAR_PEXELS",
    "1"
) == "1"

USAR_PIXABAY = os.getenv(
    "SHORT_USAR_PIXABAY",
    "1"
) == "1"

USAR_COVERR = os.getenv(
    "SHORT_USAR_COVERR",
    "1"
) == "1"

USAR_LOCAL = os.getenv(
    "SHORT_USAR_LOCAL",
    "1"
) == "1"

USAR_VIDEOS = os.getenv(
    "SHORT_USAR_VIDEOS",
    "1"
) == "1"

try:
    VIDEO_META = int(
        os.getenv(
            "SHORT_VIDEO_META",
            "5"
        )
    )
except ValueError:
    VIDEO_META = 5

VIDEO_META = max(
    2,
    min(VIDEO_META, 8)
)

try:
    VIDEO_BONUS = float(
        os.getenv(
            "SHORT_VIDEO_BONUS",
            "18"
        )
    )
except ValueError:
    VIDEO_BONUS = 18.0

try:
    VIDEO_TOLERANCIA = float(
        os.getenv(
            "SHORT_VIDEO_TOLERANCIA",
            "18"
        )
    )
except ValueError:
    VIDEO_TOLERANCIA = 18.0


# ==================================================
# PATHS
# ==================================================

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

SAIDA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

LOCAL_DIR = os.path.join(
    BASE,
    "midia_local"
)

os.makedirs(
    SAIDA_DIR,
    exist_ok=True
)

os.makedirs(
    LOCAL_DIR,
    exist_ok=True
)

if not os.path.exists(SCENE_MAP):
    sys.exit(
        f"ERRO: scene_map não encontrado:\n{SCENE_MAP}"
    )

try:
    with open(
        SCENE_MAP,
        "r",
        encoding="utf-8"
    ) as f:
        mapa = json.load(f)

    cenas = mapa.get(
        "scenes",
        []
    )

except Exception as e:
    sys.exit(
        f"ERRO lendo scene_map: {e}"
    )

if not cenas:
    sys.exit(
        "ERRO: scene_map sem cenas."
    )


# ==================================================
# LIMPAR MÍDIA ANTIGA
# ==================================================

for nome in os.listdir(
    SAIDA_DIR
):

    caminho = os.path.join(
        SAIDA_DIR,
        nome
    )

    if nome.lower().endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".mp4"
        )
    ):
        try:
            os.remove(caminho)
        except Exception:
            pass


# ==================================================
# TEXTO
# ==================================================

STOP = {
    "a", "an", "the", "of", "in",
    "on", "at", "with", "and", "or",
    "to", "for", "from", "by",
    "cinematic", "dramatic", "moody",
    "dark", "night", "close", "up",
    "shot", "view", "scene"
}


def normalizar(texto):

    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
    )


def tokenizar(texto):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
        if x not in STOP
    }


def similaridade(
    a,
    b
):

    ta = tokenizar(a)
    tb = tokenizar(b)

    if not ta:
        return 0.0

    return (
        len(
            ta.intersection(tb)
        )
        / len(ta)
    )


def similaridade_conjuntos(
    a,
    b
):

    ta = tokenizar(a)
    tb = tokenizar(b)

    if not ta or not tb:
        return 0.0

    uniao = ta.union(tb)

    if not uniao:
        return 0.0

    return (
        len(
            ta.intersection(tb)
        )
        / len(uniao)
    )


def termo_presente(
    descricao,
    termo
):

    desc = normalizar(
        descricao
    )

    termo_n = normalizar(
        termo
    )

    if not termo_n:
        return False

    if termo_n in desc:
        return True

    termo_tokens = tokenizar(
        termo_n
    )

    desc_tokens = tokenizar(
        desc
    )

    if not termo_tokens:
        return False

    encontrados = len(
        termo_tokens.intersection(
            desc_tokens
        )
    )

    return (
        encontrados
        / len(termo_tokens)
    ) >= 0.75


# ==================================================
# SCORE DE RELEVÂNCIA
# ==================================================

def avaliar_relevancia(
    busca,
    descricao,
    must_have,
    avoid
):

    score = (
        similaridade(
            busca,
            descricao
        )
        * 60
    )

    must_hits = 0

    for termo in must_have:

        if termo_presente(
            descricao,
            termo
        ):
            must_hits += 1
            score += 40

        else:
            score -= 20


    avoid_hits = 0

    for termo in avoid:

        if termo_presente(
            descricao,
            termo
        ):
            avoid_hits += 1
            score -= 55


    return (
        score,
        must_hits,
        avoid_hits
    )


# ==================================================
# DOWNLOAD
# ==================================================

def baixar(
    url,
    destino,
    timeout=120
):

    try:

        r = requests.get(
            url,
            timeout=timeout,
            stream=True
        )

        r.raise_for_status()

        with open(
            destino,
            "wb"
        ) as f:

            for bloco in r.iter_content(
                chunk_size=256 * 1024
            ):

                if bloco:
                    f.write(bloco)

        return (
            os.path.exists(destino)
            and os.path.getsize(destino) > 1000
        )

    except Exception:

        if os.path.exists(destino):
            try:
                os.remove(destino)
            except Exception:
                pass

        return False


# ==================================================
# ANTI REPETIÇÃO
# ==================================================

usados = set()


def penalidade_usado(
    fonte,
    ident
):

    if (
        fonte,
        str(ident)
    ) in usados:
        return -120

    return 0


def marcar_usado(
    fonte,
    ident
):

    usados.add(
        (
            fonte,
            str(ident)
        )
    )


# ==================================================
# PEXELS VIDEO
# ==================================================

def pexels_video(
    busca,
    must_have,
    avoid
):

    if not USAR_PEXELS or not PEXELS_KEY:
        return []

    try:

        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={
                "Authorization":
                PEXELS_KEY
            },
            params={
                "query": busca,
                "orientation": "portrait",
                "per_page": 20
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    saida = []

    for item in r.json().get(
        "videos",
        []
    ):

        ident = item.get("id")

        descricao = " ".join(
            [
                str(item.get("url", "")),
                str(
                    item.get(
                        "user",
                        {}
                    ).get(
                        "name",
                        ""
                    )
                )
            ]
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        for arq in item.get(
            "video_files",
            []
        ):

            url = arq.get("link")

            if not url:
                continue

            w = arq.get(
                "width"
            ) or 0

            h = arq.get(
                "height"
            ) or 0

            score = rel

            if h > w:
                score += 28

            if h >= 1280:
                score += 16

            if w >= 720:
                score += 8

            score += penalidade_usado(
                "Pexels",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits": must_hits,
                    "avoid_hits": avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte": "Pexels",
                    "tipo": "vídeo",
                    "descricao": descricao
                }
            )

    return saida


# ==================================================
# PEXELS FOTO
# ==================================================

def pexels_foto(
    busca,
    must_have,
    avoid
):

    if not USAR_PEXELS or not PEXELS_KEY:
        return []

    try:

        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={
                "Authorization":
                PEXELS_KEY
            },
            params={
                "query": busca,
                "orientation": "portrait",
                "per_page": 25
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    saida = []

    for item in r.json().get(
        "photos",
        []
    ):

        ident = item.get("id")

        descricao = str(
            item.get(
                "alt",
                ""
            )
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        src = item.get(
            "src",
            {}
        )

        url = (
            src.get("portrait")
            or src.get("large2x")
            or src.get("large")
            or src.get("original")
        )

        if not url:
            continue

        w = item.get(
            "width"
        ) or 0

        h = item.get(
            "height"
        ) or 0

        score = rel

        if h > w:
            score += 28

        if h >= 1280:
            score += 16

        score += penalidade_usado(
            "Pexels",
            ident
        )

        saida.append(
            {
                "score": score,
                "must_hits": must_hits,
                "avoid_hits": avoid_hits,
                "id": ident,
                "url": url,
                "fonte": "Pexels",
                "tipo": "foto",
                "descricao": descricao
            }
        )

    return saida


# ==================================================
# PIXABAY VIDEO
# ==================================================

def pixabay_video(
    busca,
    must_have,
    avoid
):

    if not USAR_PIXABAY or not PIXABAY_KEY:
        return []

    try:

        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_KEY,
                "q": busca,
                "video_type": "film",
                "safesearch": "true",
                "order": "popular",
                "per_page": 20
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    saida = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = item.get("id")

        descricao = " ".join(
            [
                str(item.get("tags", "")),
                str(item.get("pageURL", ""))
            ]
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        formatos = item.get(
            "videos",
            {}
        )

        for chave in [
            "large",
            "medium",
            "small",
            "tiny"
        ]:

            info = formatos.get(
                chave,
                {}
            )

            url = info.get("url")

            if not url:
                continue

            w = info.get(
                "width"
            ) or 0

            h = info.get(
                "height"
            ) or 0

            score = rel

            if h > w:
                score += 28

            if h >= 720:
                score += 12

            if h >= 1080:
                score += 8

            score += penalidade_usado(
                "Pixabay",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits": must_hits,
                    "avoid_hits": avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte": "Pixabay",
                    "tipo": "vídeo",
                    "descricao": descricao
                }
            )

    return saida


# ==================================================
# PIXABAY FOTO
# ==================================================

def pixabay_foto(
    busca,
    must_have,
    avoid
):

    if not USAR_PIXABAY or not PIXABAY_KEY:
        return []

    try:

        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_KEY,
                "q": busca,
                "image_type": "photo",
                "orientation": "vertical",
                "safesearch": "true",
                "order": "popular",
                "per_page": 25
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    saida = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = item.get("id")

        descricao = str(
            item.get(
                "tags",
                ""
            )
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        url = (
            item.get("largeImageURL")
            or item.get("webformatURL")
        )

        if not url:
            continue

        w = item.get(
            "imageWidth"
        ) or 0

        h = item.get(
            "imageHeight"
        ) or 0

        score = rel

        if h > w:
            score += 28

        if h >= 1280:
            score += 16

        score += penalidade_usado(
            "Pixabay",
            ident
        )

        saida.append(
            {
                "score": score,
                "must_hits": must_hits,
                "avoid_hits": avoid_hits,
                "id": ident,
                "url": url,
                "fonte": "Pixabay",
                "tipo": "foto",
                "descricao": descricao
            }
        )

    return saida


# ==================================================
# COVERR
# ==================================================

def coverr_video(
    busca,
    must_have,
    avoid
):

    if not USAR_COVERR or not COVERR_KEY:
        return []

    try:

        r = requests.get(
            "https://api.coverr.co/videos",
            headers={
                "Authorization":
                f"Bearer {COVERR_KEY}"
            },
            params={
                "query": busca,
                "page": 0,
                "page_size": 20,
                "urls": "true"
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    saida = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = (
            item.get("id")
            or item.get("slug")
            or item.get("title")
        )

        descricao = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("description", "")),
                str(item.get("tags", ""))
            ]
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        urls = item.get(
            "urls",
            {}
        )

        if not isinstance(
            urls,
            dict
        ):
            continue

        for _, url in urls.items():

            if not isinstance(
                url,
                str
            ):
                continue

            score = rel

            if ".mp4" in url.lower():
                score += 8

            score += penalidade_usado(
                "Coverr",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits": must_hits,
                    "avoid_hits": avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte": "Coverr",
                    "tipo": "vídeo",
                    "descricao": descricao
                }
            )

    return saida


# ==================================================
# LOCAL
# ==================================================

def buscar_local(
    preferir_video
):

    if not USAR_LOCAL:
        return None

    videos = []
    fotos = []

    for nome in os.listdir(
        LOCAL_DIR
    ):

        caminho = os.path.join(
            LOCAL_DIR,
            nome
        )

        ext = os.path.splitext(
            nome
        )[1].lower()

        if ext == ".mp4":
            videos.append(caminho)

        elif ext in [
            ".jpg",
            ".jpeg",
            ".png"
        ]:
            fotos.append(caminho)

    random.shuffle(videos)
    random.shuffle(fotos)

    candidatos = (
        videos + fotos
        if preferir_video
        else fotos + videos
    )

    if not candidatos:
        return None

    return candidatos[0]


# ==================================================
# FILTRO DE QUALIDADE
# ==================================================

def aceitavel(
    candidato,
    must_total
):

    hits = candidato[
        "must_hits"
    ]

    avoid_hits = candidato[
        "avoid_hits"
    ]

    score = candidato[
        "score"
    ]

    if avoid_hits >= 2:
        return False

    if must_total > 0 and hits == 0:
        return False

    if (
        must_total > 0
        and hits == must_total
    ):
        return True

    if (
        must_total > 0
        and hits >= 1
        and score >= 45
    ):
        return True

    if (
        must_total == 0
        and score >= 20
    ):
        return True

    return False


# ==================================================
# MOTION PREFERENCE
# ==================================================

def escolher_com_movimento(
    candidatos,
    must_total,
    videos_usados,
    cenas_restantes
):

    validos = [
        c
        for c in candidatos
        if aceitavel(
            c,
            must_total
        )
    ]

    if not validos:
        return None


    # Penaliza repetição semântica
    # com a mídia escolhida anteriormente.

    for c in validos:

        if descricao_anterior:

            repeticao = (
                similaridade_conjuntos(
                    descricao_anterior,
                    c.get(
                        "descricao",
                        ""
                    )
                )
            )

            if repeticao >= 0.55:
                c["score"] -= 25

            elif repeticao >= 0.35:
                c["score"] -= 10


    validos.sort(
        key=lambda x: (
            x["must_hits"],
            -x["avoid_hits"],
            x["score"]
        ),
        reverse=True
    )


    melhor = validos[0]


    # ----------------------------------
    # META DE VÍDEOS
    # ----------------------------------

    videos_necessarios = max(
        0,
        VIDEO_META
        - videos_usados
    )


    precisa_video = (
        videos_necessarios
        >= cenas_restantes
    )


    videos_validos = [
        c
        for c in validos
        if c["tipo"] == "vídeo"
    ]


    if not videos_validos:
        return melhor


    videos_validos.sort(
        key=lambda x: (
            x["must_hits"],
            -x["avoid_hits"],
            x["score"]
        ),
        reverse=True
    )


    melhor_video = (
        videos_validos[0]
    )


    # Se já estamos atrasados na meta,
    # vídeo válido ganha prioridade.

    if precisa_video:
        return melhor_video


    # Se o melhor já é vídeo,
    # mantém.

    if melhor[
        "tipo"
    ] == "vídeo":

        return melhor


    # Compara foto x vídeo.
    # Vídeo pode perder alguns pontos,
    # desde que não perca must_have.

    if (
        melhor_video[
            "must_hits"
        ]
        >= melhor[
            "must_hits"
        ]
    ):

        diferenca = (
            melhor["score"]
            - melhor_video["score"]
        )

        if diferenca <= VIDEO_TOLERANCIA:

            melhor_video[
                "score"
            ] += VIDEO_BONUS

            return melhor_video


    return melhor


# ==================================================
# EXECUÇÃO
# ==================================================

print()
print("================================")
print("MOTION PREFERENCE V6.5.2")
print("================================")
print()

print(
    f"Meta vídeos: "
    f"{VIDEO_META}/{len(cenas)}"
)

print(
    f"Tolerância vídeo: "
    f"{VIDEO_TOLERANCIA:.1f}"
)

print()


total = 0
videos_total = 0
fotos_total = 0

descricao_anterior = ""

contagem = {
    "Pexels": 0,
    "Pixabay": 0,
    "Coverr": 0,
    "Local": 0
}


for numero, cena in enumerate(
    cenas,
    start=1
):

    busca = str(
        cena.get(
            "query",
            ""
        )
    ).strip()

    must_have = [
        str(x).strip().lower()
        for x in cena.get(
            "must_have",
            []
        )
        if str(x).strip()
    ]

    avoid = [
        str(x).strip().lower()
        for x in cena.get(
            "avoid",
            []
        )
        if str(x).strip()
    ]


    print()
    print(
        f"[{numero}/{len(cenas)}] "
        f"{busca}"
    )

    print(
        f"  MUST: "
        f"{', '.join(must_have)}"
    )


    # =================================
    # TODAS AS FONTES COMPETEM
    # =================================

    todos = []

    if USAR_VIDEOS:

        todos.extend(
            pexels_video(
                busca,
                must_have,
                avoid
            )
        )

        todos.extend(
            pixabay_video(
                busca,
                must_have,
                avoid
            )
        )

        todos.extend(
            coverr_video(
                busca,
                must_have,
                avoid
            )
        )


    todos.extend(
        pexels_foto(
            busca,
            must_have,
            avoid
        )
    )

    todos.extend(
        pixabay_foto(
            busca,
            must_have,
            avoid
        )
    )


    # =================================
    # TOP 3 BRUTO
    # =================================

    todos.sort(
        key=lambda x: (
            x["must_hits"],
            -x["avoid_hits"],
            x["score"]
        ),
        reverse=True
    )


    for pos, c in enumerate(
        todos[:3],
        1
    ):

        print(
            f"  TOP{pos}: "
            f"{c['fonte']} "
            f"{c['tipo']} "
            f"score={c['score']:.1f} "
            f"must={c['must_hits']}/"
            f"{len(must_have)}"
        )


    cenas_restantes = (
        len(cenas)
        - numero
        + 1
    )


    escolhido = escolher_com_movimento(
        todos,
        len(must_have),
        videos_total,
        cenas_restantes
    )


    sucesso = False


    if escolhido:

        ext = (
            ".mp4"
            if escolhido[
                "tipo"
            ] == "vídeo"
            else ".jpg"
        )

        destino = os.path.join(
            SAIDA_DIR,
            f"scene_{numero:02d}{ext}"
        )

        if baixar(
            escolhido[
                "url"
            ],
            destino
        ):

            sucesso = True

            marcar_usado(
                escolhido[
                    "fonte"
                ],
                escolhido[
                    "id"
                ]
            )


    # =================================
    # FALLBACK LOCAL
    # =================================

    if not sucesso:

        origem = buscar_local(
            videos_total
            < VIDEO_META
        )

        if origem:

            ext = os.path.splitext(
                origem
            )[1].lower()

            destino = os.path.join(
                SAIDA_DIR,
                f"scene_{numero:02d}{ext}"
            )

            try:

                shutil.copy2(
                    origem,
                    destino
                )

                sucesso = True

                escolhido = {
                    "fonte": "Local",
                    "tipo":
                        (
                            "vídeo"
                            if ext == ".mp4"
                            else "foto"
                        ),
                    "score": 0,
                    "must_hits": 0,
                    "avoid_hits": 0,
                    "descricao":
                        os.path.basename(
                            origem
                        )
                }

            except Exception:
                sucesso = False


    if sucesso:

        fonte = escolhido[
            "fonte"
        ]

        tipo = escolhido[
            "tipo"
        ]

        descricao_anterior = (
            escolhido.get(
                "descricao",
                ""
            )
        )


        if tipo == "vídeo":
            videos_total += 1
        else:
            fotos_total += 1


        contagem[
            fonte
        ] += 1

        total += 1


        print(
            f"  ESCOLHIDO: "
            f"{fonte} / {tipo}"
        )

        print(
            f"  score="
            f"{escolhido['score']:.1f} "
            f"must="
            f"{escolhido['must_hits']}/"
            f"{len(must_have)}"
        )

        print(
            f"  MOVIMENTO: "
            f"{videos_total}/"
            f"{VIDEO_META} vídeos"
        )


    else:

        print(
            "  ERRO: nenhuma mídia disponível."
        )


    time.sleep(
        0.20
    )


# ==================================================
# RESUMO
# ==================================================

print()
print("================================")
print("V6.5.2 - RESUMO")
print("================================")
print()

print(
    f"Total: "
    f"{total}/{len(cenas)}"
)

print(
    f"Pexels: "
    f"{contagem['Pexels']}"
)

print(
    f"Pixabay: "
    f"{contagem['Pixabay']}"
)

print(
    f"Coverr: "
    f"{contagem['Coverr']}"
)

print(
    f"Local: "
    f"{contagem['Local']}"
)

print(
    f"Vídeos: "
    f"{videos_total}"
)

print(
    f"Fotos: "
    f"{fotos_total}"
)

print()


if total < 6:

    sys.exit(
        "ERRO: poucas mídias disponíveis."
    )

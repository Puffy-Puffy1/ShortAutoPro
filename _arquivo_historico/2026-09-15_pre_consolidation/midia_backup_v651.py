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
    VIDEO_A_CADA = int(
        os.getenv(
            "SHORT_VIDEO_A_CADA",
            "2"
        )
    )
except ValueError:
    VIDEO_A_CADA = 2

VIDEO_A_CADA = max(
    1,
    VIDEO_A_CADA
)


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


if not os.path.exists(
    SCENE_MAP
):

    sys.exit(
        f"ERRO: scene_map não encontrado:\n"
        f"{SCENE_MAP}"
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
# TEXTO / SCORE
# ==================================================

STOP = {
    "a", "an", "the", "of", "in",
    "on", "at", "with", "and", "or",
    "to", "for", "from", "by",
    "cinematic", "dramatic", "moody",
    "dark", "night", "close", "up",
    "shot", "view"
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
    busca,
    descricao
):

    query_tokens = tokenizar(
        busca
    )

    desc_tokens = tokenizar(
        descricao
    )

    if not query_tokens:
        return 0.0

    return (
        len(
            query_tokens.intersection(
                desc_tokens
            )
        )
        / len(query_tokens)
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

    # frase exata primeiro
    if termo_n in desc:
        return True

    # se for uma frase composta,
    # exige pelo menos 75% das palavras
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

    proporcao = (
        encontrados
        / len(termo_tokens)
    )

    return proporcao >= 0.75


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
            and os.path.getsize(
                destino
            ) > 1000
        )

    except Exception:

        if os.path.exists(
            destino
        ):

            try:
                os.remove(destino)
            except Exception:
                pass

        return False


# ==================================================
# ANTI REPETIÇÃO NO MESMO SHORT
# ==================================================

usados = set()


def penalidade_usado(
    fonte,
    ident
):

    chave = (
        fonte,
        str(ident)
    )

    if chave in usados:
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

    if (
        not USAR_PEXELS
        or not PEXELS_KEY
    ):
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
                "orientation":
                    "portrait",
                "per_page": 20
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    candidatos = []

    for item in r.json().get(
        "videos",
        []
    ):

        ident = item.get("id")

        # IMPORTANTE:
        # não adicionamos a query aqui.
        descricao = " ".join(
            [
                str(
                    item.get(
                        "url",
                        ""
                    )
                ),
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

            url = arq.get(
                "link"
            )

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
                "pexels_video",
                ident
            )

            candidatos.append(
                {
                    "score": score,
                    "must_hits":
                        must_hits,
                    "avoid_hits":
                        avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte":
                        "Pexels",
                    "tipo":
                        "vídeo",
                    "descricao":
                        descricao
                }
            )

    return candidatos


# ==================================================
# PEXELS FOTO
# ==================================================

def pexels_foto(
    busca,
    must_have,
    avoid
):

    if (
        not USAR_PEXELS
        or not PEXELS_KEY
    ):
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
                "orientation":
                    "portrait",
                "per_page": 25
            },
            timeout=30
        )

    except Exception:
        return []

    if not r.ok:
        return []

    candidatos = []

    for item in r.json().get(
        "photos",
        []
    ):

        ident = item.get(
            "id"
        )

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
            "pexels_foto",
            ident
        )

        candidatos.append(
            {
                "score": score,
                "must_hits":
                    must_hits,
                "avoid_hits":
                    avoid_hits,
                "id": ident,
                "url": url,
                "fonte":
                    "Pexels",
                "tipo":
                    "foto",
                "descricao":
                    descricao
            }
        )

    return candidatos


# ==================================================
# PIXABAY VIDEO
# ==================================================

def pixabay_video(
    busca,
    must_have,
    avoid
):

    if (
        not USAR_PIXABAY
        or not PIXABAY_KEY
    ):
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

    candidatos = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = item.get(
            "id"
        )

        descricao = " ".join(
            [
                str(
                    item.get(
                        "tags",
                        ""
                    )
                ),
                str(
                    item.get(
                        "pageURL",
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

            url = info.get(
                "url"
            )

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
                "pixabay_video",
                ident
            )

            candidatos.append(
                {
                    "score": score,
                    "must_hits":
                        must_hits,
                    "avoid_hits":
                        avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte":
                        "Pixabay",
                    "tipo":
                        "vídeo",
                    "descricao":
                        descricao
                }
            )

    return candidatos


# ==================================================
# PIXABAY FOTO
# ==================================================

def pixabay_foto(
    busca,
    must_have,
    avoid
):

    if (
        not USAR_PIXABAY
        or not PIXABAY_KEY
    ):
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

    candidatos = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = item.get(
            "id"
        )

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
            item.get(
                "largeImageURL"
            )
            or item.get(
                "webformatURL"
            )
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
            "pixabay_foto",
            ident
        )

        candidatos.append(
            {
                "score": score,
                "must_hits":
                    must_hits,
                "avoid_hits":
                    avoid_hits,
                "id": ident,
                "url": url,
                "fonte":
                    "Pixabay",
                "tipo":
                    "foto",
                "descricao":
                    descricao
            }
        )

    return candidatos


# ==================================================
# COVERR
# ==================================================

def coverr_video(
    busca,
    must_have,
    avoid
):

    if (
        not USAR_COVERR
        or not COVERR_KEY
    ):
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

    candidatos = []

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
                str(
                    item.get(
                        "title",
                        ""
                    )
                ),
                str(
                    item.get(
                        "description",
                        ""
                    )
                ),
                str(
                    item.get(
                        "tags",
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
                "coverr",
                ident
            )

            candidatos.append(
                {
                    "score": score,
                    "must_hits":
                        must_hits,
                    "avoid_hits":
                        avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte":
                        "Coverr",
                    "tipo":
                        "vídeo",
                    "descricao":
                        descricao
                }
            )

    return candidatos


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
            videos.append(
                caminho
            )

        elif ext in [
            ".jpg",
            ".jpeg",
            ".png"
        ]:
            fotos.append(
                caminho
            )

    random.shuffle(
        videos
    )

    random.shuffle(
        fotos
    )

    candidatos = (
        videos + fotos
        if preferir_video
        else fotos + videos
    )

    if not candidatos:
        return None

    return candidatos[0]


# ==================================================
# QUALIDADE DO CANDIDATO
# ==================================================

def candidato_aceitavel(
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

    # qualquer avoid forte já é suspeito
    if avoid_hits >= 2:
        return False

    # nenhum must encontrado:
    # rejeita se havia regra obrigatória
    if (
        must_total > 0
        and hits == 0
    ):
        return False

    # todos os must encontrados
    if (
        must_total > 0
        and hits == must_total
    ):
        return True

    # encontrou parte dos must:
    # exige score mais alto
    if (
        must_total > 0
        and hits >= 1
        and score >= 45
    ):
        return True

    # cena sem must_have
    if (
        must_total == 0
        and score >= 20
    ):
        return True

    return False


# ==================================================
# EXECUÇÃO
# ==================================================

print()
print("================================")
print("REAL RELEVANCE SCORING V6.5.1")
print("================================")
print()

print(
    f"Pexels: "
    f"{'ON' if USAR_PEXELS else 'OFF'}"
)

print(
    f"Pixabay: "
    f"{'ON' if USAR_PIXABAY else 'OFF'}"
)

print(
    f"Coverr: "
    f"{'ON' if USAR_COVERR else 'OFF'}"
)

print()


total = 0

contagem = {
    "Pexels": 0,
    "Pixabay": 0,
    "Coverr": 0,
    "Local": 0
}

videos_total = 0
fotos_total = 0


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


    preferir_video = (
        USAR_VIDEOS
        and (
            (numero - 1)
            % VIDEO_A_CADA
            == 0
        )
    )


    print()
    print(
        f"[{numero}/{len(cenas)}] "
        f"{busca}"
    )

    print(
        f"  MUST: "
        f"{', '.join(must_have)}"
    )

    if avoid:

        print(
            f"  AVOID: "
            f"{', '.join(avoid)}"
        )


    todos = []


    # ==================================================
    # FAZ AS FONTES COMPETIREM
    # ==================================================

    if preferir_video:

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


    # Sempre busca fotos também.
    # Assim uma foto muito relevante pode vencer
    # um vídeo ruim.

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


    # ==================================================
    # BONUS DE VÍDEO
    # ==================================================

    for candidato in todos:

        if (
            preferir_video
            and candidato[
                "tipo"
            ] == "vídeo"
        ):

            candidato[
                "score"
            ] += 8


    # ==================================================
    # ORDENAR GLOBALMENTE
    # ==================================================

    todos.sort(
        key=lambda x: (
            x["must_hits"],
            -x["avoid_hits"],
            x["score"]
        ),
        reverse=True
    )


    # Mostra top 3 para diagnóstico
    for pos, c in enumerate(
        todos[:3],
        start=1
    ):

        print(
            f"  TOP{pos}: "
            f"{c['fonte']} "
            f"{c['tipo']} "
            f"score={c['score']:.1f} "
            f"must={c['must_hits']}/"
            f"{len(must_have)} "
            f"avoid={c['avoid_hits']}"
        )


    sucesso = False
    escolhido = None


    # ==================================================
    # PRIMEIRA PASSAGEM RÍGIDA
    # ==================================================

    for candidato in todos[:15]:

        if not candidato_aceitavel(
            candidato,
            len(must_have)
        ):
            continue


        ext = (
            ".mp4"
            if candidato[
                "tipo"
            ] == "vídeo"
            else ".jpg"
        )

        destino = os.path.join(
            SAIDA_DIR,
            f"scene_{numero:02d}{ext}"
        )


        if baixar(
            candidato["url"],
            destino
        ):

            sucesso = True
            escolhido = candidato

            marcar_usado(
                candidato[
                    "fonte"
                ],
                candidato[
                    "id"
                ]
            )

            break


    # ==================================================
    # SEGUNDA PASSAGEM RELAXADA
    # ==================================================

    if (
        not sucesso
        and todos
    ):

        print(
            "  Nenhum candidato passou "
            "na regra rígida."
        )

        print(
            "  Tentando melhor candidato disponível..."
        )


        for candidato in todos[:8]:

            # ainda rejeita mídia com
            # muitos termos proibidos

            if candidato[
                "avoid_hits"
            ] >= 2:
                continue


            ext = (
                ".mp4"
                if candidato[
                    "tipo"
                ] == "vídeo"
                else ".jpg"
            )

            destino = os.path.join(
                SAIDA_DIR,
                f"scene_{numero:02d}{ext}"
            )


            if baixar(
                candidato["url"],
                destino
            ):

                sucesso = True
                escolhido = candidato

                marcar_usado(
                    candidato[
                        "fonte"
                    ],
                    candidato[
                        "id"
                    ]
                )

                break


    # ==================================================
    # LOCAL
    # ==================================================

    if not sucesso:

        origem = buscar_local(
            preferir_video
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
                    "avoid_hits": 0
                }

            except Exception:

                sucesso = False


    # ==================================================
    # RESULTADO
    # ==================================================

    if sucesso:

        fonte = escolhido[
            "fonte"
        ]

        tipo = escolhido[
            "tipo"
        ]

        print(
            f"  ESCOLHIDO: "
            f"{fonte} / {tipo}"
        )

        print(
            f"  score="
            f"{escolhido['score']:.1f} "
            f"must="
            f"{escolhido['must_hits']}/"
            f"{len(must_have)} "
            f"avoid="
            f"{escolhido['avoid_hits']}"
        )


        total += 1

        contagem[
            fonte
        ] += 1

        if tipo == "vídeo":
            videos_total += 1
        else:
            fotos_total += 1


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
print("V6.5.1 - RESUMO")
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

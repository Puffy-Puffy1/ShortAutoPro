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

        mapa = json.load(
            f
        )

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
            os.remove(
                caminho
            )
        except Exception:
            pass


# ==================================================
# UTILIDADES
# ==================================================

STOP = {
    "a", "an", "the", "of", "in",
    "on", "at", "with", "and", "or",
    "to", "for", "from", "by",
    "cinematic", "dramatic", "moody",
    "dark", "night", "close", "up"
}


def tokenizar(texto):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            texto.lower()
        )
        if x not in STOP
    }


def normalizar_texto(texto):

    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            texto.lower()
        )
    )


def similaridade(
    busca,
    descricao
):

    a = tokenizar(
        busca
    )

    b = tokenizar(
        descricao
    )

    if not a:
        return 0

    return (
        len(
            a.intersection(b)
        )
        / len(a)
    )


def contains_phrase(
    texto,
    termo
):

    texto = normalizar_texto(
        texto
    )

    termo = normalizar_texto(
        termo
    )

    if not termo:
        return False

    return termo in texto


def score_relevancia(
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
        * 50
    )

    must_hits = 0

    for termo in must_have:

        if contains_phrase(
            descricao,
            termo
        ):

            score += 35
            must_hits += 1

        else:

            score -= 18

    for termo in avoid:

        if contains_phrase(
            descricao,
            termo
        ):

            score -= 45

    return (
        score,
        must_hits
    )


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
                    f.write(
                        bloco
                    )

        return (
            os.path.exists(
                destino
            )
            and os.path.getsize(
                destino
            ) > 1000
        )

    except Exception:

        if os.path.exists(
            destino
        ):

            try:
                os.remove(
                    destino
                )
            except Exception:
                pass

        return False


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
        return -100

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

def candidatos_pexels_video(
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

    saida = []

    for item in r.json().get(
        "videos",
        []
    ):

        ident = item.get(
            "id"
        )

        descricao = " ".join(
            [
                busca,
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

        rel, must_hits = (
            score_relevancia(
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
                score += 30

            if h >= 1280:
                score += 18

            if w >= 720:
                score += 8

            score += penalidade_usado(
                "pexels_video",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits":
                        must_hits,
                    "id": ident,
                    "url": url,
                    "fonte":
                        "Pexels",
                    "tipo":
                        "vídeo"
                }
            )

    return saida


# ==================================================
# PEXELS FOTO
# ==================================================

def candidatos_pexels_foto(
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

    saida = []

    for item in r.json().get(
        "photos",
        []
    ):

        ident = item.get(
            "id"
        )

        descricao = " ".join(
            [
                str(
                    item.get(
                        "alt",
                        ""
                    )
                ),
                busca
            ]
        )

        rel, must_hits = (
            score_relevancia(
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
            score += 30

        if h >= 1280:
            score += 18

        score += penalidade_usado(
            "pexels_foto",
            ident
        )

        saida.append(
            {
                "score": score,
                "must_hits":
                    must_hits,
                "id": ident,
                "url": url,
                "fonte":
                    "Pexels",
                "tipo":
                    "foto"
            }
        )

    return saida


# ==================================================
# PIXABAY VIDEO
# ==================================================

def candidatos_pixabay_video(
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

    saida = []

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
                busca
            ]
        )

        rel, must_hits = (
            score_relevancia(
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
            "medium",
            "small",
            "large",
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
                score += 30

            if h >= 720:
                score += 15

            if h >= 1080:
                score += 8

            score += penalidade_usado(
                "pixabay_video",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits":
                        must_hits,
                    "id": ident,
                    "url": url,
                    "fonte":
                        "Pixabay",
                    "tipo":
                        "vídeo"
                }
            )

    return saida


# ==================================================
# PIXABAY FOTO
# ==================================================

def candidatos_pixabay_foto(
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

    saida = []

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
                busca
            ]
        )

        rel, must_hits = (
            score_relevancia(
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
            score += 30

        if h >= 1280:
            score += 18

        score += penalidade_usado(
            "pixabay_foto",
            ident
        )

        saida.append(
            {
                "score": score,
                "must_hits":
                    must_hits,
                "id": ident,
                "url": url,
                "fonte":
                    "Pixabay",
                "tipo":
                    "foto"
            }
        )

    return saida


# ==================================================
# COVERR VIDEO
# ==================================================

def candidatos_coverr(
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
                ),
                busca
            ]
        )

        rel, must_hits = (
            score_relevancia(
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

            score = (
                rel
                + 8
                if ".mp4"
                in url.lower()
                else rel
            )

            score += penalidade_usado(
                "coverr",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits":
                        must_hits,
                    "id": ident,
                    "url": url,
                    "fonte":
                        "Coverr",
                    "tipo":
                        "vídeo"
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
# EXECUÇÃO
# ==================================================

print()
print("================================")
print("VISUAL RELEVANCE GUARD V6.5")
print("================================")
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
        str(x).lower()
        for x in cena.get(
            "must_have",
            []
        )
    ]

    avoid = [
        str(x).lower()
        for x in cena.get(
            "avoid",
            []
        )
    ]


    preferir_video = (
        USAR_VIDEOS
        and (
            (numero - 1)
            % VIDEO_A_CADA
            == 0
        )
    )


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


    candidatos = []


    # ----------------------------------
    # VIDEO
    # ----------------------------------

    if preferir_video:

        candidatos.extend(
            candidatos_pexels_video(
                busca,
                must_have,
                avoid
            )
        )

        candidatos.extend(
            candidatos_pixabay_video(
                busca,
                must_have,
                avoid
            )
        )

        candidatos.extend(
            candidatos_coverr(
                busca,
                must_have,
                avoid
            )
        )


    # ----------------------------------
    # FOTO
    # ----------------------------------

    if not candidatos:

        candidatos.extend(
            candidatos_pexels_foto(
                busca,
                must_have,
                avoid
            )
        )

        candidatos.extend(
            candidatos_pixabay_foto(
                busca,
                must_have,
                avoid
            )
        )


    # ----------------------------------
    # ORDENAR
    # ----------------------------------

    candidatos.sort(
        key=lambda x: (
            x["must_hits"],
            x["score"]
        ),
        reverse=True
    )


    sucesso = False
    escolhido = None


    # Tenta os melhores,
    # caso algum download falhe.

    for candidato in candidatos[:8]:

        # Se existem must_have,
        # prioriza candidato que cumpra
        # pelo menos um deles.

        if (
            must_have
            and candidato[
                "must_hits"
            ] == 0
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


    # ----------------------------------
    # Se regra rígida não encontrou,
    # relaxa must_have antes do local.
    # ----------------------------------

    if (
        not sucesso
        and candidatos
    ):

        print(
            "  Nenhum candidato cumpriu "
            "must_have. Relaxando regra..."
        )


        for candidato in candidatos[:5]:

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


    # ----------------------------------
    # LOCAL
    # ----------------------------------

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
                    "must_hits": 0
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

        score = escolhido.get(
            "score",
            0
        )

        hits = escolhido.get(
            "must_hits",
            0
        )

        print(
            f"  OK: "
            f"{fonte} / {tipo} "
            f"score={score:.1f} "
            f"must={hits}/{len(must_have)}"
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
print("V6.5 - RESUMO")
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

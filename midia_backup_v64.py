#!/usr/bin/env python3

import os
import sys
import time
import random
import shutil
import re
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
    QTD_CENAS = int(
        os.getenv(
            "SHORT_QTD_CENAS",
            "12"
        )
    )
except ValueError:
    QTD_CENAS = 12

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

KEYWORDS = os.path.join(
    BASE,
    "roteiros",
    f"keywords_{SHORT_ID}.txt"
)

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


if not os.path.exists(KEYWORDS):
    sys.exit(
        f"ERRO: keywords não encontradas:\n{KEYWORDS}"
    )


with open(
    KEYWORDS,
    "r",
    encoding="utf-8"
) as f:

    buscas = [
        x.strip()
        for x in f
        if x.strip()
    ]


buscas = buscas[:QTD_CENAS]

if not buscas:
    sys.exit(
        "ERRO: nenhuma busca visual encontrada."
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
# UTILIDADES
# ==================================================

def tokens(texto):

    return set(
        re.findall(
            r"[a-z0-9]+",
            texto.lower()
        )
    )


def similaridade_textual(
    busca,
    texto
):

    a = tokens(busca)
    b = tokens(texto)

    if not a:
        return 0

    return len(
        a.intersection(b)
    ) / len(a)


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
# ANTI-REPETIÇÃO
# ==================================================

usados_ids = set()


def penalidade_repeticao(
    fonte,
    midia_id
):

    chave = (
        str(fonte),
        str(midia_id)
    )

    if chave in usados_ids:
        return -100

    return 0


def marcar_usado(
    fonte,
    midia_id
):

    usados_ids.add(
        (
            str(fonte),
            str(midia_id)
        )
    )


# ==================================================
# PEXELS VIDEO
# ==================================================

def pexels_video(
    busca,
    numero
):

    if (
        not USAR_PEXELS
        or not PEXELS_KEY
    ):
        return None

    try:

        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={
                "Authorization": PEXELS_KEY
            },
            params={
                "query": busca,
                "orientation": "portrait",
                "per_page": 15
            },
            timeout=30
        )

    except Exception:
        return None

    if not r.ok:
        return None

    videos = r.json().get(
        "videos",
        []
    )

    candidatos = []

    for item in videos:

        vid = item.get("id")

        titulo = " ".join(
            [
                str(item.get("url", "")),
                str(item.get("user", {}).get("name", ""))
            ]
        )

        arquivos = item.get(
            "video_files",
            []
        )

        for arq in arquivos:

            url = arq.get("link")

            if not url:
                continue

            w = arq.get("width") or 0
            h = arq.get("height") or 0

            score = 0

            if h > w:
                score += 30

            if h >= 1280:
                score += 20

            if w >= 720:
                score += 10

            score += (
                similaridade_textual(
                    busca,
                    titulo
                )
                * 20
            )

            score += penalidade_repeticao(
                "pexels_video",
                vid
            )

            candidatos.append(
                {
                    "score": score,
                    "id": vid,
                    "url": url
                }
            )


    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidatos[0]


# ==================================================
# PEXELS FOTO
# ==================================================

def pexels_foto(
    busca,
    numero
):

    if (
        not USAR_PEXELS
        or not PEXELS_KEY
    ):
        return None

    try:

        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={
                "Authorization": PEXELS_KEY
            },
            params={
                "query": busca,
                "orientation": "portrait",
                "per_page": 20
            },
            timeout=30
        )

    except Exception:
        return None

    if not r.ok:
        return None

    fotos = r.json().get(
        "photos",
        []
    )

    candidatos = []

    for item in fotos:

        fid = item.get("id")

        alt = str(
            item.get(
                "alt",
                ""
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

        w = item.get("width") or 0
        h = item.get("height") or 0

        score = 0

        if h > w:
            score += 30

        if h >= 1280:
            score += 20

        score += (
            similaridade_textual(
                busca,
                alt
            )
            * 30
        )

        score += penalidade_repeticao(
            "pexels_foto",
            fid
        )

        candidatos.append(
            {
                "score": score,
                "id": fid,
                "url": url
            }
        )


    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidatos[0]


# ==================================================
# PIXABAY VIDEO
# ==================================================

def pixabay_video(
    busca,
    numero
):

    if (
        not USAR_PIXABAY
        or not PIXABAY_KEY
    ):
        return None

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
        return None

    if not r.ok:
        return None

    hits = r.json().get(
        "hits",
        []
    )

    candidatos = []

    for item in hits:

        vid = item.get("id")

        descricao = " ".join(
            [
                str(item.get("tags", "")),
                str(item.get("pageURL", ""))
            ]
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

            url = info.get("url")

            if not url:
                continue

            w = info.get("width") or 0
            h = info.get("height") or 0

            score = 0

            if h > w:
                score += 30

            if h >= 720:
                score += 15

            if h >= 1080:
                score += 10

            score += (
                similaridade_textual(
                    busca,
                    descricao
                )
                * 35
            )

            score += penalidade_repeticao(
                "pixabay_video",
                vid
            )

            candidatos.append(
                {
                    "score": score,
                    "id": vid,
                    "url": url
                }
            )


    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidatos[0]


# ==================================================
# PIXABAY FOTO
# ==================================================

def pixabay_foto(
    busca,
    numero
):

    if (
        not USAR_PIXABAY
        or not PIXABAY_KEY
    ):
        return None

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
                "per_page": 20
            },
            timeout=30
        )

    except Exception:
        return None

    if not r.ok:
        return None

    hits = r.json().get(
        "hits",
        []
    )

    candidatos = []

    for item in hits:

        fid = item.get("id")

        descricao = str(
            item.get(
                "tags",
                ""
            )
        )

        url = (
            item.get("largeImageURL")
            or item.get("webformatURL")
        )

        if not url:
            continue

        w = item.get("imageWidth") or 0
        h = item.get("imageHeight") or 0

        score = 0

        if h > w:
            score += 30

        if h >= 1280:
            score += 20

        score += (
            similaridade_textual(
                busca,
                descricao
            )
            * 35
        )

        score += penalidade_repeticao(
            "pixabay_foto",
            fid
        )

        candidatos.append(
            {
                "score": score,
                "id": fid,
                "url": url
            }
        )


    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidatos[0]


# ==================================================
# COVERR VIDEO
# ==================================================

def coverr_video(
    busca,
    numero
):

    if (
        not USAR_COVERR
        or not COVERR_KEY
    ):
        return None

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
                "page_size": 15,
                "urls": "true"
            },
            timeout=30
        )

    except Exception:
        return None

    if not r.ok:
        return None

    hits = r.json().get(
        "hits",
        []
    )

    candidatos = []

    for item in hits:

        vid = (
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

            score = 0

            if ".mp4" in url.lower():
                score += 10

            score += (
                similaridade_textual(
                    busca,
                    descricao
                )
                * 40
            )

            score += penalidade_repeticao(
                "coverr",
                vid
            )

            candidatos.append(
                {
                    "score": score,
                    "id": vid,
                    "url": url
                }
            )


    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidatos[0]


# ==================================================
# LOCAL
# ==================================================

def local_media(
    numero,
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
# EXECUÇÃO
# ==================================================

print()
print("================================")
print("SMART MEDIA SELECTOR V6.4")
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

print(
    f"Local: "
    f"{'ON' if USAR_LOCAL else 'OFF'}"
)

print()


contagem = {
    "Pexels": 0,
    "Pixabay": 0,
    "Coverr": 0,
    "Local": 0
}

videos_total = 0
fotos_total = 0
total = 0


for numero, busca in enumerate(
    buscas,
    start=1
):

    preferir_video = (
        USAR_VIDEOS
        and (
            (numero - 1)
            % VIDEO_A_CADA
            == 0
        )
    )

    print(
        f"[{numero}/{len(buscas)}] "
        f"{busca}"
    )

    candidato = None
    fonte = None
    tipo = None

    # =================================
    # VIDEO
    # =================================

    if preferir_video:

        candidatos = []

        c = pexels_video(
            busca,
            numero
        )

        if c:
            candidatos.append(
                (
                    c["score"],
                    "Pexels",
                    "vídeo",
                    c
                )
            )

        c = pixabay_video(
            busca,
            numero
        )

        if c:
            candidatos.append(
                (
                    c["score"],
                    "Pixabay",
                    "vídeo",
                    c
                )
            )

        c = coverr_video(
            busca,
            numero
        )

        if c:
            candidatos.append(
                (
                    c["score"],
                    "Coverr",
                    "vídeo",
                    c
                )
            )

        if candidatos:

            candidatos.sort(
                key=lambda x: x[0],
                reverse=True
            )

            _, fonte, tipo, candidato = (
                candidatos[0]
            )


    # =================================
    # FOTO
    # =================================

    if candidato is None:

        candidatos = []

        c = pexels_foto(
            busca,
            numero
        )

        if c:
            candidatos.append(
                (
                    c["score"],
                    "Pexels",
                    "foto",
                    c
                )
            )

        c = pixabay_foto(
            busca,
            numero
        )

        if c:
            candidatos.append(
                (
                    c["score"],
                    "Pixabay",
                    "foto",
                    c
                )
            )

        if candidatos:

            candidatos.sort(
                key=lambda x: x[0],
                reverse=True
            )

            _, fonte, tipo, candidato = (
                candidatos[0]
            )


    # =================================
    # DOWNLOAD
    # =================================

    sucesso = False

    if candidato is not None:

        ext = (
            ".mp4"
            if tipo == "vídeo"
            else ".jpg"
        )

        destino = os.path.join(
            SAIDA_DIR,
            f"scene_{numero:02d}{ext}"
        )

        sucesso = baixar(
            candidato["url"],
            destino
        )

        if sucesso:

            marcar_usado(
                fonte,
                candidato["id"]
            )

            print(
                f"  OK: "
                f"{fonte} / {tipo} "
                f"score={candidato['score']:.1f}"
            )


    # =================================
    # LOCAL FALLBACK
    # =================================

    if not sucesso:

        origem = local_media(
            numero,
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
                fonte = "Local"

                tipo = (
                    "vídeo"
                    if ext == ".mp4"
                    else "foto"
                )

                print(
                    f"  OK: Local / {tipo}"
                )

            except Exception:
                sucesso = False


    if sucesso:

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
print("SMART MEDIA - RESUMO")
print("================================")
print()

print(
    f"Total: "
    f"{total}/{len(buscas)}"
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

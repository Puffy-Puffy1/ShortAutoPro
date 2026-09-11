#!/usr/bin/env python3

import os
import sys
import time
import random
import shutil
import requests
from datetime import date

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

CENAS_PATH = os.path.join(
    BASE,
    "roteiros",
    f"keywords_{SHORT_ID}.txt"
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
    CENAS_PATH
):
    sys.exit(
        f"ERRO: cenas não encontradas:\n"
        f"{CENAS_PATH}"
    )

with open(
    CENAS_PATH,
    "r",
    encoding="utf-8"
) as f:

    cenas = [
        linha.strip()
        for linha in f
        if linha.strip()
    ]

cenas = cenas[:QTD_CENAS]

if not cenas:
    sys.exit(
        "ERRO: nenhuma cena encontrada."
    )

# Limpa mídia antiga do mesmo ID
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
# PEXELS
# ==================================================

def pexels_video(
    busca,
    numero
):

    if (
        not USAR_PEXELS
        or not PEXELS_KEY
    ):
        return False

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
                "per_page": 12
            },
            timeout=30
        )

    except Exception:
        return False

    if not r.ok:
        return False

    videos = r.json().get(
        "videos",
        []
    )

    if not videos:
        return False

    item = videos[
        (numero - 1)
        % len(videos)
    ]

    candidatos = []

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

        candidatos.append(
            (
                1 if h >= w else 0,
                1 if h >= 1280 else 0,
                min(
                    w * h,
                    1080 * 1920 * 4
                ),
                url
            )
        )

    if not candidatos:
        return False

    candidatos.sort(
        reverse=True
    )

    destino = os.path.join(
        SAIDA_DIR,
        f"scene_{numero:02d}.mp4"
    )

    return baixar(
        candidatos[0][3],
        destino
    )


def pexels_foto(
    busca,
    numero
):

    if (
        not USAR_PEXELS
        or not PEXELS_KEY
    ):
        return False

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
                "per_page": 15
            },
            timeout=30
        )

    except Exception:
        return False

    if not r.ok:
        return False

    fotos = r.json().get(
        "photos",
        []
    )

    if not fotos:
        return False

    item = fotos[
        (numero * 2)
        % len(fotos)
    ]

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
        return False

    destino = os.path.join(
        SAIDA_DIR,
        f"scene_{numero:02d}.jpg"
    )

    return baixar(
        url,
        destino,
        timeout=60
    )


# ==================================================
# PIXABAY
# ==================================================

def pixabay_video(
    busca,
    numero
):

    if (
        not USAR_PIXABAY
        or not PIXABAY_KEY
    ):
        return False

    try:

        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_KEY,
                "q": busca,
                "video_type": "film",
                "safesearch": "true",
                "order": "popular",
                "per_page": 12
            },
            timeout=30
        )

    except Exception:
        return False

    if not r.ok:
        return False

    hits = r.json().get(
        "hits",
        []
    )

    if not hits:
        return False

    item = hits[
        (numero - 1)
        % len(hits)
    ]

    formatos = item.get(
        "videos",
        {}
    )

    candidatos = []

    for chave in [
        "medium",
        "small",
        "tiny",
        "large"
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

        tamanho = info.get(
            "size"
        ) or 0

        candidatos.append(
            (
                1 if h >= w else 0,
                1 if h >= 720 else 0,
                -tamanho,
                url
            )
        )

    if not candidatos:
        return False

    candidatos.sort(
        reverse=True
    )

    destino = os.path.join(
        SAIDA_DIR,
        f"scene_{numero:02d}.mp4"
    )

    return baixar(
        candidatos[0][3],
        destino
    )


def pixabay_foto(
    busca,
    numero
):

    if (
        not USAR_PIXABAY
        or not PIXABAY_KEY
    ):
        return False

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
        return False

    if not r.ok:
        return False

    hits = r.json().get(
        "hits",
        []
    )

    if not hits:
        return False

    item = hits[
        (numero * 3)
        % len(hits)
    ]

    url = (
        item.get(
            "largeImageURL"
        )
        or item.get(
            "webformatURL"
        )
    )

    if not url:
        return False

    destino = os.path.join(
        SAIDA_DIR,
        f"scene_{numero:02d}.jpg"
    )

    return baixar(
        url,
        destino,
        timeout=60
    )


# ==================================================
# COVERR
# ==================================================

def coverr_video(
    busca,
    numero
):

    if (
        not USAR_COVERR
        or not COVERR_KEY
    ):
        return False

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
                "page_size": 10,
                "urls": "true"
            },
            timeout=30
        )

    except Exception:
        return False

    if not r.ok:
        return False

    hits = r.json().get(
        "hits",
        []
    )

    if not hits:
        return False

    item = hits[
        (numero - 1)
        % len(hits)
    ]

    urls = item.get(
        "urls",
        {}
    )

    candidatos = []

    if isinstance(
        urls,
        dict
    ):

        for chave, valor in urls.items():

            if not isinstance(
                valor,
                str
            ):
                continue

            # tenta priorizar mp4
            prioridade = (
                1
                if ".mp4" in valor.lower()
                else 0
            )

            candidatos.append(
                (
                    prioridade,
                    valor
                )
            )

    if not candidatos:

        for chave in [
            "url",
            "download_url"
        ]:

            valor = item.get(
                chave
            )

            if valor:

                candidatos.append(
                    (
                        1,
                        valor
                    )
                )

    if not candidatos:
        return False

    candidatos.sort(
        reverse=True
    )

    destino = os.path.join(
        SAIDA_DIR,
        f"scene_{numero:02d}.mp4"
    )

    return baixar(
        candidatos[0][1],
        destino
    )


# ==================================================
# LOCAL
# ==================================================

def buscar_local(
    numero,
    preferir_video
):

    if not USAR_LOCAL:
        return False

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

        elif ext in (
            ".jpg",
            ".jpeg",
            ".png"
        ):

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
        return False

    origem = candidatos[0]

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

        return True

    except Exception:
        return False


# ==================================================
# EXECUÇÃO
# ==================================================

print()
print("================================")
print("SHORTAUTOPRO - BUSCA DE MÍDIA")
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


total = 0

contagem = {
    "Pexels": 0,
    "Pixabay": 0,
    "Coverr": 0,
    "Local": 0
}

videos_total = 0
fotos_total = 0


for numero, busca in enumerate(
    cenas,
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
        f"[{numero}/"
        f"{len(cenas)}] "
        f"{busca}"
    )

    sucesso = False
    fonte = ""
    tipo = ""

    # ------------------------------
    # VIDEO
    # ------------------------------

    if preferir_video:

        if pexels_video(
            busca,
            numero
        ):

            sucesso = True
            fonte = "Pexels"
            tipo = "vídeo"

        elif pixabay_video(
            busca,
            numero
        ):

            sucesso = True
            fonte = "Pixabay"
            tipo = "vídeo"

        elif coverr_video(
            busca,
            numero
        ):

            sucesso = True
            fonte = "Coverr"
            tipo = "vídeo"

    # ------------------------------
    # FOTO
    # ------------------------------

    if not sucesso:

        if pexels_foto(
            busca,
            numero
        ):

            sucesso = True
            fonte = "Pexels"
            tipo = "foto"

        elif pixabay_foto(
            busca,
            numero
        ):

            sucesso = True
            fonte = "Pixabay"
            tipo = "foto"

    # ------------------------------
    # LOCAL
    # ------------------------------

    if not sucesso:

        if buscar_local(
            numero,
            preferir_video
        ):

            sucesso = True
            fonte = "Local"

            arquivos_local = [
                x
                for x in os.listdir(
                    SAIDA_DIR
                )
                if x.startswith(
                    f"scene_{numero:02d}."
                )
            ]

            if (
                arquivos_local
                and arquivos_local[0]
                .lower()
                .endswith(".mp4")
            ):

                tipo = "vídeo"

            else:

                tipo = "foto"

    if sucesso:

        print(
            f"  OK: "
            f"{fonte} / {tipo}"
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
            "  ERRO: nenhuma fonte "
            "encontrou mídia."
        )

    time.sleep(
        0.25
    )


print()
print("================================")
print("RESUMO DA MÍDIA")
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

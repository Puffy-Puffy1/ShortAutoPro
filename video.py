#!/usr/bin/env python3

import os
import sys
import glob
import json
import subprocess
from datetime import date


# =====================================================
# CONFIG
# =====================================================

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

AUDIO = os.path.join(
    BASE,
    "audios",
    f"short_{SHORT_ID}.mp3"
)

ASS = os.path.join(
    BASE,
    "videos",
    f"short_{SHORT_ID}.ass"
)

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

TEMP = os.path.join(
    BASE,
    "temp",
    SHORT_ID
)

VIDEO_DIR = os.path.join(
    BASE,
    "videos"
)

VIDEO_SEM_AUDIO = os.path.join(
    TEMP,
    "video_sem_audio.mp4"
)

os.makedirs(
    TEMP,
    exist_ok=True
)

os.makedirs(
    VIDEO_DIR,
    exist_ok=True
)


FPS = 30
TRANSICAO = 0.25

PRESET = os.getenv(
    "SHORT_PRESET_CENAS",
    "veryfast"
)

CRF_CENAS = os.getenv(
    "SHORT_CRF_CENAS",
    "23"
)


# =====================================================
# VERIFICAÇÕES
# =====================================================

if not os.path.exists(AUDIO):
    sys.exit(
        "ERRO: áudio não encontrado."
    )

if not os.path.isdir(MEDIA_DIR):
    sys.exit(
        "ERRO: pasta de mídia não encontrada."
    )


# =====================================================
# LOCALIZAR MÍDIAS
# =====================================================

arquivos = []

for caminho in glob.glob(
    os.path.join(
        MEDIA_DIR,
        "scene_*"
    )
):

    ext = os.path.splitext(
        caminho
    )[1].lower()

    if ext in [
        ".jpg",
        ".jpeg",
        ".png",
        ".mp4"
    ]:
        arquivos.append(
            caminho
        )


arquivos = sorted(
    arquivos
)

if not arquivos:
    sys.exit(
        "ERRO: nenhuma mídia encontrada."
    )


# =====================================================
# DURAÇÃO DO ÁUDIO
# =====================================================

try:

    duracao_total = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                AUDIO
            ],
            text=True
        ).strip()
    )

except Exception as e:

    sys.exit(
        f"ERRO lendo duração do áudio: {e}"
    )


# =====================================================
# CONVERTER TEMPO ASS
# =====================================================

def ass_para_segundos(valor):

    try:

        h, m, resto = valor.split(":")

        s, cent = resto.split(".")

        return (
            int(h) * 3600
            + int(m) * 60
            + int(s)
            + int(cent) / 100
        )

    except Exception:

        return None


# =====================================================
# EXTRAIR EVENTOS DA LEGENDA
# =====================================================

def extrair_eventos_ass():

    if not os.path.exists(ASS):
        return []

    eventos = []

    try:

        with open(
            ASS,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                if not linha.startswith(
                    "Dialogue:"
                ):
                    continue

                partes = linha.split(
                    ",",
                    9
                )

                if len(partes) < 10:
                    continue

                inicio = ass_para_segundos(
                    partes[1].strip()
                )

                fim = ass_para_segundos(
                    partes[2].strip()
                )

                if (
                    inicio is None
                    or fim is None
                ):
                    continue

                if fim <= inicio:
                    continue

                eventos.append(
                    (
                        inicio,
                        fim
                    )
                )

    except Exception:

        return []

    eventos.sort(
        key=lambda x: x[0]
    )

    return eventos


# =====================================================
# FALLBACK UNIFORME
# =====================================================

def duracoes_uniformes():

    quantidade = len(
        arquivos
    )

    uniforme = (
        duracao_total
        / quantidade
    )

    return (
        [uniforme] * quantidade,
        "UNIFORME"
    )


# =====================================================
# CÁLCULO SEMÂNTICO V6.3
# =====================================================

def calcular_duracoes():

    quantidade = len(
        arquivos
    )

    eventos = extrair_eventos_ass()

    if len(eventos) < quantidade:

        return duracoes_uniformes()


    # ---------------------------------
    # CARREGAR MAPA
    # ---------------------------------

    if not os.path.exists(
        SCENE_MAP
    ):

        return duracoes_uniformes()


    try:

        with open(
            SCENE_MAP,
            "r",
            encoding="utf-8"
        ) as f:

            mapa = json.load(f)

        mapa_cenas = mapa.get(
            "scenes",
            []
        )

    except Exception:

        return duracoes_uniformes()


    if len(mapa_cenas) != quantidade:

        return duracoes_uniformes()


    # ---------------------------------
    # PESO EM PALAVRAS
    # ---------------------------------

    pesos = []

    for cena in mapa_cenas:

        try:

            peso = int(
                cena.get(
                    "words",
                    1
                )
            )

        except Exception:

            peso = 1

        pesos.append(
            max(
                1,
                peso
            )
        )


    soma_pesos = sum(
        pesos
    )

    if soma_pesos <= 0:

        return duracoes_uniformes()


    # ---------------------------------
    # DISTRIBUIR PELOS EVENTOS
    # ---------------------------------

    total_eventos = len(
        eventos
    )

    limites = [
        0.0
    ]

    acumulado_palavras = 0


    for i in range(
        quantidade - 1
    ):

        acumulado_palavras += (
            pesos[i]
        )

        proporcao = (
            acumulado_palavras
            / soma_pesos
        )

        indice = round(
            proporcao
            * total_eventos
        )

        indice = max(
            1,
            min(
                indice,
                total_eventos - 1
            )
        )

        tempo = eventos[
            indice
        ][0]

        limites.append(
            tempo
        )


    limites.append(
        duracao_total
    )


    # ---------------------------------
    # PROTEÇÃO CONTRA TEMPOS INVÁLIDOS
    # ---------------------------------

    for i in range(
        1,
        len(limites)
    ):

        if limites[i] <= limites[i - 1]:

            limites[i] = (
                limites[i - 1]
                + 0.15
            )


    limites[-1] = (
        duracao_total
    )


    # ---------------------------------
    # DURAÇÕES
    # ---------------------------------

    duracoes = []

    for i in range(
        quantidade
    ):

        dur = (
            limites[i + 1]
            - limites[i]
        )

        duracoes.append(
            max(
                0.65,
                dur
            )
        )


    soma = sum(
        duracoes
    )

    if soma <= 0:

        return duracoes_uniformes()


    # Normaliza para terminar junto do áudio

    fator = (
        duracao_total
        / soma
    )


    duracoes = [
        d * fator
        for d in duracoes
    ]


    return (
        duracoes,
        "SEMANTICA V6.3"
    )


# =====================================================
# CALCULAR
# =====================================================

duracoes_cena, modo_sync = (
    calcular_duracoes()
)


# =====================================================
# INFORMAÇÕES
# =====================================================

print()
print("================================")
print("VIDEO V6.3 - SCENE DIRECTOR")
print("================================")
print()

print(
    f"Mídias: {len(arquivos)}"
)

print(
    f"Duração total: "
    f"{duracao_total:.2f}s"
)

print(
    f"Sincronização: "
    f"{modo_sync}"
)

print(
    f"Transição: "
    f"{TRANSICAO:.2f}s"
)

print()


for i, dur in enumerate(
    duracoes_cena,
    1
):

    print(
        f"Cena {i:02d}: "
        f"{dur:.2f}s"
    )


print()


# =====================================================
# MOTION PLAN LOADER 3.8
# =====================================================

MOTION_PLAN = os.path.join(
    BASE,
    "roteiros",
    f"motion_plan_{SHORT_ID}.json"
)


def carregar_motion_plan():

    if not os.path.exists(
        MOTION_PLAN
    ):

        print(
            "AVISO: motion_plan não encontrado. "
            "Usando movimento padrão."
        )

        return {}


    try:

        with open(
            MOTION_PLAN,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

    except Exception as e:

        print(
            f"AVISO lendo motion_plan: {e}"
        )

        return {}


    cenas_motion = dados.get(
        "scenes",
        []
    )


    if not isinstance(
        cenas_motion,
        list
    ):

        return {}


    resultado = {}


    for item in cenas_motion:

        if not isinstance(
            item,
            dict
        ):
            continue


        try:

            numero_cena = int(
                item.get(
                    "scene"
                )
            )

        except Exception:

            continue


        resultado[
            numero_cena
        ] = item


    return resultado


MOTION = carregar_motion_plan()


def motion_da_cena(
    numero_cena
):

    configuracao = MOTION.get(
        numero_cena
    )


    if isinstance(
        configuracao,
        dict
    ):

        return configuracao


    # Fallback seguro.
    return {
        "motion_profile":
            "legacy",

        "zoom_start":
            1.00,

        "zoom_end":
            1.08,

        "pan":
            "center",

        "intensity":
            3
    }


print(
    f"Motion Plan carregado: "
    f"{len(MOTION)} cenas"
)

print()


# =====================================================
# RENDER DAS CENAS
# =====================================================

cenas = []


for numero, arquivo in enumerate(
    arquivos
):

    ext = os.path.splitext(
        arquivo
    )[1].lower()


    duracao_logica = (
        duracoes_cena[
            numero
        ]
    )


    # Crossfade precisa de sobreposição

    duracao_render = (
        duracao_logica
        + TRANSICAO
    )


    motion_cfg = motion_da_cena(
        numero + 1
    )

    motion_profile = str(
        motion_cfg.get(
            "motion_profile",
            "legacy"
        )
    )

    zoom_start = float(
        motion_cfg.get(
            "zoom_start",
            1.00
        )
    )

    zoom_end = float(
        motion_cfg.get(
            "zoom_end",
            1.08
        )
    )

    pan_dir = str(
        motion_cfg.get(
            "pan",
            "center"
        )
    )

    frames_foto = max(
        1,
        round(
            duracao_render
            * FPS
        )
    )


    cena = os.path.join(
        TEMP,
        f"v63_cena_{numero:02d}.mp4"
    )


    print(
        f"Render "
        f"{numero + 1}/"
        f"{len(arquivos)} "
        f"({duracao_logica:.2f}s) "
        f"{ext}"
    )


    # =================================================
    # FOTO
    # =================================================

    if ext in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:

        # =============================================
        # CINEMATIC MOTION DIRECTOR 3.8
        # =============================================

        delta_zoom = max(
            0.0,
            zoom_end - zoom_start
        )

        passo_zoom = (
            delta_zoom
            / max(
                frames_foto - 1,
                1
            )
        )


        # Zoom começa exatamente no valor
        # definido pelo Motion Director.
        zoom_expr = (
            f"if(eq(on,1),"
            f"{zoom_start:.6f},"
            f"min(zoom+{passo_zoom:.8f},"
            f"{zoom_end:.6f}))"
        )


        # Movimento horizontal suave.
        if pan_dir == "left":

            x_expr = (
                f"(iw-iw/zoom)"
                f"*(1-on/{max(frames_foto, 1)})"
            )

        elif pan_dir == "right":

            x_expr = (
                f"(iw-iw/zoom)"
                f"*(on/{max(frames_foto, 1)})"
            )

        else:

            x_expr = (
                "(iw-iw/zoom)/2"
            )


        # Vertical permanece centralizado.
        y_expr = (
            "(ih-ih/zoom)/2"
        )


        movimento = (
            "zoompan="
            f"z='{zoom_expr}':"
            f"x='{x_expr}':"
            f"y='{y_expr}':"
        )


        print(
            f"  MOTION: "
            f"{motion_profile} | "
            f"zoom "
            f"{zoom_start:.3f}"
            f"->{zoom_end:.3f} | "
            f"pan={pan_dir}"
        )


        filtro = (
            "scale=1200:2133:"
            "force_original_aspect_ratio=increase,"
            "crop=1200:2133,"
            + movimento
            + f"d={frames_foto}:"
            "s=1080x1920:"
            f"fps={FPS},"
            "setsar=1,"
            "format=yuv420p"
        )


        comando = [
            "ffmpeg",
            "-y",

            "-loop",
            "1",

            "-i",
            arquivo,

            "-vf",
            filtro,

            "-frames:v",
            str(
                frames_foto
            ),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

            "-pix_fmt",
            "yuv420p",

            cena
        ]


    # =================================================
    # VÍDEO
    # =================================================

    else:

        filtro = (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"fps={FPS},"
            "setsar=1,"
            "format=yuv420p"
        )


        comando = [
            "ffmpeg",
            "-y",

            "-stream_loop",
            "-1",

            "-i",
            arquivo,

            "-t",
            str(
                duracao_render
            ),

            "-vf",
            filtro,

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

            "-pix_fmt",
            "yuv420p",

            cena
        ]


    # VI6.46 MODULE-LEVEL TRANSACTIONAL BINDING
    try:
        from vi6_47_renderer_switch import adapt_scene_command as _vi647_adapt_scene_command

        comando = _vi647_adapt_scene_command(
            comando,
            {
                "source": "video.py",
                "stage": "SCENE_RENDER_PRIMARY",
            },
        )

    except Exception as _vi647_bridge_exc:
        try:
            from vi6_48_emergency_rollback import trip as _vi648_trip

            _vi648_trip(
                "scene_command_bridge:"
                + type(_vi647_bridge_exc).__name__
            )

        except Exception:
            pass

    try:

        # VI7.00 TRUE SCENE EXECUTOR
        # LEGACY remains default unless VI700_CANARY_MODE=ON.
        try:
            import os as _vi700_os

            if (
                _vi700_os.getenv(
                    "VI700_CANARY_MODE",
                    "OFF"
                ).upper()
                == "ON"
            ):
                from vi6_95_scene_executor import (
                    execute as _vi700_execute_scene
                )

                _vi700_execute_scene(
                    comando,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:
                subprocess.run(
                    comando,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

        except ImportError:
            subprocess.run(
                comando,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    except subprocess.CalledProcessError:

        sys.exit(
            f"ERRO renderizando cena "
            f"{numero + 1}."
        )


    cenas.append(
        cena
    )


# =====================================================
# CROSSFADE
# =====================================================

print()
print(
    "Aplicando transições semânticas..."
)
print()


if len(cenas) == 1:

    try:

        subprocess.run(
            [
                "ffmpeg",
                "-y",

                "-i",
                cenas[0],

                "-t",
                str(
                    duracao_total
                ),

                "-an",

                "-c:v",
                "libx264",

                "-preset",
                PRESET,

                "-crf",
                CRF_CENAS,

                "-pix_fmt",
                "yuv420p",

                "-movflags",
                "+faststart",

                VIDEO_SEM_AUDIO
            ],
            check=True
        )

    except subprocess.CalledProcessError:

        sys.exit(
            "ERRO criando vídeo final."
        )


else:

    comando = [
        "ffmpeg",
        "-y"
    ]


    for cena in cenas:

        comando.extend(
            [
                "-i",
                cena
            ]
        )


    filtros = []


    acumulado = (
        duracoes_cena[0]
    )


    filtros.append(
        f"[0:v][1:v]"
        f"xfade="
        f"transition=fade:"
        f"duration={TRANSICAO}:"
        f"offset={acumulado:.4f}"
        f"[v1]"
    )


    for i in range(
        2,
        len(cenas)
    ):

        acumulado += (
            duracoes_cena[
                i - 1
            ]
        )

        filtros.append(
            f"[v{i-1}]"
            f"[{i}:v]"
            f"xfade="
            f"transition=fade:"
            f"duration={TRANSICAO}:"
            f"offset={acumulado:.4f}"
            f"[v{i}]"
        )


    saida_final = (
        f"[v{len(cenas)-1}]"
    )


    filtro_complexo = (
        ";".join(
            filtros
        )
    )


    comando.extend(
        [
            "-filter_complex",
            filtro_complexo,

            "-map",
            saida_final,

            "-t",
            str(
                duracao_total
            ),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            VIDEO_SEM_AUDIO
        ]
    )


    try:

        subprocess.run(
            comando,
            check=True
        )

    except subprocess.CalledProcessError:

        sys.exit(
            "ERRO aplicando crossfade "
            "semântico."
        )


# =====================================================
# VERIFICAÇÃO
# =====================================================

if not os.path.exists(
    VIDEO_SEM_AUDIO
):

    sys.exit(
        "ERRO: vídeo sem áudio "
        "não foi criado."
    )


try:

    dur_final = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                VIDEO_SEM_AUDIO
            ],
            text=True
        ).strip()
    )

except Exception:

    dur_final = 0


print()
print("================================")
print("VIDEO V6.3 PRONTO!")
print("================================")
print()

print(
    f"Sincronização: "
    f"{modo_sync}"
)

print(
    f"Duração: "
    f"{dur_final:.2f}s"
)

print(
    f"Arquivo:\n"
    f"{VIDEO_SEM_AUDIO}"
)

print()

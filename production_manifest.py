#!/usr/bin/env python3

import os
import json
import glob
import subprocess
from datetime import datetime, date


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

MANIFEST_DIR = os.path.join(
    BASE,
    "manifests"
)

os.makedirs(
    MANIFEST_DIR,
    exist_ok=True
)

SAIDA = os.path.join(
    MANIFEST_DIR,
    f"{SHORT_ID}.json"
)


# =====================================================
# PATHS
# =====================================================

TOPIC = os.path.join(
    BASE,
    "roteiros",
    f"used_topic_{SHORT_ID}.txt"
)

TOPIC_FALLBACK = os.path.join(
    BASE,
    "roteiros",
    f"topic_{SHORT_ID}.txt"
)

HOOK = os.path.join(
    BASE,
    "roteiros",
    f"hook_{SHORT_ID}.txt"
)

ROTEIRO = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}.txt"
)

FONTE = os.path.join(
    BASE,
    "roteiros",
    f"fonte_{SHORT_ID}.txt"
)

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

PUBLISH = os.path.join(
    BASE,
    "roteiros",
    f"publish_{SHORT_ID}.json"
)

VIDEO_V6 = os.path.join(
    BASE,
    "videos",
    f"short_v6_{SHORT_ID}.mp4"
)

VIDEO_V5 = os.path.join(
    BASE,
    "videos",
    f"short_v5_{SHORT_ID}.mp4"
)

LOG = os.path.join(
    BASE,
    "logs",
    "producao",
    f"short_{SHORT_ID}.log"
)


# =====================================================
# HELPERS
# =====================================================

def ler_txt(path):

    if not os.path.exists(
        path
    ):
        return ""

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


def ler_json(path):

    if not os.path.exists(
        path
    ):
        return {}

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

        if isinstance(
            dados,
            dict
        ):
            return dados

    except Exception:
        pass

    return {}


def ffprobe(path):

    if not os.path.exists(
        path
    ):
        return {}

    try:

        saida = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                path
            ],
            text=True
        )

        return json.loads(
            saida
        )

    except Exception:

        return {}


# =====================================================
# ASSUNTO
# =====================================================

assunto = (
    ler_txt(TOPIC)
    or ler_txt(
        TOPIC_FALLBACK
    )
)


# =====================================================
# PUBLISH PACK
# =====================================================

publish = ler_json(
    PUBLISH
)


# =====================================================
# SCENE MAP
# =====================================================

scene_map = ler_json(
    SCENE_MAP
)

scenes = scene_map.get(
    "scenes",
    []
)

if not isinstance(
    scenes,
    list
):
    scenes = []


# =====================================================
# VÍDEO FINAL
# =====================================================

if os.path.exists(
    VIDEO_V6
):

    video = VIDEO_V6
    video_version = "V6"

elif os.path.exists(
    VIDEO_V5
):

    video = VIDEO_V5
    video_version = "V5"

else:

    video = ""
    video_version = ""


video_info = ffprobe(
    video
) if video else {}


# =====================================================
# METADADOS VÍDEO
# =====================================================

duracao = None
width = None
height = None
fps = None
codec_video = None
codec_audio = None


formato = video_info.get(
    "format",
    {}
)

streams = video_info.get(
    "streams",
    []
)


try:

    duracao = float(
        formato.get(
            "duration",
            0
        )
    )

except Exception:

    duracao = None


for stream in streams:

    tipo = stream.get(
        "codec_type"
    )

    if tipo == "video":

        codec_video = stream.get(
            "codec_name"
        )

        width = stream.get(
            "width"
        )

        height = stream.get(
            "height"
        )

        fps_raw = stream.get(
            "avg_frame_rate",
            "0/1"
        )

        try:

            num, den = fps_raw.split(
                "/"
            )

            fps = (
                float(num)
                / float(den)
                if float(den) != 0
                else 0
            )

        except Exception:

            fps = None


    elif tipo == "audio":

        codec_audio = stream.get(
            "codec_name"
        )


# =====================================================
# CENAS FÍSICAS
# =====================================================

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

cenas_fisicas = []

if os.path.isdir(
    MEDIA_DIR
):

    cenas_fisicas = [
        x
        for x in glob.glob(
            os.path.join(
                MEDIA_DIR,
                "scene_*"
            )
        )
        if os.path.splitext(
            x
        )[1].lower()
        in [
            ".jpg",
            ".jpeg",
            ".png",
            ".mp4"
        ]
    ]


cenas_fisicas.sort()


# =====================================================
# QUALITY
# =====================================================

quality = {
    "video_exists":
        bool(video),

    "scene_map_count":
        len(scenes),

    "physical_scene_count":
        len(cenas_fisicas),

    "resolution_ok":
        (
            width == 1080
            and height == 1920
        ),

    "fps_ok":
        (
            fps is not None
            and 29 <= fps <= 31
        ),

    "audio_exists":
        codec_audio is not None
}


quality_pass = all(
    [
        quality[
            "video_exists"
        ],
        quality[
            "resolution_ok"
        ],
        quality[
            "fps_ok"
        ],
        quality[
            "audio_exists"
        ],
        quality[
            "scene_map_count"
        ] == 12,
        quality[
            "physical_scene_count"
        ] == 12
    ]
)


# =====================================================
# MANIFEST
# =====================================================

manifest = {
    "short_id":
        SHORT_ID,

    "created_at":
        datetime.now().isoformat(),

    "status":
        (
            "QUALITY_PASS"
            if quality_pass
            else "INCOMPLETE"
        ),

    "topic":
        assunto,

    "hook":
        ler_txt(HOOK),

    "script":
        {
            "path":
                ROTEIRO,

            "text":
                ler_txt(
                    ROTEIRO
                )
        },

    "source":
        {
            "path":
                FONTE
        },

    "publish":
        {
            "path":
                PUBLISH,

            "chosen_title":
                publish.get(
                    "chosen_title",
                    ""
                ),

            "titles":
                publish.get(
                    "titles",
                    []
                ),

            "description":
                publish.get(
                    "description",
                    ""
                ),

            "hashtags":
                publish.get(
                    "hashtags",
                    []
                ),

            "pinned_comment":
                publish.get(
                    "pinned_comment",
                    ""
                )
        },

    "scenes":
        {
            "map_path":
                SCENE_MAP,

            "count":
                len(scenes),

            "physical_count":
                len(
                    cenas_fisicas
                ),

            "items":
                scenes
        },

    "video":
        {
            "path":
                video,

            "version":
                video_version,

            "duration_seconds":
                duracao,

            "width":
                width,

            "height":
                height,

            "fps":
                fps,

            "video_codec":
                codec_video,

            "audio_codec":
                codec_audio
        },

    "quality":
        quality,

    "log":
        LOG
}


# =====================================================
# SALVAR
# =====================================================

with open(
    SAIDA,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        manifest,
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# RESULTADO
# =====================================================

print()
print("================================")
print("PRODUCTION MANIFEST - 1.7")
print("================================")
print()

print(
    f"ID: {SHORT_ID}"
)

print(
    f"Status: "
    f"{manifest['status']}"
)

print(
    f"Assunto: "
    f"{assunto}"
)

print(
    f"Cenas: "
    f"{len(cenas_fisicas)}/12"
)

if video:

    print(
        f"Vídeo: "
        f"{width}x{height} "
        f"{fps:.2f}fps"
        if fps is not None
        else "Vídeo encontrado"
    )

print()

print(
    f"Manifest:\n{SAIDA}"
)

print()

print(
    "PRODUCTION MANIFEST: OK"
)

print()

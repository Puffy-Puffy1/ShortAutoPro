#!/usr/bin/env python3

import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def certify(path):

    path = Path(path)

    if not path.is_file():
        raise RuntimeError(
            "output ausente"
        )

    if path.stat().st_size <= 0:
        raise RuntimeError(
            "output vazio"
        )


    probe = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,r_frame_rate",
            "-show_entries",
            "format=duration,size,bit_rate",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )

    metadata = json.loads(
        probe
    )


    video_hash_line = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-c",
            "copy",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "-",
        ],
        text=True,
    ).strip()


    if not video_hash_line.startswith(
        "SHA256="
    ):
        raise RuntimeError(
            "video stream hash inválido"
        )


    result = {
        "file":
            str(path),

        "bytes":
            path.stat().st_size,

        "sha256":
            sha(path),

        "video_stream_sha256":
            video_hash_line.split(
                "=",
                1,
            )[1],

        "probe":
            metadata,
    }


    if not result["sha256"]:
        raise RuntimeError(
            "hash vazio"
        )


    if not result[
        "video_stream_sha256"
    ]:
        raise RuntimeError(
            "video hash vazio"
        )


    return result

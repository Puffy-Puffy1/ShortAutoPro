#!/usr/bin/env python3

import hashlib
import json
import os
import re
import shutil
import subprocess

from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

TMP = (
    ROOT
    / "temp"
    / "vi1400"
)

LOG = (
    ROOT
    / "logs"
    / "producao"
)

OUT = (
    ROOT
    / "videos"
    / "canary"
    / "vi1400"
)


for path in (
    TMP,
    LOG,
    OUT,
):
    path.mkdir(
        parents=True,
        exist_ok=True
    )


def load_json(
    path,
    default=None,
):
    path = Path(
        path
    )


    if not path.exists():

        return (
            {}
            if default is None
            else default
        )


    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return (
            {}
            if default is None
            else default
        )


def save_json(
    path,
    data,
):
    path = Path(
        path
    )


    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def run(
    cmd,
    timeout=120,
):
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


    return (
        process.returncode,
        process.stdout,
        process.stderr,
    )


def ffprobe(
    path,
):
    rc, stdout, stderr = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration,size,bit_rate:"
            "stream=index,codec_type,codec_name,"
            "width,height,r_frame_rate,"
            "sample_rate,channels"
        ),
        "-of",
        "json",
        str(
            path
        ),
    ])


    if rc != 0:

        raise RuntimeError(
            stderr.strip()
            or
            "ffprobe_failed"
        )


    return json.loads(
        stdout
    )


def duration(
    path,
):
    value = (
        ffprobe(
            path
        )
        .get(
            "format",
            {}
        )
        .get(
            "duration"
        )
    )


    return float(
        value
        or 0
    )


def sha256_file(
    path,
):
    digest = hashlib.sha256()


    with open(
        path,
        "rb"
    ) as handle:

        for chunk in iter(
            lambda:
                handle.read(
                    1024 * 1024
                ),
            b"",
        ):
            digest.update(
                chunk
            )


    return digest.hexdigest()


def newest(
    paths,
):
    values = [
        Path(
            path
        )

        for path
        in paths

        if Path(
            path
        ).exists()
    ]


    if not values:
        return None


    return max(
        values,
        key=lambda path:
            path.stat().st_mtime
    )


def norm(
    value,
):
    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        )
        .strip()
        .lower(),
    )


def env_on(
    name,
    default=False,
):
    value = os.environ.get(
        name
    )


    if value is None:
        return default


    return (
        value.strip().upper()
        in {
            "1",
            "ON",
            "TRUE",
            "YES",
            "SIM",
        }
    )


def command_exists(
    name,
):
    return (
        shutil.which(
            name
        )
        is not None
    )


def policy():
    return load_json(
        ROOT
        / "config"
        / "vi1400_final_policy.json",
        {}
    )

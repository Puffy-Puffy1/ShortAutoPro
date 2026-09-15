#!/usr/bin/env python3

import hashlib
import json
import re
import subprocess
import time

from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

BASE = (
    ROOT
    / "temp"
    / "vi1510"
)

RUNS = (
    BASE
    / "runs"
)

LOG = (
    ROOT
    / "logs"
    / "producao"
)

POLICY_PATH = (
    ROOT
    / "config"
    / "vi1510_generalization_policy.json"
)


for path in (
    BASE,
    RUNS,
    LOG,
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
    value,
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
            value,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def policy():
    return load_json(
        POLICY_PATH,
        {}
    )


def sha256_file(
    path,
):
    digest = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def norm(
    value,
):
    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ).strip().lower(),
    )


def safe_name(
    value,
):
    value = re.sub(
        r"[^\w\-]+",
        "_",
        str(
            value
            or ""
        ),
        flags=re.UNICODE,
    )

    return (
        value.strip(
            "_"
        )
        or
        "item"
    )[:100]


def run(
    command,
    timeout=120,
):
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )

    return {
        "returncode":
            process.returncode,

        "stdout":
            process.stdout,

        "stderr":
            process.stderr,
    }


def parse_run_timestamp(
    name,
):
    match = re.search(
        r"(\d{8}_\d{6})",
        str(
            name
        )
    )

    if not match:
        return None

    try:
        return time.mktime(
            time.strptime(
                match.group(
                    1
                ),
                "%Y%m%d_%H%M%S"
            )
        )

    except Exception:
        return None


def extract_short_id(
    value,
):
    value = str(
        value
        or ""
    )

    match = re.search(
        r"(\d{4}-\d{2}-\d{2}_\d{4,6})",
        value,
    )

    if match:
        return match.group(
            1
        )

    return None


def in_window(
    path,
    start,
    end,
):
    try:
        mtime = Path(
            path
        ).stat().st_mtime

        return (
            start
            <=
            mtime
            <=
            end
        )

    except Exception:
        return False


def ffprobe(
    path,
):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration,size,format_name:"
            "stream=index,codec_type,codec_name,"
            "width,height"
        ),
        "-of",
        "json",
        str(
            path
        ),
    ])

    if result[
        "returncode"
    ] != 0:
        return {}

    try:
        return json.loads(
            result[
                "stdout"
            ]
        )

    except Exception:
        return {}


def recursive_values(
    value,
):
    if isinstance(
        value,
        dict
    ):

        for key, item in value.items():
            yield (
                key,
                item
            )

            yield from recursive_values(
                item
            )

    elif isinstance(
        value,
        list
    ):

        for item in value:
            yield from recursive_values(
                item
            )

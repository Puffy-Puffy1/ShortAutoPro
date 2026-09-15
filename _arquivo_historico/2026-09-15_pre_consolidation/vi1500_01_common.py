#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
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
    / "vi1500"
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

CONFIG = (
    ROOT
    / "config"
    / "vi1500_qualification_policy.json"
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


def policy():
    return load_json(
        CONFIG,
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


def sha256_text(
    value,
):
    return hashlib.sha256(
        str(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def run(
    command,
    *,
    cwd=None,
    env=None,
    timeout=120,
):
    process = subprocess.run(
        command,
        cwd=(
            str(
                cwd
            )
            if cwd
            else None
        ),
        env=env,
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


def timestamp():
    return time.strftime(
        "%Y%m%d_%H%M%S"
    )


def newest(
    paths,
):
    paths = [
        Path(
            path
        )

        for path in paths

        if Path(
            path
        ).exists()
    ]

    if not paths:
        return None

    return max(
        paths,
        key=lambda path:
            path.stat().st_mtime
    )


def free_mb():
    return (
        shutil.disk_usage(
            ROOT
        ).free
        //
        (
            1024 * 1024
        )
    )


def safe_name(
    value,
):
    import re

    value = re.sub(
        r"[^\w\-]+",
        "_",
        str(
            value
        ).strip(),
        flags=re.UNICODE,
    )

    return (
        value.strip(
            "_"
        )[:80]
        or
        "topic"
    )


def recursive_strings(
    value,
):
    if isinstance(
        value,
        dict
    ):
        for key, item in value.items():
            yield str(
                key
            )
            yield from recursive_strings(
                item
            )

    elif isinstance(
        value,
        list
    ):
        for item in value:
            yield from recursive_strings(
                item
            )

    elif value is not None:
        yield str(
            value
        )

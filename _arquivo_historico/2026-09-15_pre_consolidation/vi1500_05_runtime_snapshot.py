#!/usr/bin/env python3

import shutil
import time

from pathlib import Path

from vi1500_01_common import (
    BASE,
    ROOT,
    save_json,
    sha256_file,
)


CORE = [
    "video.py",
    "gerar_short.sh",
    "roteiro.py",
    "v6.py",
    "vi6_95_scene_executor.py",
    "vi1000_1_semantic_core.py",
    "vi1000_1_query_gate.py",
    "vi1000_runtime.py",
    "vi1000_command_hook.py",
]


BACKUP = (
    BASE
    / "core_backup"
)


def create_core_backup():
    BACKUP.mkdir(
        parents=True,
        exist_ok=True
    )

    hashes = {}


    for name in CORE:
        source = (
            ROOT
            / name
        )

        if not source.exists():
            continue

        destination = (
            BACKUP
            / name
        )

        shutil.copy2(
            source,
            destination
        )

        hashes[
            name
        ] = sha256_file(
            source
        )


    save_json(
        BASE
        / "core_baseline.json",
        {
            "hashes":
                hashes
        }
    )


    return hashes


def verify_and_restore_core():
    baseline = (
        __import__(
            "json"
        )
        .loads(
            (
                BASE
                / "core_baseline.json"
            ).read_text(
                encoding="utf-8"
            )
        )
        .get(
            "hashes",
            {}
        )
    )


    changed = []

    restored = []


    for name, expected in baseline.items():
        source = (
            ROOT
            / name
        )

        backup = (
            BACKUP
            / name
        )


        current = (
            sha256_file(
                source
            )
            if source.exists()
            else None
        )


        if current != expected:
            changed.append(
                name
            )

            if backup.exists():
                shutil.copy2(
                    backup,
                    source
                )

                restored.append(
                    name
                )


    return {
        "changed":
            changed,

        "restored":
            restored,

        "clean":
            not changed,
    }


def filesystem_snapshot():
    result = {}


    roots = [
        ROOT / "videos",
        ROOT / "temp",
        ROOT / "logs",
        ROOT / "manifests",
        ROOT / "credits",
    ]


    for base in roots:
        if not base.exists():
            continue

        for path in base.rglob(
            "*"
        ):
            if not path.is_file():
                continue

            try:
                stat = path.stat()

                result[
                    str(
                        path
                    )
                ] = {
                    "size":
                        stat.st_size,

                    "mtime":
                        stat.st_mtime,
                }

            except Exception:
                pass


    return {
        "time":
            time.time(),

        "files":
            result,
    }


if __name__ == "__main__":
    hashes = create_core_backup()

    print(
        "VI1500 CORE SNAPSHOT=PASS"
    )

    print(
        "CORE_FILES=",
        len(
            hashes
        )
    )

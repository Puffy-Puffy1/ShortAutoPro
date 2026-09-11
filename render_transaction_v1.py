#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from fresh_render_guard_v1 import (
    clean,
)

from render_input_fingerprint_v1 import (
    fingerprint,
)


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


def sha256(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def run(script, env):

    print()
    print(
        "RUN=",
        script,
        flush=True,
    )

    result = subprocess.run(
        [
            "python",
            script,
        ],
        cwd=ROOT,
        env=env,
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"{script} failed "
            f"with "
            f"{result.returncode}"
        )


def main():

    sid = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()


    if not sid:

        raise RuntimeError(
            "SHORT_ID ausente"
        )


    before = fingerprint(
        sid
    )


    if before[
        "media_count"
    ] != 12:

        raise RuntimeError(
            "media_count != 12"
        )


    print(
        "INPUT_FINGERPRINT=",
        before[
            "fingerprint"
        ],
    )


    removed = clean(
        sid
    )


    print(
        "STALE_RENDER_FILES_REMOVED=",
        len(
            removed
        ),
    )


    env = os.environ.copy()

    env[
        "SHORT_ID"
    ] = sid

    env[
        "SAP_NO_PUBLISH"
    ] = "1"


    started = time.time()


    run(
        "video.py",
        env,
    )


    run(
        "v6.py",
        env,
    )


    final = (
        ROOT
        / "videos"
        / f"short_v6_{sid}.mp4"
    )


    if not final.is_file():

        raise RuntimeError(
            "final output ausente"
        )


    if (
        final.stat().st_mtime
        <
        started - 2
    ):

        raise RuntimeError(
            "final output stale"
        )


    after = fingerprint(
        sid
    )


    if (
        after[
            "fingerprint"
        ]
        !=
        before[
            "fingerprint"
        ]
    ):

        raise RuntimeError(
            "mídia mudou durante render"
        )


    manifest = {
        "short_id":
            sid,

        "input_fingerprint":
            before[
                "fingerprint"
            ],

        "output":
            str(
                final
            ),

        "output_sha256":
            sha256(
                final
            ),

        "output_bytes":
            final.stat().st_size,

        "render_started":
            started,

        "output_mtime":
            final.stat().st_mtime,

        "fresh":
            True,
    }


    manifest_path = (
        ROOT
        / "manifests"
        / f"render_transaction_{sid}.json"
    )


    manifest_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print(
        "RENDER_TRANSACTION=PASS"
    )

    print(
        "OUTPUT_SHA256=",
        manifest[
            "output_sha256"
        ],
    )

    print(
        "MANIFEST=",
        manifest_path,
    )


if __name__ == "__main__":

    main()

#!/usr/bin/env python3

import json
import os
import subprocess
import time
from pathlib import Path

from fresh_render_guard_v1 import clean
from render_input_fingerprint_v1 import fingerprint
from render_output_certifier_v2 import certify


ROOT = Path.home() / "ShortAutoPro"


def run(script, env):

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
            f"{script} status="
            f"{result.returncode}"
        )


def main():

    sid = os.getenv(
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


    ass = (
        ROOT
        / "videos"
        / f"short_{sid}.ass"
    )


    audio = (
        ROOT
        / "audios"
        / f"short_{sid}.mp3"
    )


    if not audio.is_file():
        raise RuntimeError(
            "audio ausente"
        )


    # Preserva/regenera ASS antes da limpeza.
    if not ass.is_file():

        env = os.environ.copy()

        env[
            "SHORT_ID"
        ] = sid

        run(
            "legenda_dinamica.py",
            env,
        )


    if not ass.is_file():

        raise RuntimeError(
            "ASS não criado"
        )


    clean(
        sid
    )


    # clean() V2/V3 nunca pode apagar ASS.
    if not ass.is_file():

        raise RuntimeError(
            "render guard removeu ASS"
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


    video_base = (
        ROOT
        / "temp"
        / sid
        / "video_sem_audio.mp4"
    )


    if not video_base.is_file():

        raise RuntimeError(
            "video_sem_audio ausente"
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
            "final ausente"
        )


    if (
        final.stat().st_mtime
        <
        started - 2
    ):

        raise RuntimeError(
            "final stale"
        )


    after = fingerprint(
        sid
    )


    if (
        before["fingerprint"]
        !=
        after["fingerprint"]
    ):

        raise RuntimeError(
            "mídias mudaram durante render"
        )


    certification = certify(
        final
    )


    manifest = {
        "short_id":
            sid,

        "input_fingerprint":
            before["fingerprint"],

        "output":
            certification,

        "fresh":
            True,
    }


    path = (
        ROOT
        / "manifests"
        / f"render_transaction_v2_{sid}.json"
    )


    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    print(
        "RENDER_TRANSACTION_V2=PASS"
    )

    print(
        "FINAL_SHA256=",
        certification["sha256"],
    )

    print(
        "VIDEO_STREAM_SHA256=",
        certification[
            "video_stream_sha256"
        ],
    )


if __name__ == "__main__":
    main()

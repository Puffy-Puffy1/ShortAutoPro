#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


def valid_ass(path):

    if not path.is_file():
        return False

    if path.stat().st_size <= 100:
        return False

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        return False


    return (
        "[Events]" in text
        and
        "Dialogue:" in text
    )


def ensure_ass(short_id):

    ass = (
        ROOT
        / "videos"
        / f"short_{short_id}.ass"
    )


    if valid_ass(
        ass
    ):

        print(
            "ASS_STATUS=EXISTING_VALID"
        )

        return True


    audio = (
        ROOT
        / "audios"
        / f"short_{short_id}.mp3"
    )

    script = (
        ROOT
        / "roteiros"
        / f"short_{short_id}.txt"
    )


    if not audio.is_file():

        print(
            "ASS_RECOVERY=FAIL_AUDIO_MISSING"
        )

        return False


    if not script.is_file():

        print(
            "ASS_RECOVERY=FAIL_SCRIPT_MISSING"
        )

        return False


    env = os.environ.copy()

    env[
        "SHORT_ID"
    ] = short_id


    result = subprocess.run(
        [
            "python",
            "legenda_dinamica.py",
        ],
        cwd=ROOT,
        env=env,
    )


    if (
        result.returncode == 0
        and
        valid_ass(
            ass
        )
    ):

        print(
            "ASS_RECOVERY=PASS"
        )

        return True


    print(
        "ASS_RECOVERY=FAIL"
    )

    return False


if __name__ == "__main__":

    sid = os.getenv(
        "SHORT_ID",
        "",
    ).strip()


    if not sid:

        print(
            "ASS_GUARD=FAIL_SHORT_ID"
        )

        raise SystemExit(1)


    ok = ensure_ass(
        sid
    )


    print(
        "ASS_GUARD="
        +
        (
            "PASS"
            if ok
            else
            "FAIL"
        )
    )


    if not ok:
        raise SystemExit(1)

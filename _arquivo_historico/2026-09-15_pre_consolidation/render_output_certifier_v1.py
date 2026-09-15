#!/usr/bin/env python3

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


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


def probe(path):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            (
                "format=duration,size,bit_rate:"
                "stream=codec_name,codec_type,"
                "width,height,r_frame_rate"
            ),
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr.strip()
            or
            "ffprobe failure"
        )

    return json.loads(
        result.stdout
    )


def certify(short_id, max_age=1800):

    final = (
        ROOT
        / "videos"
        / f"short_v6_{short_id}.mp4"
    )


    result = {
        "short_id":
            short_id,

        "path":
            str(final),

        "exists":
            False,

        "fresh":
            False,

        "hash_valid":
            False,

        "probe_valid":
            False,

        "pass":
            False,
    }


    if not final.is_file():

        return result


    if final.stat().st_size <= 0:

        return result


    result[
        "exists"
    ] = True


    digest = sha256(
        final
    )


    result[
        "sha256"
    ] = digest


    result[
        "hash_valid"
    ] = (
        isinstance(
            digest,
            str,
        )
        and
        len(digest) == 64
        and
        set(digest)
        <=
        set(
            "0123456789abcdef"
        )
    )


    age = max(
        0.0,
        time.time()
        -
        final.stat().st_mtime,
    )


    result[
        "age_seconds"
    ] = age


    result[
        "fresh"
    ] = (
        age <= max_age
    )


    try:

        metadata = probe(
            final
        )

        result[
            "probe"
        ] = metadata

        streams = metadata.get(
            "streams",
            [],
        )

        video_streams = [
            stream
            for stream in streams
            if stream.get(
                "codec_type"
            )
            ==
            "video"
        ]


        result[
            "probe_valid"
        ] = bool(
            video_streams
        )

    except Exception as exc:

        result[
            "probe_error"
        ] = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )


    result[
        "pass"
    ] = all(
        (
            result["exists"],
            result["fresh"],
            result["hash_valid"],
            result["probe_valid"],
        )
    )


    return result


if __name__ == "__main__":

    sid = os.getenv(
        "SHORT_ID",
        "",
    ).strip()

    if not sid:

        print(
            "CERTIFIER=FAIL_SHORT_ID"
        )

        raise SystemExit(1)


    result = certify(
        sid
    )


    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


    if result["pass"]:

        print(
            "RENDER_CERTIFICATION=PASS"
        )

    else:

        print(
            "RENDER_CERTIFICATION=FAIL"
        )

        raise SystemExit(1)

#!/usr/bin/env python3

import hashlib
import json
import os
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def media_files(short_id):

    root = (
        ROOT
        / "imagens"
        / f"short_{short_id}"
    )

    result = []

    for scene in range(1, 13):

        matches = sorted(
            p
            for p in root.glob(
                f"scene_{scene:02d}.*"
            )
            if p.is_file()
        )

        for p in matches:

            result.append(
                {
                    "scene": scene,
                    "name": p.name,
                    "path": str(p),
                    "bytes": p.stat().st_size,
                    "sha256": sha256(p),
                }
            )

    return result


def fingerprint(short_id):

    files = media_files(
        short_id
    )

    payload = json.dumps(
        files,
        ensure_ascii=False,
        sort_keys=True,
    ).encode()

    return {
        "short_id": short_id,
        "media_count": len(files),
        "media": files,
        "fingerprint":
            hashlib.sha256(
                payload
            ).hexdigest(),
    }


def main():

    sid = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if not sid:
        raise SystemExit(
            "SHORT_ID ausente"
        )

    data = fingerprint(
        sid
    )

    output = (
        ROOT
        / "temp"
        / f"render_input_{sid}.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "SHORT_ID=",
        sid,
    )

    print(
        "MEDIA_COUNT=",
        data["media_count"],
    )

    print(
        "INPUT_FINGERPRINT=",
        data["fingerprint"],
    )

    for item in data["media"]:

        print(
            f"SCENE_{item['scene']:02d} "
            f"{item['name']} "
            f"{item['sha256'][:16]}"
        )


if __name__ == "__main__":
    main()

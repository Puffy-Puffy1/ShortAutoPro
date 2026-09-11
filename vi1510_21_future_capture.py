#!/usr/bin/env python3

import argparse
import subprocess
import time

from pathlib import Path

from vi1510_01_common import (
    BASE,
    ROOT,
    save_json,
)


def snapshot(
    output,
):
    roots = [
        ROOT / "imagens",
        ROOT / "temp",
        ROOT / "manifests",
        ROOT / "credits",
        ROOT / "roteiros",
        ROOT / "videos",
    ]


    rows = {}


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

            except Exception:
                continue


            rows[
                str(
                    path.resolve()
                )
            ] = {
                "size":
                    stat.st_size,

                "mtime":
                    stat.st_mtime,
            }


    save_json(
        output,
        {
            "time":
                time.time(),

            "files":
                rows,
        }
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--label",
        required=True,
        choices=[
            "A",
            "B",
            "C",
        ]
    )

    args = parser.parse_args()


    capture = (
        BASE
        /
        (
            "future_capture_"
            +
            args.label
        )
    )


    capture.mkdir(
        parents=True,
        exist_ok=True
    )


    snapshot(
        capture
        / "before.json"
    )


    process = subprocess.run(
        [
            "python",
            str(
                ROOT
                / "vi1500_24_topic_runner.py"
            ),
            "--label",
            args.label,
        ],
        cwd=str(
            ROOT
        ),
    )


    snapshot(
        capture
        / "after.json"
    )


    save_json(
        capture
        / "result.json",
        {
            "returncode":
                process.returncode,
        }
    )


    print(
        "VI1510 FUTURE CAPTURE COMPLETE"
    )

    print(
        "LABEL=",
        args.label
    )

    print(
        "RETURN_CODE=",
        process.returncode
    )


if __name__ == "__main__":

    main()

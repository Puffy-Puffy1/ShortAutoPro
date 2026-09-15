#!/usr/bin/env python3

import math
import subprocess

from vi1400_01_common import (
    TMP,
    load_json,
    save_json,
)


W = 180
H = 320


def sample_gray(
    video,
    timestamp,
):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",

        "-ss",
        f"{timestamp:.3f}",

        "-i",
        str(
            video
        ),

        "-frames:v",
        "1",

        "-vf",
        (
            f"scale={W}:{H}:"
            "flags=area,"
            "format=gray"
        ),

        "-f",
        "rawvideo",

        "-pix_fmt",
        "gray",

        "pipe:1",
    ]


    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
    )


    if (
        process.returncode != 0
        or
        len(
            process.stdout
        )
        <
        W * H
    ):

        raise RuntimeError(
            "frame_sample_failed:"
            +
            process.stderr.decode(
                "utf-8",
                "ignore"
            )[-300:]
        )


    return process.stdout[
        :W * H
    ]


def stats(
    buffer,
):
    values = buffer

    count = len(
        values
    )


    mean = (
        sum(
            values
        )
        /
        count
    )


    variance = (
        sum(
            (
                value
                -
                mean
            )
            ** 2

            for value
            in values
        )
        /
        count
    )


    deviation = (
        math.sqrt(
            variance
        )
    )


    black_fraction = (
        sum(
            value < 18

            for value
            in values
        )
        /
        count
    )


    white_fraction = (
        sum(
            value > 240

            for value
            in values
        )
        /
        count
    )


    edge_total = 0

    edge_hits = 0


    for y in range(
        0,
        H,
        2
    ):

        row = (
            y
            *
            W
        )


        for x in range(
            0,
            W - 2,
            2
        ):

            edge_total += 1


            if abs(
                values[
                    row + x
                ]
                -
                values[
                    row + x + 2
                ]
            ) > 24:

                edge_hits += 1


    edge_density = (
        edge_hits
        /
        max(
            edge_total,
            1
        )
    )


    third_deviation = []


    for start_y, end_y in [
        (
            0,
            H // 3
        ),

        (
            H // 3,
            2 * H // 3
        ),

        (
            2 * H // 3,
            H
        ),
    ]:

        part = []


        for y in range(
            start_y,
            end_y
        ):

            part.extend(
                values[
                    y * W:
                    (
                        y + 1
                    )
                    * W
                ]
            )


        part_mean = (
            sum(
                part
            )
            /
            len(
                part
            )
        )


        part_deviation = math.sqrt(
            sum(
                (
                    value
                    -
                    part_mean
                )
                ** 2

                for value
                in part
            )
            /
            len(
                part
            )
        )


        third_deviation.append(
            part_deviation
        )


    blur_band = (
        third_deviation[
            1
        ]
        > 18

        and

        min(
            third_deviation[
                0
            ],
            third_deviation[
                2
            ],
        )
        <
        third_deviation[
            1
        ]
        *
        0.45
    )


    score = 10.0


    if deviation < 24:

        score -= 2.0

    elif deviation < 34:

        score -= 0.8


    if edge_density < 0.055:

        score -= 1.6

    elif edge_density < 0.085:

        score -= 0.6


    if white_fraction > 0.50:

        score -= 1.7


    if black_fraction > 0.58:

        score -= 1.0


    if blur_band:

        score -= 0.6


    return {
        "mean":
            round(
                mean,
                2
            ),

        "stddev":
            round(
                deviation,
                2
            ),

        "black_fraction":
            round(
                black_fraction,
                4
            ),

        "white_fraction":
            round(
                white_fraction,
                4
            ),

        "edge_density":
            round(
                edge_density,
                4
            ),

        "third_stddev": [
            round(
                value,
                2
            )

            for value
            in third_deviation
        ],

        "blur_band_proxy":
            blur_band,

        "visual_strength":
            round(
                max(
                    0,
                    min(
                        10,
                        score
                    )
                ),
                2
            ),
    }


def analyze():
    artifacts = load_json(
        TMP
        / "artifacts.json"
    )


    timeline = load_json(
        TMP
        / "timeline.json"
    ).get(
        "timeline",
        []
    )


    video = artifacts[
        "final_video"
    ]


    rows = []


    for item in timeline:

        midpoint = (
            float(
                item[
                    "start"
                ]
            )
            +
            float(
                item[
                    "end"
                ]
            )
        ) / 2


        metrics = stats(
            sample_gray(
                video,
                midpoint
            )
        )


        metrics.update({
            "scene":
                item[
                    "scene"
                ],

            "timestamp":
                round(
                    midpoint,
                    3
                ),
        })


        rows.append(
            metrics
        )


    save_json(
        TMP
        / "frame_metrics.json",
        {
            "scenes":
                rows
        }
    )


    return rows


if __name__ == "__main__":

    rows = analyze()


    print(
        "VI1400 FRAME METRICS=PASS"
    )


    for row in rows:

        print(
            "SCENE",
            row[
                "scene"
            ],
            "SCORE",
            row[
                "visual_strength"
            ],
            "WHITE",
            row[
                "white_fraction"
            ],
            "BLUR_BAND",
            row[
                "blur_band_proxy"
            ],
        )

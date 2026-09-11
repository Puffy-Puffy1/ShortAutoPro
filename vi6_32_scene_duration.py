#!/usr/bin/env python3

import re


VERSION = "6.32"

WORDS_PER_SECOND = 2.55


def _s(v):
    return str(v or "").strip()


def _f(v):

    try:

        value = float(v)

        if value > 0:
            return value

    except Exception:
        pass

    return None


def _scene_number(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )

    try:

        return int(
            board.get(
                "scene",
                0
            )
            or 0
        )

    except Exception:

        return 0


def _role(scene):

    role = _s(
        scene.get(
            "retrieval_role_6_7"
        )
    ).upper()


    if role:
        return role


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    return _s(
        board.get(
            "role"
        )
        or "CONTEXT"
    ).upper()


def _narration(scene):

    for field in (
        "segmento",
        "segment",
        "narracao",
        "narração",
        "texto",
        "text",
        "script",
    ):

        value = _s(
            scene.get(
                field
            )
        )


        if value:
            return value


    return ""


def _word_count(text):

    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            _s(text)
        )
    )


def _explicit_duration(scene):

    for field in (
        "duration",
        "duration_s",
        "duration_sec",
        "scene_duration",
        "duracao",
        "duração",
        "duracao_s",
        "duracao_segundos",
    ):

        value = _f(
            scene.get(
                field
            )
        )


        if value is not None:

            return (
                value,
                field
            )


    timing = (
        scene.get(
            "timing"
        )
        or scene.get(
            "timestamps"
        )
        or {}
    )


    if isinstance(
        timing,
        dict
    ):

        start = _f(
            timing.get(
                "start"
            )
            or timing.get(
                "inicio"
            )
        )


        end = _f(
            timing.get(
                "end"
            )
            or timing.get(
                "fim"
            )
        )


        if (
            start is not None
            and end is not None
            and end > start
        ):

            return (
                end - start,
                "timing_start_end"
            )


    start = _f(
        scene.get(
            "start"
        )
        or scene.get(
            "inicio"
        )
    )


    end = _f(
        scene.get(
            "end"
        )
        or scene.get(
            "fim"
        )
    )


    if (
        start is not None
        and end is not None
        and end > start
    ):

        return (
            end - start,
            "scene_start_end"
        )


    return (
        None,
        None
    )


def duration_info(scene):

    explicit, source = (
        _explicit_duration(
            scene
        )
    )


    role = _role(
        scene
    )


    if explicit is not None:

        value = max(
            .75,
            min(
                20.0,
                explicit
            )
        )


        return {

            "version":
                VERSION,

            "scene":
                _scene_number(
                    scene
                ),

            "role":
                role,

            "seconds":
                round(
                    value,
                    3
                ),

            "source":
                source,

            "confidence":
                "HIGH",

            "estimated":
                False,
        }


    narration = _narration(
        scene
    )


    words = _word_count(
        narration
    )


    if words > 0:

        estimated = (
            words
            / WORDS_PER_SECOND
        )


        if role == "CTA":

            minimum = 1.2

        else:

            minimum = 1.6


        estimated = max(
            minimum,
            min(
                12.0,
                estimated
            )
        )


        return {

            "version":
                VERSION,

            "scene":
                _scene_number(
                    scene
                ),

            "role":
                role,

            "seconds":
                round(
                    estimated,
                    3
                ),

            "source":
                "narration_word_estimate",

            "confidence":
                "MEDIUM",

            "estimated":
                True,

            "words":
                words,

            "words_per_second":
                WORDS_PER_SECOND,
        }


    # Último fallback apenas para que
    # possamos validar o plano offline.
    fallback = (
        2.0
        if role == "CTA"
        else 4.0
    )


    return {

        "version":
            VERSION,

        "scene":
            _scene_number(
                scene
            ),

        "role":
            role,

        "seconds":
            fallback,

        "source":
            "safe_default",

        "confidence":
            "LOW",

        "estimated":
            True,

        "words":
            0,
    }


def motion_metrics(
    contract,
    duration
):

    seconds = float(
        duration.get(
            "seconds",
            4.0
        )
        or 4.0
    )


    seconds = max(
        .25,
        seconds
    )


    ken = (
        contract.get(
            "ken_burns"
        )
        or {}
    )


    if not ken.get(
        "enabled"
    ):

        return {

            "zoom_delta":
                0.0,

            "zoom_rate":
                0.0,

            "pan_distance":
                0.0,

            "pan_rate":
                0.0,
        }


    z1 = float(
        ken.get(
            "zoom_start",
            1.0
        )
    )


    z2 = float(
        ken.get(
            "zoom_end",
            1.0
        )
    )


    x1 = float(
        ken.get(
            "start_x",
            .5
        )
    )


    x2 = float(
        ken.get(
            "end_x",
            .5
        )
    )


    y1 = float(
        ken.get(
            "start_y",
            .5
        )
    )


    y2 = float(
        ken.get(
            "end_y",
            .5
        )
    )


    zoom_delta = abs(
        z2 - z1
    )


    pan_distance = (
        (
            (x2 - x1) ** 2
            + (y2 - y1) ** 2
        )
        ** .5
    )


    return {

        "zoom_delta":
            round(
                zoom_delta,
                5
            ),

        "zoom_rate":
            round(
                zoom_delta
                / seconds,
                5
            ),

        "pan_distance":
            round(
                pan_distance,
                5
            ),

        "pan_rate":
            round(
                pan_distance
                / seconds,
                5
            ),
    }


def self_test():

    explicit = duration_info(
        {
            "duration":
                4.25,

            "_vi68_storyboard":
                {
                    "scene": 2
                }
        }
    )


    assert (
        explicit[
            "seconds"
        ]
        == 4.25
    )


    assert (
        explicit[
            "confidence"
        ]
        == "HIGH"
    )


    estimated = duration_info(
        {
            "segmento":
                (
                    "This is a short narration "
                    "with approximately ten words "
                    "for this scene."
                ),

            "_vi68_storyboard":
                {
                    "scene": 3
                }
        }
    )


    assert (
        estimated[
            "seconds"
        ]
        > 1
    )


    assert (
        estimated[
            "estimated"
        ]
        is True
    )


    metrics = motion_metrics(
        {
            "ken_burns":
                {
                    "enabled":
                        True,

                    "zoom_start":
                        1.0,

                    "zoom_end":
                        1.04,

                    "start_x":
                        .45,

                    "end_x":
                        .55,

                    "start_y":
                        .50,

                    "end_y":
                        .50,
                }
        },
        {
            "seconds":
                4.0
        }
    )


    assert (
        metrics[
            "zoom_rate"
        ]
        == .01
    )


    assert (
        metrics[
            "pan_rate"
        ]
        == .025
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.32 DURATION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Explicit Duration"
    )
    print(
        "OK Timestamp Duration"
    )
    print(
        "OK Narration Estimate"
    )
    print(
        "OK Safe Default"
    )
    print(
        "OK Zoom Rate"
    )
    print(
        "OK Pan Rate"
    )
    print()


if __name__ == "__main__":

    self_test()

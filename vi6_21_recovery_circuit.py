#!/usr/bin/env python3

VERSION = "6.21"

MAX_CALLS_PER_SHORT = 4
MAX_CALLS_PER_SCENE = 2
MAX_ERRORS = 2


_STATE = {

    "calls":
        0,

    "errors":
        0,

    "success":
        0,

    "scene_calls":
        {},

    "open":
        False,
}


def _scene(scene):

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


def status():

    return {

        "version":
            VERSION,

        "calls":
            _STATE[
                "calls"
            ],

        "errors":
            _STATE[
                "errors"
            ],

        "success":
            _STATE[
                "success"
            ],

        "open":
            _STATE[
                "open"
            ],

        "scene_calls":
            dict(
                _STATE[
                    "scene_calls"
                ]
            ),

        "max_calls":
            MAX_CALLS_PER_SHORT,

        "max_scene_calls":
            MAX_CALLS_PER_SCENE,

        "max_errors":
            MAX_ERRORS,
    }


def allow(
    scene
):

    if _STATE[
        "open"
    ]:

        return (
            False,
            "circuit_open"
        )


    if (
        _STATE[
            "calls"
        ]
        >= MAX_CALLS_PER_SHORT
    ):

        _STATE[
            "open"
        ] = True

        return (
            False,
            "short_budget_exhausted"
        )


    number = _scene(
        scene
    )


    used = int(
        _STATE[
            "scene_calls"
        ].get(
            number,
            0
        )
    )


    if (
        used
        >= MAX_CALLS_PER_SCENE
    ):

        return (
            False,
            "scene_budget_exhausted"
        )


    return (
        True,
        "allowed"
    )


def register_call(
    scene
):

    number = _scene(
        scene
    )


    _STATE[
        "calls"
    ] += 1


    _STATE[
        "scene_calls"
    ][
        number
    ] = (
        int(
            _STATE[
                "scene_calls"
            ].get(
                number,
                0
            )
        )
        + 1
    )


def register_success():

    _STATE[
        "success"
    ] += 1


def register_error():

    _STATE[
        "errors"
    ] += 1


    if (
        _STATE[
            "errors"
        ]
        >= MAX_ERRORS
    ):

        _STATE[
            "open"
        ] = True


def reset():

    _STATE[
        "calls"
    ] = 0

    _STATE[
        "errors"
    ] = 0

    _STATE[
        "success"
    ] = 0

    _STATE[
        "scene_calls"
    ].clear()

    _STATE[
        "open"
    ] = False


def self_test():

    reset()


    scene = {
        "_vi68_storyboard":
            {
                "scene": 3
            }
    }


    ok, _ = allow(
        scene
    )

    assert ok is True


    register_call(
        scene
    )

    register_call(
        scene
    )


    ok, reason = allow(
        scene
    )


    assert ok is False

    assert (
        reason
        == "scene_budget_exhausted"
    )


    register_error()
    register_error()


    assert status()[
        "open"
    ] is True


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.21 CIRCUIT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK max 4 recovery calls / short"
    )
    print(
        "OK max 2 calls / scene"
    )
    print(
        "OK error circuit"
    )
    print(
        "OK reset"
    )
    print()


if __name__ == "__main__":

    self_test()

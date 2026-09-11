#!/usr/bin/env python3

VERSION = "6.93"


_selected_zones = set()
_selected_scenes = set()


def reset():

    _selected_zones.clear()
    _selected_scenes.clear()


def selected_count():

    return len(
        _selected_scenes
    )


def can_claim(
    scene,
    zone,
    max_canaries=3
):

    if selected_count() >= max_canaries:
        return False

    if scene in _selected_scenes:
        return False

    if zone in _selected_zones:
        return False

    return True


def claim(
    scene,
    zone
):

    _selected_scenes.add(
        scene
    )

    _selected_zones.add(
        zone
    )


def snapshot():

    return {
        "version": VERSION,

        "selected_scenes":
            sorted(
                _selected_scenes
            ),

        "selected_zones":
            sorted(
                _selected_zones
            ),
    }


def self_test():

    reset()

    assert can_claim(
        5,
        "CONTEXT_A"
    )

    claim(
        5,
        "CONTEXT_A"
    )

    assert not can_claim(
        4,
        "CONTEXT_A"
    )

    print(
        "VI6.93 RUNTIME STATE=PASS"
    )


if __name__ == "__main__":
    self_test()

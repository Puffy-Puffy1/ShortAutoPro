#!/usr/bin/env python3

VERSION = "7.02"

_selected_scenes = set()

_zone_scenes = {}


def reset():

    _selected_scenes.clear()
    _zone_scenes.clear()


def total():

    return len(
        _selected_scenes
    )


def zone_count(zone):

    return len(
        _zone_scenes.get(
            zone,
            set()
        )
    )


def can_claim(
    scene,
    zone,
    max_total,
    max_zone
):

    if scene in _selected_scenes:
        return False

    if total() >= max_total:
        return False

    if zone_count(zone) >= max_zone:
        return False

    return True


def claim(
    scene,
    zone
):

    _selected_scenes.add(
        scene
    )

    _zone_scenes.setdefault(
        zone,
        set()
    ).add(
        scene
    )


def snapshot():

    return {
        "version":
            VERSION,

        "selected_scenes":
            sorted(
                _selected_scenes
            ),

        "zone_scenes":
            {
                key:
                    sorted(value)

                for key, value
                in _zone_scenes.items()
            },

        "total":
            total(),
    }


def self_test():

    reset()

    assert can_claim(
        3,
        "EARLY",
        6,
        2
    )

    claim(
        3,
        "EARLY"
    )

    claim(
        4,
        "EARLY"
    )

    assert not can_claim(
        2,
        "EARLY",
        6,
        2
    )

    assert total() == 2

    reset()

    print(
        "VI7.02 RUNTIME STATE=PASS"
    )


if __name__ == "__main__":
    self_test()

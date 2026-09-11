#!/usr/bin/env python3

VERSION = "7.14"


_selected = []

_profiles = []

_roles = []

_last_seen_scene = None


def reset():

    global _last_seen_scene

    _selected.clear()
    _profiles.clear()
    _roles.clear()

    _last_seen_scene = None


def count():

    return len(
        _selected
    )


def selected():

    return list(
        _selected
    )


def profiles():

    return list(
        _profiles
    )


def roles():

    return list(
        _roles
    )


def last_profiles(n=2):

    return _profiles[-n:]


def previous_selected_scenes(n=2):

    return _selected[-n:]


def claim(
    scene,
    profile,
    role
):

    _selected.append(
        scene
    )

    _profiles.append(
        profile
    )

    _roles.append(
        role
    )


def consecutive_vi7_if_select(scene):

    if not _selected:
        return 1

    run = 1

    expected = scene - 1

    for previous in reversed(
        _selected
    ):

        if previous == expected:
            run += 1
            expected -= 1
        else:
            break

    return run


def snapshot():

    return {
        "version":
            VERSION,

        "selected":
            selected(),

        "profiles":
            profiles(),

        "roles":
            roles(),

        "count":
            count(),
    }


def self_test():

    reset()

    claim(
        2,
        "SLOW_PUSH",
        "EARLY_CONTEXT"
    )

    claim(
        3,
        "DETAIL_PUSH",
        "EARLY_CONTEXT"
    )

    assert (
        consecutive_vi7_if_select(
            4
        )
        == 3
    )

    reset()

    print(
        "VI7.14 ADAPTIVE STATE=PASS"
    )


if __name__ == "__main__":
    self_test()

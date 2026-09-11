#!/usr/bin/env python3


VERSION = "6.66.1"


FORBIDDEN = (
    ";",
    "\n",
    "\r",
    "`",
    "$(",
)


def _validate(vf):

    blockers = []
    warnings = []


    if not isinstance(
        vf,
        str
    ):

        return (
            ["filter_missing"],
            warnings
        )


    if len(vf) > 6000:

        blockers.append(
            "filter_too_large"
        )


    for token in FORBIDDEN:

        if token in vf:

            blockers.append(
                "unsafe_filter_token"
            )


    REQUIRED = (
        "scale=",
        "crop=",
        "zoompan=",
        "setsar=1",
        "format=yuv420p",
    )


    for item in REQUIRED:

        if item not in vf:

            blockers.append(
                "missing:"
                + item
            )


    if ":fps=" not in vf:

        blockers.append(
            "zoompan_fps_missing"
        )


    return (
        blockers,
        warnings
    )


def preview(candidate):

    if not candidate:

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["candidate_missing"],
            "filter_applied":
                False,
        }


    legacy = candidate.get(
        "legacy_vf"
    )


    proposed = candidate.get(
        "proposed_vi6_vf"
    )


    blockers, warnings = _validate(
        proposed
    )


    if not isinstance(
        legacy,
        str
    ):

        blockers.append(
            "legacy_filter_missing"
        )


    different = (
        isinstance(legacy, str)
        and isinstance(
            proposed,
            str
        )
        and legacy != proposed
    )


    if not different:

        blockers.append(
            "vi6_filter_not_different"
        )


    compile_data = (
        candidate.get(
            "motion_compile"
        )
        or {}
    )


    if (
        compile_data.get(
            "status"
        )
        != "COMPILED"
    ):

        blockers.append(
            "motion_filter_not_compiled"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "PREVIEW_READY"
                if not blockers
                else "HOLD"
            ),

        "scene":
            candidate.get(
                "scene"
            ),

        "motion_profile":
            candidate.get(
                "recommended_motion_profile"
            ),

        "legacy_vf":
            legacy,

        "proposed_vi6_vf":
            proposed,

        "previous_dry_plan_vf":
            candidate.get(
                "previous_dry_plan_vf"
            ),

        "different_from_legacy":
            different,

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            warnings,

        "filter_applied":
            False,

        "command_mutated":
            False,
    }


def self_test():

    proposed = (
        "scale=1200:2133:"
        "force_original_aspect_ratio=increase,"
        "crop=1200:2133,"
        "zoompan="
        "z='1.01':"
        "x='0':"
        "y='0':"
        "d=102:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1,"
        "format=yuv420p"
    )


    result = preview(
        {
            "scene":
                5,

            "recommended_motion_profile":
                "SLOW_PUSH",

            "legacy_vf":
                "legacy",

            "proposed_vi6_vf":
                proposed,

            "motion_compile": {
                "status":
                    "COMPILED"
            },
        }
    )


    assert (
        result["status"]
        == "PREVIEW_READY"
    )


    assert (
        result["filter_applied"]
        is False
    )


    print(
        "VI6.66.1 FILTER PREVIEW=PASS"
    )


if __name__ == "__main__":
    self_test()

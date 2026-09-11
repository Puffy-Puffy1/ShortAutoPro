#!/usr/bin/env python3


VERSION = "6.38"


FORBIDDEN = (
    "\n",
    "\r",
    ";",
    "&&",
    "||",
    "`",
    "$(",
)


ALLOWED_FILTERS = {
    "scale",
    "crop",
    "zoompan",
    "format",
    "fps",
}


def _balanced(
    text,
    opening,
    closing
):

    count = 0


    for char in text:

        if char == opening:

            count += 1

        elif char == closing:

            count -= 1


        if count < 0:

            return False


    return count == 0


def _filter_names(vf):

    names = []


    for segment in vf.split(
        ","
    ):

        segment = (
            segment.strip()
        )


        if not segment:

            continue


        name = segment.split(
            "=",
            1
        )[0].strip()


        # Expressões internas do zoompan
        # podem conter vírgulas apenas quando
        # a sintaxe futura mudar. No compilador
        # atual não devem aparecer.
        if name:

            names.append(
                name
            )


    return names


def validate(
    dry_plan
):

    issues = []
    warnings = []


    if (
        dry_plan.get(
            "mode"
        )
        != "DRY_RUN"
    ):

        issues.append(
            "not_dry_run"
        )


    if (
        dry_plan.get(
            "executed"
        )
        is not False
    ):

        issues.append(
            "execution_flag_true"
        )


    mode = (
        dry_plan.get(
            "renderer_mode"
        )
    )


    if mode == "NATIVE_VIDEO_PRESERVE":

        if dry_plan.get(
            "vf"
        ):

            issues.append(
                "video_should_not_have_synthetic_vf"
            )


        return {

            "version":
                VERSION,

            "status":
                (
                    "PASS"
                    if not issues
                    else "HOLD"
                ),

            "mode":
                mode,

            "issues":
                issues,

            "warnings":
                warnings,

            "static_only":
                True,
        }


    if mode == "NO_RENDER_PLAN":

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "mode":
                mode,

            "issues":
                [
                    "no_render_plan"
                ],

            "warnings":
                [],

            "static_only":
                True,
        }


    vf = str(
        dry_plan.get(
            "vf"
        )
        or ""
    )


    if not vf:

        issues.append(
            "empty_filter"
        )


    for marker in FORBIDDEN:

        if marker in vf:

            issues.append(
                "forbidden_token:"
                + repr(
                    marker
                )
            )


    if not _balanced(
        vf,
        "(",
        ")"
    ):

        issues.append(
            "unbalanced_parentheses"
        )


    if (
        vf.count("'")
        % 2
        != 0
    ):

        issues.append(
            "unbalanced_single_quotes"
        )


    names = _filter_names(
        vf
    )


    unknown = [
        name
        for name in names
        if name
        not in ALLOWED_FILTERS
    ]


    if unknown:

        issues.append(
            "unknown_filter:"
            + ",".join(
                sorted(
                    set(
                        unknown
                    )
                )
            )
        )


    if mode == "KEN_BURNS_STILL":

        required = (
            "scale=",
            "crop=",
            "zoompan=",
            "format=yuv420p",
        )


        for marker in required:

            if marker not in vf:

                issues.append(
                    "missing:"
                    + marker
                )


        if (
            vf.count(
                "zoompan="
            )
            != 1
        ):

            issues.append(
                "zoompan_count"
            )


        if (
            "1080"
            not in vf
            or "1920"
            not in vf
        ):

            issues.append(
                "target_dimensions_missing"
            )


    if mode == "STATIC_STILL":

        if "zoompan=" in vf:

            issues.append(
                "static_still_contains_zoompan"
            )


    argv = (
        dry_plan.get(
            "argv"
        )
    )


    if mode in {
        "KEN_BURNS_STILL",
        "STATIC_STILL",
    }:

        if not isinstance(
            argv,
            list
        ):

            issues.append(
                "argv_not_list"
            )


        else:

            if (
                not argv
                or argv[0]
                != "ffmpeg"
            ):

                issues.append(
                    "argv_missing_ffmpeg"
                )


            if "{INPUT}" not in argv:

                issues.append(
                    "input_placeholder_missing"
                )


            if "{OUTPUT}" not in argv:

                issues.append(
                    "output_placeholder_missing"
                )


            if "{DURATION}" not in argv:

                issues.append(
                    "duration_placeholder_missing"
                )


    status = (
        "PASS"
        if not issues
        else "HOLD"
    )


    return {

        "version":
            VERSION,

        "status":
            status,

        "mode":
            mode,

        "filters":
            names,

        "issues":
            issues,

        "warnings":
            warnings,

        "static_only":
            True,

        "ffmpeg_executed":
            False,
    }


def self_test():

    good = {

        "mode":
            "DRY_RUN",

        "executed":
            False,

        "renderer_mode":
            "KEN_BURNS_STILL",

        "vf":
            (
                "scale=1080:1920:"
                "force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "zoompan=z='1+0.04*(on/119)':"
                "x='(iw-iw/zoom)*(0.5)':"
                "y='(ih-ih/zoom)*(0.5)':"
                "d=120:s=1080x1920:fps=30,"
                "format=yuv420p"
            ),

        "argv":
            [
                "ffmpeg",
                "-loop",
                "1",
                "-i",
                "{INPUT}",
                "-vf",
                "{FILTER}",
                "-t",
                "{DURATION}",
                "{OUTPUT}",
            ],
    }


    result = validate(
        good
    )


    assert (
        result[
            "status"
        ]
        == "PASS"
    )


    bad = dict(
        good
    )


    bad[
        "vf"
    ] = (
        good[
            "vf"
        ]
        + ";rm -rf something"
    )


    result = validate(
        bad
    )


    assert (
        result[
            "status"
        ]
        == "HOLD"
    )


    video = validate(
        {
            "mode":
                "DRY_RUN",

            "executed":
                False,

            "renderer_mode":
                "NATIVE_VIDEO_PRESERVE",

            "vf":
                None,

            "argv":
                None,
        }
    )


    assert (
        video[
            "status"
        ]
        == "PASS"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.38 FILTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Filter Whitelist"
    )
    print(
        "OK Parenthesis Validation"
    )
    print(
        "OK Quote Validation"
    )
    print(
        "OK Injection Token Guard"
    )
    print(
        "OK Ken Burns Structure"
    )
    print(
        "OK Native Video No-Op"
    )
    print(
        "OK Zero FFmpeg Execution"
    )
    print()


if __name__ == "__main__":

    self_test()

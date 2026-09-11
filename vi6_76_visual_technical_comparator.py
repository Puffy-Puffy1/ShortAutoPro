#!/usr/bin/env python3

VERSION = "6.76"


def _float(value):

    try:
        return float(value)

    except Exception:
        return None


def compare(
    legacy,
    vi6
):

    blockers = []

    warnings = []


    if legacy.get(
        "status"
    ) != "PASS":

        blockers.append(
            "legacy_probe_hold"
        )


    if vi6.get(
        "status"
    ) != "PASS":

        blockers.append(
            "vi6_probe_hold"
        )


    for side, data in (
        ("legacy", legacy),
        ("vi6", vi6),
    ):

        if (
            data.get("width")
            != 1080
            or data.get("height")
            != 1920
        ):

            blockers.append(
                side
                + "_resolution_invalid"
            )


        if (
            data.get("pix_fmt")
            not in {
                "yuv420p",
                "yuvj420p",
            }
        ):

            blockers.append(
                side
                + "_pixfmt_invalid"
            )


    ld = _float(
        legacy.get(
            "duration"
        )
    )


    vd = _float(
        vi6.get(
            "duration"
        )
    )


    delta = None


    if (
        ld is not None
        and vd is not None
    ):

        delta = abs(
            ld - vd
        )


        if delta > .12:

            blockers.append(
                "duration_delta_too_high"
            )


    else:

        blockers.append(
            "duration_missing"
        )


    if (
        legacy.get(
            "codec"
        )
        != "h264"
    ):

        warnings.append(
            "legacy_codec_not_h264"
        )


    if (
        vi6.get(
            "codec"
        )
        != "h264"
    ):

        warnings.append(
            "vi6_codec_not_h264"
        )


    status = (
        "HOLD"
        if blockers
        else (
            "PASS_WITH_WARNINGS"
            if warnings
            else "PASS"
        )
    )


    return {
        "version": VERSION,

        "status": status,

        "duration_delta":
            (
                round(
                    delta,
                    4
                )
                if delta is not None
                else None
            ),

        "same_resolution":
            (
                legacy.get("width")
                == vi6.get("width")
                and legacy.get("height")
                == vi6.get("height")
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "visual_quality_human_review_required":
            True,
    }


def self_test():

    base = {
        "status": "PASS",
        "width": 1080,
        "height": 1920,
        "pix_fmt": "yuv420p",
        "codec": "h264",
        "duration": "4.0",
    }


    assert compare(
        dict(base),
        dict(base)
    )["status"] == "PASS"


    print(
        "VI6.76 TECHNICAL COMPARATOR=PASS"
    )


if __name__ == "__main__":
    self_test()

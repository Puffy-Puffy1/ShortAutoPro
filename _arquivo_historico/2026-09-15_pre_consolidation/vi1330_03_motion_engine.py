#!/usr/bin/env python3


def zoompan(
    frames,
    *,
    max_zoom,
    speed,
    x="iw/2-(iw/zoom/2)",
    y="ih/2-(ih/zoom/2)",
):
    return (
        "zoompan="
        "z='min(zoom+"
        + f"{speed:.8f}"
        + ","
        + f"{max_zoom:.5f}"
        + ")':"
        "x='"
        + x
        + "':"
        "y='"
        + y
        + "':"
        "d="
        + str(
            frames
        )
        + ":"
        "s=1080x1920:"
        "fps=30"
    )


def image_filter(
    strategy,
    frames,
):
    if strategy == "HOTEL_SIGN_TIGHT":

        return (
            "crop=620:1480:300:80,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.045,
                speed=0.00023,
            )
            +
            ",format=yuv420p"
        )


    if strategy == "HOTEL_FACADE_WIDE":

        return (
            zoompan(
                frames,
                max_zoom=1.035,
                speed=0.00014,
                x="iw/2-(iw/zoom/2)",
                y="ih/2-(ih/zoom/2)-25",
            )
            +
            ",format=yuv420p"
        )


    if strategy == "HALLWAY_MONO_PUSH":

        return (
            zoompan(
                frames,
                max_zoom=1.05,
                speed=0.00028,
                x="iw/2-(iw/zoom/2)+20",
            )
            +
            ",format=yuv420p"
        )


    if strategy == "HALLWAY_RED_DRIFT":

        return (
            "scale=1160:2062,"
            "crop=1080:1920:"
            "x='70-40*t/4':"
            "y=60,"
            "fps=30,"
            "format=yuv420p"
        )


    if strategy == "ELEVATOR_INTERIOR_PUSH":

        return (
            "crop=980:1540:50:190,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.055,
                speed=0.00030,
            )
            +
            ",format=yuv420p"
        )


    if strategy == "CCTV_CAMERA_FOCUS":

        return (
            "crop=900:1450:90:130,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.06,
                speed=0.00034,
                y="ih/2-(ih/zoom/2)-60",
            )
            +
            ",format=yuv420p"
        )


    if strategy == "MEDICAL_GRAPH_FOCUS":

        return (
            "crop=980:940:50:470,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.055,
                speed=0.00025,
            )
            +
            ",eq=contrast=1.04,"
            "format=yuv420p"
        )


    if strategy == "WORKER_SUBJECT_FOCUS":

        # The worker in the current certified asset is
        # concentrated in the lower-left/central region.
        return (
            "crop=720:1080:80:690,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.06,
                speed=0.00031,
                x="iw/2-(iw/zoom/2)-35",
                y="ih/2-(ih/zoom/2)+25",
            )
            +
            ",vignette=PI/7,"
            "format=yuv420p"
        )


    if strategy == "WATER_TANK_SUBJECT_FOCUS":

        # Stronger lower-frame crop than VI1320:
        # skyline becomes context, tanks become subject.
        return (
            "crop=880:1120:100:680,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.06,
                speed=0.00030,
                x="iw/2-(iw/zoom/2)+20",
                y="ih/2-(ih/zoom/2)+35",
            )
            +
            ",eq=contrast=1.035,"
            "format=yuv420p"
        )


    if strategy == "AUTOPSY_DOCUMENT_FOCUS":

        return (
            "crop=940:1220:70:190,"
            "scale=1080:1920,"
            +
            zoompan(
                frames,
                max_zoom=1.045,
                speed=0.00020,
                y="ih/2-(ih/zoom/2)-35",
            )
            +
            ",eq=contrast=1.06,"
            "format=yuv420p"
        )


    return (
        zoompan(
            frames,
            max_zoom=1.04,
            speed=0.00018,
        )
        +
        ",format=yuv420p"
    )

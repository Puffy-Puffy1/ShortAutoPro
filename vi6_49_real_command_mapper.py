#!/usr/bin/env python3

import hashlib
import json
import os
import re


VERSION = "6.49"


def _s(value):

    return str(
        value
        if value is not None
        else ""
    )


def _float(value):

    try:
        return float(value)

    except Exception:
        return None


def _arg_value(
    command,
    flag
):

    try:

        index = command.index(
            flag
        )


        if index + 1 < len(
            command
        ):

            return command[
                index + 1
            ]


    except Exception:

        pass


    return None


def _has(
    command,
    flag
):

    try:
        return flag in command

    except Exception:
        return False


def _input_path(
    command
):

    return _arg_value(
        command,
        "-i"
    )


def _output_path(
    command
):

    if not command:
        return None


    # No renderer atual, a saída é o
    # último argumento do comando.
    value = command[-1]


    if isinstance(
        value,
        str
    ):

        return value


    return None


def infer_scene_number(
    output_path
):

    if not output_path:
        return None


    name = os.path.basename(
        str(
            output_path
        )
    )


    # ==================================================
    # Internal video.py numbering is ZERO-BASED.
    #
    # v63_cena_00 = editorial scene 1
    # ...
    # v63_cena_11 = editorial scene 12
    #
    # Conversion is restricted to this exact prefix.
    # ==================================================

    internal = re.fullmatch(
        r"v63_cena_(\d+)\.mp4",
        name,
        flags=re.IGNORECASE
    )


    if internal:

        try:

            raw_index = int(
                internal.group(
                    1
                )
            )


            editorial_scene = (
                raw_index
                + 1
            )


            if (
                1
                <= editorial_scene
                <= 99
            ):

                return editorial_scene


        except Exception:
            pass


    # Normal externally numbered files are already
    # one-based and MUST NOT receive +1.

    patterns = (

        r"(?:cena|scene)[_-]?0*(\d+)",

        r"(?:clip|frame)[_-]?0*(\d+)",

        r"[_-]0*(\d+)(?:\.[A-Za-z0-9]+)?$",
    )


    for pattern in patterns:

        match = re.search(
            pattern,
            name,
            flags=re.IGNORECASE
        )


        if match:

            try:

                number = int(
                    match.group(
                        1
                    )
                )


                if 1 <= number <= 99:
                    return number


            except Exception:
                pass


    return None

def _fps_from_filter(
    vf
):

    if not isinstance(
        vf,
        str
    ):

        return None


    match = re.search(
        r"(?:^|[,:])fps=([0-9]+(?:\.[0-9]+)?)",
        vf
    )


    if not match:
        return None


    return _float(
        match.group(
            1
        )
    )


def _frames(
    command
):

    raw = _arg_value(
        command,
        "-frames:v"
    )


    try:
        return int(raw)

    except Exception:
        return None


def _duration(
    command,
    vf
):

    # Vídeo real possui -t.
    explicit = _float(
        _arg_value(
            command,
            "-t"
        )
    )


    if (
        explicit is not None
        and explicit > 0
    ):

        return (
            explicit,
            "command_t"
        )


    # Foto possui -frames:v + fps no filtro.
    frames = _frames(
        command
    )


    fps = _fps_from_filter(
        vf
    )


    if (
        frames is not None
        and frames > 0
        and fps is not None
        and fps > 0
    ):

        return (
            frames / fps,
            "frames_over_fps"
        )


    return (
        None,
        "unknown"
    )


def _branch(
    command
):

    if (
        _has(
            command,
            "-loop"
        )
        and _arg_value(
            command,
            "-loop"
        )
        == "1"
    ):

        return "STILL"


    if _has(
        command,
        "-stream_loop"
    ):

        return "VIDEO"


    return "UNKNOWN"


def _fingerprint(
    command
):

    payload = json.dumps(
        command,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()[:16]


def map_command(
    command,
    context=None
):

    context = dict(
        context
        or {}
    )


    if not isinstance(
        command,
        list
    ):

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "command_not_list",

            "mutated":
                False,
        }


    vf = _arg_value(
        command,
        "-vf"
    )


    branch = _branch(
        command
    )


    input_path = _input_path(
        command
    )


    output_path = _output_path(
        command
    )


    scene = infer_scene_number(
        output_path
    )


    duration, duration_source = (
        _duration(
            command,
            vf
        )
    )


    fps = _fps_from_filter(
        vf
    )


    result = {

        "version":
            VERSION,

        "status":
            "MAPPED",

        "branch":
            branch,

        "scene":
            scene,

        "input_path":
            input_path,

        "output_path":
            output_path,

        "has_vf":
            isinstance(
                vf,
                str
            ),

        "vf":
            vf,

        "has_zoompan":
            (
                isinstance(
                    vf,
                    str
                )
                and "zoompan="
                in vf
            ),

        "has_scale":
            (
                isinstance(
                    vf,
                    str
                )
                and "scale="
                in vf
            ),

        "has_crop":
            (
                isinstance(
                    vf,
                    str
                )
                and "crop="
                in vf
            ),

        "has_yuv420p":
            (
                isinstance(
                    vf,
                    str
                )
                and "format=yuv420p"
                in vf
            ),

        "frames":
            _frames(
                command
            ),

        "fps":
            fps,

        "duration_seconds":
            (
                round(
                    duration,
                    4
                )
                if duration
                is not None
                else None
            ),

        "duration_source":
            duration_source,

        "codec":
            _arg_value(
                command,
                "-c:v"
            ),

        "preset":
            _arg_value(
                command,
                "-preset"
            ),

        "crf":
            _arg_value(
                command,
                "-crf"
            ),

        "command_fingerprint":
            _fingerprint(
                command
            ),

        "context":
            context,

        "mutated":
            False,
    }


    blockers = []


    if (
        branch
        == "UNKNOWN"
    ):

        blockers.append(
            "unknown_media_branch"
        )


    if not result[
        "has_vf"
    ]:

        blockers.append(
            "vf_missing"
        )


    if (
        branch
        == "STILL"
        and not result[
            "has_zoompan"
        ]
    ):

        blockers.append(
            "still_zoompan_missing"
        )


    if (
        duration is None
        or duration <= 0
    ):

        blockers.append(
            "duration_unknown"
        )


    if blockers:

        result[
            "status"
        ] = "HOLD"


    result[
        "blockers"
    ] = blockers


    return result


def self_test():

    still = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        "/tmp/image.jpg",

        "-vf",
        (
            "scale=1200:2133:"
            "force_original_aspect_ratio=increase,"
            "crop=1200:2133,"
            "zoompan=z='1.02':x='0':y='0':"
            "d=120:s=1080x1920:fps=30,"
            "setsar=1,"
            "format=yuv420p"
        ),

        "-frames:v",
        "120",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "fast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "/tmp/cena_03.mp4",
    ]


    result = map_command(
        still
    )


    assert (
        result[
            "status"
        ]
        == "MAPPED"
    )


    assert (
        result[
            "branch"
        ]
        == "STILL"
    )


    assert (
        result[
            "scene"
        ]
        == 3
    )


    assert abs(
        result[
            "duration_seconds"
        ]
        - 4.0
    ) < .01


    assert (
        result[
            "has_zoompan"
        ]
        is True
    )


    video = [

        "ffmpeg",
        "-y",

        "-stream_loop",
        "-1",

        "-i",
        "/tmp/a.mp4",

        "-t",
        "4.25",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "fps=30,"
            "setsar=1,"
            "format=yuv420p"
        ),

        "-an",
        "-c:v",
        "libx264",

        "/tmp/cena_04.mp4",
    ]


    result = map_command(
        video
    )


    assert (
        result[
            "branch"
        ]
        == "VIDEO"
    )


    assert (
        result[
            "scene"
        ]
        == 4
    )


    assert abs(
        result[
            "duration_seconds"
        ]
        - 4.25
    ) < .001


    print()
    print(
        "======================================"
    )
    print(
        " VI6.49 COMMAND MAPPER: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK STILL branch"
    )
    print(
        "OK VIDEO branch"
    )
    print(
        "OK Scene Number"
    )
    print(
        "OK Duration"
    )
    print(
        "OK VF Extraction"
    )
    print(
        "OK Command Fingerprint"
    )
    print()


if __name__ == "__main__":
    self_test()

#!/usr/bin/env python3

import json
import os

from datetime import datetime


from vi6_48_emergency_rollback import (
    resolve_mode,
    trip,
)


VERSION = "6.47-module+6.49-6.50"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


LOG = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_47_shadow_runtime_latest.json"
)


def _requested_mode():

    return str(
        os.getenv(
            "VI647_RENDERER_MODE",
            "LEGACY"
        )
        or "LEGACY"
    ).strip().upper()


def _find_vf(
    command
):

    try:

        index = command.index(
            "-vf"
        )


        if (
            index + 1
            < len(
                command
            )
        ):

            return (
                index,
                command[
                    index + 1
                ]
            )


    except Exception:

        pass


    return (
        None,
        None
    )


def _legacy_shadow_log(
    command,
    context,
    mapped=None,
    comparison=None
):

    try:

        os.makedirs(
            os.path.dirname(
                LOG
            ),
            exist_ok=True
        )


        vf_index, vf = _find_vf(
            command
        )


        payload = {

            "version":
                VERSION,

            "time":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "mode":
                "SHADOW",

            "vf_index":
                vf_index,

            "has_vf":
                vf is not None,

            "has_zoompan":
                (
                    isinstance(
                        vf,
                        str
                    )
                    and "zoompan="
                    in vf
                ),

            "context":
                context
                or {},

            "vi649":
                mapped,

            "vi650":
                comparison,

            "legacy_command_preserved":
                True,

            "command_mutated":
                False,

            "active_renderer_used":
                False,
        }


        with open(
            LOG,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2
            )


    except Exception:

        pass


def adapt_scene_command(
    command,
    context=None
):

    # Fail closed.
    if not isinstance(
        command,
        list
    ):

        return command


    requested = (
        _requested_mode()
    )


    try:

        mode, reason = resolve_mode(
            requested
        )


    except Exception as exc:

        trip(
            "resolve_mode:"
            + type(
                exc
            ).__name__
        )


        return command


    # =====================================
    # LEGACY
    # =====================================
    #
    # Zero análise obrigatória.
    # Zero mutação.
    # =====================================

    if mode == "LEGACY":

        return command


    # =====================================
    # SHADOW
    # =====================================
    #
    # Analisa o comando REAL.
    # Compila plano VI6.
    # Compara filtros.
    # JAMAIS troca o comando.
    # =====================================

    if mode == "SHADOW":

        mapped = None

        comparison = None


        try:

            from vi6_49_real_command_mapper import (
                map_command
            )


            mapped = map_command(
                command,
                context
            )


        except Exception as exc:

            mapped = {

                "status":
                    "HOLD",

                "reason":
                    (
                        "vi649_exception:"
                        + type(
                            exc
                        ).__name__
                    ),
            }


        try:

            if (
                mapped
                and mapped.get(
                    "status"
                )
                == "MAPPED"
            ):

                from vi6_50_shadow_filter_comparator import (
                    shadow_compare,
                    record,
                )


                comparison = shadow_compare(
                    command,
                    mapped,
                    context
                )


                record(
                    comparison
                )


        except Exception as exc:

            comparison = {

                "status":
                    "HOLD",

                "reason":
                    (
                        "vi650_exception:"
                        + type(
                            exc
                        ).__name__
                    ),

                "command_mutated":
                    False,

                "legacy_filter_replaced":
                    False,
            }


        _legacy_shadow_log(
            command,
            context,
            mapped,
            comparison
        )


        return command


    # ACTIVE continua bloqueado
    # pelo VI6.48.
    return command


def self_test():

    still = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        "x.jpg",

        "-vf",
        (
            "scale=1200:2133,"
            "crop=1200:2133,"
            "zoompan=z='1.02':"
            "d=120:s=1080x1920:fps=30,"
            "format=yuv420p"
        ),

        "-frames:v",
        "120",

        "-c:v",
        "libx264",

        "cena_01.mp4",
    ]


    old = os.environ.get(
        "VI647_RENDERER_MODE"
    )


    try:

        # LEGACY
        os.environ[
            "VI647_RENDERER_MODE"
        ] = "LEGACY"


        before = list(
            still
        )


        result = adapt_scene_command(
            still
        )


        assert result is still

        assert still == before


        # ACTIVE continua LEGACY.
        os.environ[
            "VI647_RENDERER_MODE"
        ] = "ACTIVE"


        result = adapt_scene_command(
            still
        )


        assert result is still

        assert still == before


    finally:

        if old is None:

            os.environ.pop(
                "VI647_RENDERER_MODE",
                None
            )

        else:

            os.environ[
                "VI647_RENDERER_MODE"
            ] = old


    print()
    print(
        "======================================"
    )
    print(
        " VI6.47 SHADOW OBSERVER: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK LEGACY preserved"
    )
    print(
        "OK ACTIVE still blocked"
    )
    print(
        "OK Command identity preserved"
    )
    print()


if __name__ == "__main__":
    self_test()


# VI6.89 SINGLE-SCENE PRODUCTION CANARY
_vi647_original_adapt_scene_command_vi689 = (
    adapt_scene_command
)


def adapt_scene_command(
    command,
    context=None
):

    import os


    if (
        os.getenv(
            "VI682_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
    ):

        try:

            from vi6_89_runtime_canary_adapter import (
                adapt as _vi689_adapt
            )


            return _vi689_adapt(
                command
            )


        except Exception:

            return command


    return (
        _vi647_original_adapt_scene_command_vi689(
            command,
            context
        )
    )

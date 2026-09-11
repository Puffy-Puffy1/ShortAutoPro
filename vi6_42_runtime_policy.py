#!/usr/bin/env python3

import json
import os
from datetime import datetime


import vi6_6_active_brain as brain


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_40_controlled_renderer_bridge import (
    build_shadow_request
)


_ADAPTER = inspect_renderer(
    "video.py"
)


_EVENTS = []


if not getattr(
    brain,
    "_VI642_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_642 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_642(
        vi6_scene,
        candidatos,
        cena,
        current_candidate,
        current_reason
    ):

        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        try:

            number = int(
                board.get(
                    "scene",
                    0
                )
                or 0
            )

        except Exception:

            number = 0


        if number == 1:

            _EVENTS.clear()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_642(
            vi6_scene,
            candidatos,
            cena,
            current_candidate,
            current_reason
        )


        meta = dict(
            meta
            or {}
        )


        bridge = build_shadow_request(
            meta,
            _ADAPTER
        )


        meta[
            "vi640_renderer_bridge"
        ] = bridge


        meta[
            "vi640_renderer_mode"
        ] = "SHADOW"


        meta[
            "vi640_binding_performed"
        ] = False


        event = {

            "scene":
                number,

            "status":
                bridge.get(
                    "status"
                ),

            "renderer_mode":
                bridge.get(
                    "renderer_mode"
                ),

            "target_function":
                bridge.get(
                    "target_function"
                ),

            "target_line":
                bridge.get(
                    "target_line_start"
                ),

            "filter_ready":
                (
                    bridge.get(
                        "filter_report"
                    )
                    or {}
                ).get(
                    "status"
                ),

            "binding_performed":
                False,
        }


        _EVENTS.append(
            event
        )


        if candidate is not None:

            candidate[
                "_vi640_bridge_status"
            ] = bridge.get(
                "status"
            )


            candidate[
                "_vi640_renderer_mode"
            ] = "SHADOW"


            candidate[
                "_vi640_binding_performed"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                folder = os.path.expanduser(
                    "~/ShortAutoPro/logs/producao"
                )


                os.makedirs(
                    folder,
                    exist_ok=True
                )


                path = os.path.join(
                    folder,
                    "vi6_40_shadow_runtime_latest.json"
                )


                with open(
                    path,
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        {
                            "generated_at":
                                datetime.now().isoformat(
                                    timespec="seconds"
                                ),

                            "mode":
                                "SHADOW",

                            "events":
                                list(
                                    _EVENTS
                                ),

                            "renderer_active":
                                False,

                            "binding_performed":
                                False,
                        },
                        file,
                        ensure_ascii=False,
                        indent=2
                    )


                meta[
                    "vi640_shadow_report_path"
                ] = path


            except Exception as exc:

                meta[
                    "vi640_shadow_report_error"
                ] = (
                    f"{type(exc).__name__}:"
                    f"{str(exc)[:120]}"
                )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped_642
    )


    brain._VI640_RUNTIME_ACTIVE = True
    brain._VI642_RUNTIME_ACTIVE = True

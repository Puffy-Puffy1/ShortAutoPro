#!/usr/bin/env python3

import vi6_6_active_brain as brain


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer,
    save_report as save_adapter_report,
)


from vi6_38_filter_validator import (
    validate as validate_filter
)


from vi6_39_activation_gate import (
    evaluate as activation_evaluate,
    record,
    reset,
    flush,
)


_ADAPTER = inspect_renderer(
    "video.py"
)


if not getattr(
    brain,
    "_VI639_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_639 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_639(
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

            reset()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_639(
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


        contract = (
            meta.get(
                "vi634_repaired_contract"
            )
            or meta.get(
                "vi630_renderer_contract"
            )
            or {}
        )


        safety = (
            meta.get(
                "vi633_post_repair_safety"
            )
            or meta.get(
                "vi633_cinematic_safety"
            )
            or {}
        )


        dry_plan = (
            meta.get(
                "vi635_ffmpeg_dry_plan"
            )
            or {}
        )


        compatibility = (
            meta.get(
                "vi636_renderer_compatibility"
            )
            or {}
        )


        filter_report = validate_filter(
            dry_plan
        )


        gate = activation_evaluate(
            _ADAPTER,
            filter_report,
            compatibility,
            safety,
            contract,
            dry_plan
        )


        record(
            number,
            gate
        )


        meta[
            "vi637_renderer_shadow"
        ] = {

            "status":
                _ADAPTER.get(
                    "status"
                ),

            "reason":
                _ADAPTER.get(
                    "reason"
                ),

            "best":
                _ADAPTER.get(
                    "best"
                ),

            "video_sha256":
                _ADAPTER.get(
                    "file_sha256"
                ),

            "file_modified":
                False,
        }


        meta[
            "vi638_filter_validation"
        ] = filter_report


        meta[
            "vi639_activation_gate"
        ] = gate


        meta[
            "vi639_renderer_active"
        ] = False


        meta[
            "vi639_ffmpeg_active"
        ] = False


        if candidate is not None:

            candidate[
                "_vi637_shadow_status"
            ] = _ADAPTER.get(
                "status"
            )


            candidate[
                "_vi638_filter_status"
            ] = filter_report.get(
                "status"
            )


            candidate[
                "_vi639_activation_status"
            ] = gate.get(
                "status"
            )


            candidate[
                "_vi639_renderer_active"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi637_shadow_report_path"
                ] = save_adapter_report(
                    _ADAPTER
                )


                meta[
                    "vi639_gate_path"
                ] = flush()


            except Exception as exc:

                meta[
                    "vi639_report_error"
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
        _wrapped_639
    )


    brain._VI637_RUNTIME_ACTIVE = True
    brain._VI638_RUNTIME_ACTIVE = True
    brain._VI639_RUNTIME_ACTIVE = True

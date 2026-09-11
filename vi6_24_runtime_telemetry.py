#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_22_story_audit import (
    record_final,
    summary as story_summary,
    reset as story_reset,
)

from vi6_24_production_telemetry import (
    record as telemetry_record,
    flush as telemetry_flush,
    reset as telemetry_reset,
)


if not getattr(
    brain,
    "_VI624_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_624 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_624(
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

            story_reset()
            telemetry_reset()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_624(
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


        # O VI6.23 ajusta o resultado do
        # evaluator. Quando esse valor chegou
        # ao supervisor, preservamos o estado
        # quando disponível.
        if candidate is not None:

            adjustment = (
                candidate.get(
                    "_vi623_adjustment"
                )
            )


            if adjustment is not None:

                meta[
                    "vi623_adjustment"
                ] = adjustment


        record_final(
            cena,
            candidate,
            reason,
            meta
        )


        state = story_summary()


        telemetry_record(
            cena,
            candidate,
            reason,
            meta,
            state
        )


        meta[
            "vi622_story_state"
        ] = {

            "documentary":
                state.get(
                    "documentary"
                ),

            "documentary_target":
                state.get(
                    "documentary_target"
                ),

            "documentary_needed":
                state.get(
                    "documentary_needed"
                ),

            "documentary_urgency":
                state.get(
                    "documentary_urgency"
                ),

            "fallback":
                state.get(
                    "fallback"
                ),

            "true_recovery":
                state.get(
                    "true_recovery"
                ),

            "low_confidence_scenes":
                state.get(
                    "low_confidence_scenes"
                ),
        }


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi624_telemetry_path"
                ] = telemetry_flush(
                    state
                )

            except Exception as exc:

                meta[
                    "vi624_telemetry_error"
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
        _wrapped_624
    )


    brain._VI624_RUNTIME_ACTIVE = True

#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_27_transition_intelligence import (
    record,
    flush,
    reset,
)


if not getattr(
    brain,
    "_VI627_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_627 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_627(
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
        ) = _base_supervisor_627(
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


        transition = record(
            cena,
            candidate,
            meta
        )


        meta[
            "vi625_sequence_intent"
        ] = transition.get(
            "intent"
        )


        meta[
            "vi627_transition"
        ] = transition.get(
            "transition"
        )


        meta[
            "vi627_transition_reason"
        ] = transition.get(
            "reason"
        )


        meta[
            "vi627_renderer_applied"
        ] = False


        if candidate is not None:

            candidate[
                "_vi625_sequence_intent"
            ] = transition.get(
                "intent"
            )


            candidate[
                "_vi627_transition"
            ] = transition.get(
                "transition"
            )


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi627_sequence_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi627_sequence_error"
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
        _wrapped_627
    )


    brain._VI627_RUNTIME_ACTIVE = True

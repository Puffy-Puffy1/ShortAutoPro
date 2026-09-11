#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_26_motion_strategy import (
    adjust
)


if not getattr(
    brain,
    "_VI626_RUNTIME_ACTIVE",
    False
):

    _base_evaluate_626 = (
        brain.evaluate
    )


    def _evaluate_626(
        item,
        cena,
        vi6_scene=None
    ):

        result = (
            _base_evaluate_626(
                item,
                cena,
                vi6_scene
            )
        )


        if result is None:

            return None


        return adjust(
            result,
            item,
            cena
        )


    brain.evaluate = (
        _evaluate_626
    )


    brain._VI626_RUNTIME_ACTIVE = True

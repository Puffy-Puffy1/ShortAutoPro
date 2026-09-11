#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_23_adaptive_budget import (
    adjust_result
)


if not getattr(
    brain,
    "_VI623_RUNTIME_ACTIVE",
    False
):

    _base_evaluate_623 = (
        brain.evaluate
    )


    def _evaluate_623(
        item,
        cena,
        vi6_scene=None
    ):

        result = (
            _base_evaluate_623(
                item,
                cena,
                vi6_scene
            )
        )


        if result is None:

            return None


        return adjust_result(
            result,
            cena
        )


    brain.evaluate = (
        _evaluate_623
    )


    brain._VI623_RUNTIME_ACTIVE = True

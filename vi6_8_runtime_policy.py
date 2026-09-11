#!/usr/bin/env python3

# =====================================================
# VI6.8 GLOBAL STORYBOARD RUNTIME POLICY
#
# Monkey-patch controlado do evaluator VI6.6.
#
# Não busca.
# Não baixa.
# Não renderiza.
# =====================================================


import vi6_6_active_brain as brain


if not getattr(
    brain,
    "_VI68_RUNTIME_PATCHED",
    False
):

    _base_evaluate_6_6 = (
        brain.evaluate
    )


    def evaluate_6_8(
        item,
        cena,
        vi6_scene=None
    ):

        result = _base_evaluate_6_6(
            item,
            cena,
            vi6_scene
        )


        if result is None:

            return None


        global_plan = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        if not global_plan:

            return result


        score = float(
            result.get(
                "score",
                0.0
            )
        )


        reasons = list(
            result.get(
                "reasons",
                []
            )
        )


        classe = str(
            result.get(
                "class",
                ""
            )
        ).upper()


        semantic = float(
            result.get(
                "semantic",
                0.0
            )
            or 0.0
        )


        media_type = str(
            item.get(
                "tipo"
            )
            or item.get(
                "type"
            )
            or ""
        ).lower()


        # =============================================
        # GLOBAL DOCUMENTARY TARGET
        # =============================================

        if global_plan.get(
            "prefer_documentary"
        ):

            if (
                classe
                == "REAL_DOCUMENTARY"
                and result.get(
                    "truth_ok",
                    False
                )
            ):

                score += 10.0

                reasons.append(
                    "vi68_documentary_target"
                )


            elif (
                classe
                == "SAFE_CONTEXT"
            ):

                score -= 4.0

                reasons.append(
                    "vi68_stock_deprioritized"
                )


        # =============================================
        # MOTION BUDGET
        # =============================================

        if global_plan.get(
            "prefer_motion"
        ):

            if (
                media_type
                in {
                    "video",
                    "vídeo"
                }
                and semantic >= 58.0
            ):

                score += 4.0

                reasons.append(
                    "vi68_motion_target"
                )


        # =============================================
        # PHOTO IS VALID FOR DOCUMENTARY
        # =============================================

        if (
            global_plan.get(
                "photo_is_fully_valid"
            )
            and classe
            == "REAL_DOCUMENTARY"
            and media_type
            in {
                "foto",
                "photo",
                "image"
            }
        ):

            score += 3.0

            reasons.append(
                "vi68_documentary_photo_ok"
            )


        # =============================================
        # DIVERSITY PRIORITY
        # =============================================

        if (
            global_plan.get(
                "diversity_priority"
            )
            == "HIGH"
            and classe
            == "SAFE_CONTEXT"
        ):

            reason_text = " ".join(
                reasons
            ).lower()


            if (
                "generic"
                in reason_text
            ):

                score -= 4.0

                reasons.append(
                    "vi68_diversity_generic_penalty"
                )


        # =============================================
        # CTA
        # =============================================

        if global_plan.get(
            "cta_reuse"
        ):

            if bool(
                item.get(
                    "reuse",
                    False
                )
            ):

                score += 12.0

                reasons.append(
                    "vi68_cta_reuse"
                )


        result[
            "score"
        ] = round(
            score,
            3
        )


        result[
            "reasons"
        ] = reasons


        result[
            "vi68_global"
        ] = True


        return result


    brain.evaluate = (
        evaluate_6_8
    )


    brain._VI68_RUNTIME_PATCHED = (
        True
    )

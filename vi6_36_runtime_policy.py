#!/usr/bin/env python3

import vi6_6_active_brain as brain


from vi6_34_motion_auto_repair import (
    repair_contract
)


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan,
    validate_plan
)


from vi6_36_renderer_compatibility import (
    check,
    record,
    flush,
    reset,
)


from vi6_33_cinematic_safety_gate import (
    assess
)


if not getattr(
    brain,
    "_VI636_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_636 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_636(
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
        ) = _base_supervisor_636(
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
                "vi630_renderer_contract"
            )
            or {}
        )


        duration = (
            meta.get(
                "vi632_duration"
            )
            or {
                "seconds":
                    4.0,

                "confidence":
                    "LOW",

                "source":
                    "runtime_fallback",
            }
        )


        safety = (
            meta.get(
                "vi633_cinematic_safety"
            )
            or {}
        )


        # =========================================
        # VI6.34 AUTO-REPAIR
        # =========================================

        repair = repair_contract(
            contract,
            duration,
            safety
        )


        final_contract = repair[
            "contract"
        ]


        # Revalida DEPOIS do repair.
        repaired_safety = assess(
            final_contract,
            duration
        )


        final_contract[
            "vi634_repair_status"
        ] = repair[
            "reason"
        ]


        final_contract[
            "vi633_post_repair"
        ] = repaired_safety[
            "status"
        ]


        final_contract[
            "renderer_applied"
        ] = False


        # =========================================
        # VI6.35 DRY FFMPEG COMPILER
        # =========================================

        dry_plan = compile_plan(
            final_contract,
            duration
        )


        plan_ok, plan_errors = (
            validate_plan(
                dry_plan
            )
        )


        dry_plan[
            "valid"
        ] = plan_ok


        dry_plan[
            "errors"
        ] = plan_errors


        # =========================================
        # VI6.36 COMPATIBILITY
        # =========================================

        compat = check(
            final_contract,
            repaired_safety,
            dry_plan
        )


        if not plan_ok:

            compat[
                "status"
            ] = "HOLD"


            compat[
                "renderer_activation_ready"
            ] = False


            compat[
                "issues"
            ] = list(
                compat.get(
                    "issues"
                )
                or []
            ) + [
                "dry_compiler_validation_failed"
            ]


        record(
            number,
            compat,
            repair,
            dry_plan
        )


        meta[
            "vi634_motion_repair"
        ] = {

            "changed":
                repair[
                    "changed"
                ],

            "reason":
                repair[
                    "reason"
                ],

            "repaired_blockers":
                repair[
                    "repaired_blockers"
                ],

            "unrepaired_blockers":
                repair[
                    "unrepaired_blockers"
                ],
        }


        meta[
            "vi634_repaired_contract"
        ] = final_contract


        meta[
            "vi633_post_repair_safety"
        ] = repaired_safety


        meta[
            "vi635_ffmpeg_dry_plan"
        ] = dry_plan


        meta[
            "vi636_renderer_compatibility"
        ] = compat


        meta[
            "vi636_renderer_activation_ready"
        ] = compat[
            "renderer_activation_ready"
        ]


        # Nada desta camada altera mídia,
        # áudio, legenda ou renderer.
        if candidate is not None:

            candidate[
                "_vi634_motion_repaired"
            ] = repair[
                "changed"
            ]


            candidate[
                "_vi635_dry_compiled"
            ] = bool(
                dry_plan.get(
                    "renderer_mode"
                )
            )


            candidate[
                "_vi636_static_compat"
            ] = compat[
                "status"
            ]


            candidate[
                "_vi636_renderer_applied"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi636_compat_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi636_compat_error"
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
        _wrapped_636
    )


    brain._VI634_RUNTIME_ACTIVE = True
    brain._VI635_RUNTIME_ACTIVE = True
    brain._VI636_RUNTIME_ACTIVE = True

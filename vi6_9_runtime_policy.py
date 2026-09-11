#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_9_quality_firewall import (
    check
)

from vi6_11_second_chance import (
    rescue
)

from vi6_12_story_guard import (
    review,
    story_summary
)

from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_14_pre_download_gate import (
    final_gate
)

from vi6_15_decision_ledger import (
    record,
    flush
)

from vi6_19_true_recovery import (
    true_recovery
)


if not getattr(
    brain,
    "_VI69_RUNTIME_PATCHED",
    False
):

    _base = (
        brain.supervisionar_vi6_6
    )


    def _wrapped(
        vi6_scene,
        candidatos,
        cena,
        current_candidate,
        current_reason
    ):

        (
            candidate,
            reason,
            meta
        ) = _base(
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


        rejection_reason = None
        recovery_attempted = False


        def try_true_recovery(
            why
        ):

            nonlocal recovery_attempted


            if recovery_attempted:

                return (
                    None,
                    "vi619_already_attempted",
                    {}
                )


            recovery_attempted = True


            return true_recovery(
                cena,
                vi6_scene,
                why,
                brain.evaluate,
                check,
                final_gate,
                dry_run=False
            )


        # =========================================
        # VI6.9 FIREWALL
        # =========================================

        if candidate is not None:

            fw = check(
                candidate,
                cena,
                meta
            )


            meta[
                "vi69_action"
            ] = fw.get(
                "action"
            )


            meta[
                "vi69_reason"
            ] = fw.get(
                "reason"
            )


            meta[
                "vi610_contract"
            ] = fw.get(
                "contract"
            )


            if (
                fw.get(
                    "action"
                )
                == "FALLBACK"
            ):

                rejection_reason = (
                    fw.get(
                        "reason",
                        "vi69_firewall"
                    )
                )

                candidate = None


        else:

            rejection_reason = (
                reason
                or current_reason
                or "vi66_no_candidate"
            )


        # =========================================
        # VI6.11 EXISTING-CANDIDATE RESCUE
        # =========================================

        if candidate is None:

            (
                rescued,
                rescue_reason,
                rescue_meta
            ) = rescue(
                vi6_scene,
                candidatos,
                cena,
                rejection_reason,
                brain.evaluate,
                check
            )


            meta[
                "vi611_decision"
            ] = rescue_meta.get(
                "decision"
            )


            meta[
                "vi611_reason"
            ] = rescue_reason


            if rescued is not None:

                candidate = rescued
                reason = rescue_reason
                meta.update(
                    rescue_meta
                )


            else:

                # =================================
                # VI6.19 TRUE SECOND RETRIEVAL
                # =================================

                (
                    recovered,
                    recovery_reason,
                    recovery_meta
                ) = try_true_recovery(
                    rejection_reason
                    or rescue_reason
                )


                if recovered is not None:

                    candidate = recovered
                    reason = recovery_reason

                    meta.update(
                        recovery_meta
                    )


                else:

                    plan = build_recovery_plan(
                        cena,
                        vi6_scene,
                        rejection_reason
                        or rescue_reason
                    )


                    meta[
                        "vi613_recovery_plan"
                    ] = plan


                    meta[
                        "vi619_reason"
                    ] = recovery_reason


                    meta[
                        "decision"
                    ] = "5X_AFTER_619"


                    record(
                        cena,
                        None,
                        recovery_reason
                        or rejection_reason
                        or rescue_reason,
                        meta,
                        plan,
                        "FALLBACK"
                    )


                    return (
                        None,
                        recovery_reason
                        or rejection_reason
                        or rescue_reason,
                        meta
                    )


        # =========================================
        # VI6.12 GLOBAL STORY GUARD
        # =========================================

        (
            candidate,
            story_reason,
            story_meta
        ) = review(
            candidate,
            cena,
            meta,
            vi6_scene,
            candidatos,
            brain.evaluate,
            check
        )


        meta = dict(
            story_meta
            or meta
        )


        meta[
            "vi612_reason"
        ] = story_reason


        if candidate is None:

            (
                recovered,
                recovery_reason,
                recovery_meta
            ) = try_true_recovery(
                story_reason
            )


            if recovered is not None:

                (
                    candidate,
                    story_reason,
                    story_meta
                ) = review(
                    recovered,
                    cena,
                    recovery_meta,
                    vi6_scene,
                    candidatos,
                    brain.evaluate,
                    check
                )


                meta = dict(
                    story_meta
                    or recovery_meta
                )


            if candidate is None:

                plan = build_recovery_plan(
                    cena,
                    vi6_scene,
                    story_reason
                    or recovery_reason
                )


                meta[
                    "vi613_recovery_plan"
                ] = plan


                meta[
                    "decision"
                ] = "5X_AFTER_612_619"


                record(
                    cena,
                    None,
                    story_reason
                    or recovery_reason,
                    meta,
                    plan,
                    "FALLBACK"
                )


                return (
                    None,
                    story_reason
                    or recovery_reason,
                    meta
                )


        # =========================================
        # VI6.14 FINAL GATE
        # =========================================

        gate = final_gate(
            candidate,
            cena,
            meta
        )


        meta[
            "vi614_action"
        ] = gate.get(
            "action"
        )


        meta[
            "vi614_reason"
        ] = gate.get(
            "reason"
        )


        if (
            gate.get(
                "action"
            )
            != "ACCEPT"
        ):

            (
                recovered,
                recovery_reason,
                recovery_meta
            ) = try_true_recovery(
                gate.get(
                    "reason"
                )
            )


            if recovered is not None:

                (
                    recovered,
                    story_reason,
                    story_meta
                ) = review(
                    recovered,
                    cena,
                    recovery_meta,
                    vi6_scene,
                    candidatos,
                    brain.evaluate,
                    check
                )


                if recovered is not None:

                    gate2 = final_gate(
                        recovered,
                        cena,
                        story_meta
                    )


                    if (
                        gate2.get(
                            "action"
                        )
                        == "ACCEPT"
                    ):

                        candidate = recovered

                        meta = dict(
                            story_meta
                            or recovery_meta
                        )

                        meta[
                            "vi614_action"
                        ] = "ACCEPT"

                        meta[
                            "vi614_reason"
                        ] = gate2.get(
                            "reason"
                        )

                        gate = gate2


            if (
                gate.get(
                    "action"
                )
                != "ACCEPT"
            ):

                plan = build_recovery_plan(
                    cena,
                    vi6_scene,
                    gate.get(
                        "reason"
                    )
                )


                meta[
                    "vi613_recovery_plan"
                ] = plan


                meta[
                    "decision"
                ] = "5X_AFTER_614_619"


                record(
                    cena,
                    None,
                    gate.get(
                        "reason"
                    ),
                    meta,
                    plan,
                    "FALLBACK"
                )


                return (
                    None,
                    gate.get(
                        "reason"
                    ),
                    meta
                )


        # =========================================
        # ACCEPT
        # =========================================

        reason = (
            gate.get(
                "reason"
            )
            or story_reason
            or reason
        )


        record(
            cena,
            candidate,
            reason,
            meta,
            None,
            "ACCEPT"
        )


        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        if (
            board.get(
                "cta_reuse"
            )
            or int(
                board.get(
                    "scene",
                    0
                )
                or 0
            ) >= 12
        ):

            meta[
                "vi612_story_summary"
            ] = story_summary()


            try:

                meta[
                    "vi615_ledger_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi615_ledger_error"
                ] = (
                    f"{type(exc).__name__}:"
                    f"{str(exc)[:100]}"
                )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped
    )


    brain._VI69_RUNTIME_PATCHED = True
    brain._VI611_RUNTIME_ACTIVE = True
    brain._VI612_RUNTIME_ACTIVE = True
    brain._VI613_RUNTIME_ACTIVE = True
    brain._VI614_RUNTIME_ACTIVE = True
    brain._VI615_RUNTIME_ACTIVE = True
    brain._VI619_RUNTIME_ACTIVE = True
    brain._VI620_RUNTIME_ACTIVE = True
    brain._VI621_RUNTIME_ACTIVE = True


# =========================================
# VI6.22-6.24 RUNTIME STACK
# =========================================
import vi6_23_runtime_policy
import vi6_24_runtime_telemetry


# =========================================
# VI6.25-6.27 CINEMATIC RUNTIME STACK
# =========================================
import vi6_26_runtime_policy
import vi6_27_runtime_policy


# =========================================
# VI6.28-6.30 MOTION CONTRACT STACK
# =========================================
import vi6_30_runtime_policy


# =========================================
# VI6.31-6.33 PRE-RENDER SAFETY STACK
# =========================================
import vi6_33_runtime_policy


# =========================================
# VI6.34-6.36 RENDER PREPARATION STACK
# =========================================
import vi6_36_runtime_policy


# =========================================
# VI6.37-6.39 SHADOW RENDERER STACK
# =========================================
import vi6_39_runtime_policy


# =========================================
# VI6.40-6.42 CONTROLLED BRIDGE STACK
# =========================================
import vi6_42_runtime_policy


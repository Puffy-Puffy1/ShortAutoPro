#!/usr/bin/env python3

import vi6_6_active_brain as brain


from vi6_30_renderer_contract import (
    build_contract,
    validate_contract,
)


from vi6_32_scene_duration import (
    duration_info
)


from vi6_33_cinematic_safety_gate import (
    assess
)


from vi6_31_pre_render_auditor import (
    record,
    audit,
    flush,
    reset,
)


if not getattr(
    brain,
    "_VI633_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_633 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_633(
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
        ) = _base_supervisor_633(
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
        )


        # Fail-safe:
        # se por algum motivo o wrapper 6.30
        # não anexou contrato, recriamos apenas
        # metadata. Continua sem FFmpeg.
        if not isinstance(
            contract,
            dict
        ):

            contract = (
                build_contract(
                    cena,
                    candidate,
                    meta
                )
            )


            ok_contract, errors = (
                validate_contract(
                    contract
                )
            )


            contract[
                "contract_valid"
            ] = ok_contract


            if not ok_contract:

                contract[
                    "contract_errors"
                ] = errors


        duration = duration_info(
            cena
        )


        safety = assess(
            contract,
            duration
        )


        if (
            safety[
                "status"
            ]
            == "HOLD"
        ):

            contract[
                "status"
            ] = "HOLD"


        contract[
            "vi633_safety_status"
        ] = safety[
            "status"
        ]


        contract[
            "vi632_duration"
        ] = duration


        contract[
            "renderer_applied"
        ] = False


        meta[
            "vi631_pre_render"
        ] = True


        meta[
            "vi632_duration"
        ] = duration


        meta[
            "vi633_cinematic_safety"
        ] = safety


        meta[
            "vi633_renderer_allowed"
        ] = safety[
            "renderer_allowed"
        ]


        # Não veta mídia nesta fase.
        # Apenas marca o contrato.
        if candidate is not None:

            candidate[
                "_vi632_duration"
            ] = duration


            candidate[
                "_vi633_cinematic_status"
            ] = safety[
                "status"
            ]


            candidate[
                "_vi633_renderer_allowed"
            ] = safety[
                "renderer_allowed"
            ]


        record(
            contract,
            duration,
            safety
        )


        global_audit = audit()


        meta[
            "vi631_global_audit"
        ] = {

            "stage":
                global_audit[
                    "stage"
                ],

            "decision":
                global_audit[
                    "decision"
                ],

            "scenes":
                global_audit[
                    "scenes"
                ],

            "hold_scenes":
                global_audit[
                    "hold_scenes"
                ],

            "warning_scenes":
                global_audit[
                    "warning_scenes"
                ],

            "total_duration":
                global_audit[
                    "total_duration"
                ],

            "max_aggressive_streak":
                global_audit[
                    "max_aggressive_streak"
                ],
        }


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi631_audit_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi631_audit_error"
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
        _wrapped_633
    )


    brain._VI631_RUNTIME_ACTIVE = True

    brain._VI632_RUNTIME_ACTIVE = True

    brain._VI633_RUNTIME_ACTIVE = True

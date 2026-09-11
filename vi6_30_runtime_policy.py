#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_30_renderer_contract import (
    build_contract,
    validate_contract,
    record_contract,
    flush,
    reset,
)


if not getattr(
    brain,
    "_VI630_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_630 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_630(
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
        ) = _base_supervisor_630(
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
            build_contract(
                cena,
                candidate,
                meta
            )
        )


        ok, errors = (
            validate_contract(
                contract
            )
        )


        if ok:

            contract[
                "contract_valid"
            ] = True


        else:

            contract[
                "contract_valid"
            ] = False

            contract[
                "contract_errors"
            ] = errors

            contract[
                "status"
            ] = "HOLD"


        record_contract(
            contract
        )


        meta[
            "vi628_motion_profile"
        ] = contract.get(
            "profile"
        )


        meta[
            "vi629_ken_burns"
        ] = contract.get(
            "ken_burns"
        )


        meta[
            "vi630_renderer_contract"
        ] = contract


        meta[
            "vi630_contract_valid"
        ] = ok


        # Apenas metadata.
        # NÃO altera seleção.
        # NÃO altera arquivo.
        # NÃO altera renderer.
        if candidate is not None:

            candidate[
                "_vi628_motion_profile"
            ] = contract.get(
                "profile"
            )


            candidate[
                "_vi629_ken_burns"
            ] = contract.get(
                "ken_burns"
            )


            candidate[
                "_vi630_contract_hash"
            ] = contract.get(
                "contract_hash"
            )


            candidate[
                "_vi630_renderer_applied"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi630_contract_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi630_contract_error"
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
        _wrapped_630
    )


    brain._VI628_RUNTIME_ACTIVE = True

    brain._VI629_RUNTIME_ACTIVE = True

    brain._VI630_RUNTIME_ACTIVE = True

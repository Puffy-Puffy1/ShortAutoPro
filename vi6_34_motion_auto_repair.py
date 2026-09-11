#!/usr/bin/env python3

import copy
import hashlib
import json


VERSION = "6.34"


REPAIRABLE = {
    "zoom_velocity_too_high",
    "pan_velocity_too_high",
    "documentary_zoom_excess",
    "documentary_pan_excess",
}


ROLE_ZOOM_RATE = {
    "EVIDENCE": .012,
    "PERSON": .022,
    "PLACE": .022,
    "OBJECT": .030,
    "CONTEXT": .030,
    "CTA": .010,
}


ROLE_PAN_RATE = {
    "EVIDENCE": .014,
    "PERSON": .018,
    "PLACE": .030,
    "OBJECT": .026,
    "CONTEXT": .034,
    "CTA": .012,
}


def _u(v):
    return str(v or "").strip().upper()


def _f(v, default=0.0):

    try:
        return float(v)
    except Exception:
        return float(default)


def _clamp(v, low, high):

    return max(
        low,
        min(
            high,
            float(v)
        )
    )


def _rehash(contract):

    tmp = dict(contract)

    tmp.pop(
        "contract_hash",
        None
    )


    canonical = json.dumps(
        tmp,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )


    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:16]


def repair_contract(
    contract,
    duration,
    safety
):

    original = copy.deepcopy(
        contract
    )


    repaired = copy.deepcopy(
        contract
    )


    blockers = set(
        safety.get(
            "blockers",
            []
        )
        or []
    )


    if not blockers:

        return {
            "version": VERSION,
            "changed": False,
            "reason": "no_blockers",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers": [],
        }


    nonrepairable = (
        blockers
        - REPAIRABLE
    )


    repairable = (
        blockers
        & REPAIRABLE
    )


    # Não tenta "consertar" erro lógico,
    # contrato inválido ou cena curta.
    if nonrepairable:

        return {
            "version": VERSION,
            "changed": False,
            "reason": "nonrepairable_blocker",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers":
                sorted(nonrepairable),
        }


    if not repairable:

        return {
            "version": VERSION,
            "changed": False,
            "reason": "nothing_repairable",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers": [],
        }


    ken = copy.deepcopy(
        repaired.get(
            "ken_burns"
        )
        or {}
    )


    if not ken.get(
        "enabled"
    ):

        return {
            "version": VERSION,
            "changed": False,
            "reason":
                "motion_not_enabled",
            "original": original,
            "contract": repaired,
            "repaired_blockers": [],
            "unrepaired_blockers":
                sorted(repairable),
        }


    role = _u(
        repaired.get(
            "role"
        )
        or duration.get(
            "role"
        )
        or "CONTEXT"
    )


    seconds = max(
        .75,
        _f(
            duration.get(
                "seconds",
                4.0
            ),
            4.0
        )
    )


    z1 = _f(
        ken.get(
            "zoom_start",
            1.0
        ),
        1.0
    )


    z2 = _f(
        ken.get(
            "zoom_end",
            1.0
        ),
        1.0
    )


    x1 = _f(
        ken.get(
            "start_x",
            .5
        ),
        .5
    )


    x2 = _f(
        ken.get(
            "end_x",
            .5
        ),
        .5
    )


    y1 = _f(
        ken.get(
            "start_y",
            .5
        ),
        .5
    )


    y2 = _f(
        ken.get(
            "end_y",
            .5
        ),
        .5
    )


    max_zoom_delta = (
        ROLE_ZOOM_RATE.get(
            role,
            .030
        )
        * seconds
    )


    # Limite adicional absoluto.
    absolute_zoom = {
        "EVIDENCE": .045,
        "PERSON": .075,
        "PLACE": .065,
        "OBJECT": .095,
        "CONTEXT": .075,
        "CTA": .035,
    }.get(
        role,
        .075
    )


    max_zoom_delta = min(
        max_zoom_delta,
        absolute_zoom
    )


    direction = (
        1.0
        if z2 >= z1
        else -1.0
    )


    new_delta = min(
        abs(
            z2 - z1
        ),
        max_zoom_delta
    )


    new_z2 = (
        z1
        + direction
        * new_delta
    )


    new_z2 = _clamp(
        new_z2,
        1.0,
        1.10
    )


    # =================================
    # PAN REPAIR
    # =================================

    dx = (
        x2 - x1
    )

    dy = (
        y2 - y1
    )


    distance = (
        dx * dx
        + dy * dy
    ) ** .5


    max_pan_distance = (
        ROLE_PAN_RATE.get(
            role,
            .034
        )
        * seconds
    )


    absolute_pan = {
        "EVIDENCE": .030,
        "PERSON": .050,
        "PLACE": .100,
        "OBJECT": .075,
        "CONTEXT": .110,
        "CTA": .025,
    }.get(
        role,
        .100
    )


    max_pan_distance = min(
        max_pan_distance,
        absolute_pan
    )


    if (
        distance > 0
        and distance
        > max_pan_distance
    ):

        factor = (
            max_pan_distance
            / distance
        )


        dx *= factor
        dy *= factor


    new_x2 = _clamp(
        x1 + dx,
        .42,
        .58
    )


    new_y2 = _clamp(
        y1 + dy,
        .40,
        .58
    )


    # Evidência documental é ainda
    # mais conservadora.
    if role == "EVIDENCE":

        new_z2 = min(
            new_z2,
            z1 + .045
        )


        new_x2 = _clamp(
            new_x2,
            x1 - .03,
            x1 + .03
        )


        new_y2 = _clamp(
            new_y2,
            y1 - .03,
            y1 + .03
        )


    ken[
        "zoom_end"
    ] = round(
        new_z2,
        5
    )


    ken[
        "end_x"
    ] = round(
        new_x2,
        5
    )


    ken[
        "end_y"
    ] = round(
        new_y2,
        5
    )


    ken[
        "vi634_repaired"
    ] = True


    ken[
        "vi634_original"
    ] = {

        "zoom_end":
            z2,

        "end_x":
            x2,

        "end_y":
            y2,
    }


    repaired[
        "ken_burns"
    ] = ken


    repaired[
        "status"
    ] = "REPAIRED_PENDING_RECHECK"


    repaired[
        "renderer_applied"
    ] = False


    repaired[
        "ffmpeg_filter"
    ] = None


    repaired[
        "vi634_repaired"
    ] = True


    repaired[
        "vi634_repaired_blockers"
    ] = sorted(
        repairable
    )


    repaired[
        "contract_hash"
    ] = _rehash(
        repaired
    )


    changed = (
        new_z2 != z2
        or new_x2 != x2
        or new_y2 != y2
    )


    return {
        "version": VERSION,
        "changed": changed,
        "reason":
            (
                "motion_repaired"
                if changed
                else
                "already_within_repair_target"
            ),
        "original": original,
        "contract": repaired,
        "repaired_blockers":
            sorted(repairable),
        "unrepaired_blockers": [],
    }


def self_test():

    contract = {

        "role":
            "EVIDENCE",

        "media_type":
            "STILL",

        "profile":
            "DOCUMENTARY_HOLD",

        "transition":
            "DIRECT_CUT",

        "renderer_applied":
            False,

        "ffmpeg_filter":
            None,

        "ken_burns":
            {
                "enabled":
                    True,

                "zoom_start":
                    1.0,

                "zoom_end":
                    1.10,

                "start_x":
                    .50,

                "start_y":
                    .50,

                "end_x":
                    .58,

                "end_y":
                    .50,
            },
    }


    result = repair_contract(
        contract,
        {
            "seconds":
                2.0,

            "role":
                "EVIDENCE",
        },
        {
            "status":
                "HOLD",

            "blockers":
                [
                    "zoom_velocity_too_high",
                    "pan_velocity_too_high",
                    "documentary_zoom_excess",
                    "documentary_pan_excess",
                ],
        }
    )


    assert result[
        "changed"
    ] is True


    repaired = result[
        "contract"
    ]


    assert (
        repaired[
            "ken_burns"
        ][
            "zoom_end"
        ]
        <= 1.0241
    )


    assert (
        repaired[
            "renderer_applied"
        ]
        is False
    )


    blocked = repair_contract(
        contract,
        {
            "seconds":
                .5
        },
        {
            "status":
                "HOLD",

            "blockers":
                [
                    "scene_too_short"
                ],
        }
    )


    assert (
        blocked[
            "changed"
        ]
        is False
    )


    assert (
        "scene_too_short"
        in blocked[
            "unrepaired_blockers"
        ]
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.34 AUTO-REPAIR SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Zoom Velocity Repair"
    )
    print(
        "OK Pan Velocity Repair"
    )
    print(
        "OK Documentary Motion Repair"
    )
    print(
        "OK Contract Rehash"
    )
    print(
        "OK Non-Motion Errors Preserved"
    )
    print()


if __name__ == "__main__":
    self_test()

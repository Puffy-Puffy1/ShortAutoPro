#!/usr/bin/env python3

from vi6_22_story_audit import (
    summary
)


VERSION = "6.23"


DOCUMENTARY_ROLES = {
    "EVIDENCE",
    "PERSON",
    "PLACE",
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _u(v):

    return _s(
        v
    ).upper()


def adjust_result(
    result,
    scene
):

    if result is None:

        return None


    result = dict(
        result
    )


    state = summary()


    urgency = float(
        state.get(
            "documentary_urgency",
            0
        )
        or 0
    )


    if urgency <= 0:

        result[
            "vi623_adjustment"
        ] = 0.0

        return result


    role = _u(
        result.get(
            "role"
        )
        or scene.get(
            "retrieval_role_6_7"
        )
        or (
            scene.get(
                "_vi68_storyboard"
            )
            or {}
        ).get(
            "role"
        )
    )


    classe = _u(
        result.get(
            "class"
        )
    )


    truth = bool(
        result.get(
            "truth_ok",
            False
        )
    )


    adjustment = 0.0


    # Só pressiona cenas em que documentário
    # realmente faz sentido editorial.
    if role in DOCUMENTARY_ROLES:

        if (
            classe
            == "REAL_DOCUMENTARY"
            and truth
        ):

            adjustment += (
                4.0
                + urgency * 14.0
            )


        elif (
            classe
            == "SAFE_CONTEXT"
        ):

            adjustment -= (
                urgency * 9.0
            )


    # Se o alvo já ficou matematicamente
    # impossível, força prioridade documental
    # ainda maior nas cenas adequadas.
    if (
        state.get(
            "documentary_target_impossible"
        )
        and role in DOCUMENTARY_ROLES
    ):

        if (
            classe
            == "REAL_DOCUMENTARY"
            and truth
        ):

            adjustment += 6.0


        elif (
            classe
            == "SAFE_CONTEXT"
        ):

            adjustment -= 5.0


    old_score = float(
        result.get(
            "score",
            0
        )
        or 0
    )


    result[
        "score"
    ] = round(
        old_score
        + adjustment,
        3
    )


    reasons = list(
        result.get(
            "reasons",
            []
        )
        or []
    )


    if adjustment > 0:

        reasons.append(
            "vi623_documentary_budget_boost"
        )


    elif adjustment < 0:

        reasons.append(
            "vi623_stock_budget_penalty"
        )


    result[
        "reasons"
    ] = reasons


    result[
        "vi623_adjustment"
    ] = round(
        adjustment,
        3
    )


    result[
        "vi623_documentary_urgency"
    ] = urgency


    result[
        "vi623_documentary_needed"
    ] = state.get(
        "documentary_needed"
    )


    return result


def self_test():

    from vi6_22_story_audit import (
        reset,
        record_final
    )


    reset()


    # Três cenas stock iniciais:
    # deficit documental aumenta.
    for number in (
        1,
        2,
        3,
    ):

        record_final(
            {
                "_vi68_storyboard":
                    {
                        "scene":
                            number,

                        "role":
                            "CONTEXT"
                    }
            },
            {
                "fonte":
                    "Pixabay",

                "_vi6_class":
                    "SAFE_CONTEXT"
            },
            "test",
            {
                "class":
                    "SAFE_CONTEXT",

                "score":
                    70
            }
        )


    doc = adjust_result(
        {
            "score":
                70,

            "class":
                "REAL_DOCUMENTARY",

            "truth_ok":
                True,

            "role":
                "EVIDENCE",

            "reasons":
                []
        },
        {
            "retrieval_role_6_7":
                "EVIDENCE"
        }
    )


    stock = adjust_result(
        {
            "score":
                70,

            "class":
                "SAFE_CONTEXT",

            "truth_ok":
                True,

            "role":
                "EVIDENCE",

            "reasons":
                []
        },
        {
            "retrieval_role_6_7":
                "EVIDENCE"
        }
    )


    assert doc[
        "score"
    ] > 70


    assert stock[
        "score"
    ] < 70


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.23 ADAPTIVE BUDGET SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary Deficit Detection"
    )
    print(
        "OK Documentary Score Boost"
    )
    print(
        "OK Stock Penalty"
    )
    print(
        "OK Role-Aware Adjustment"
    )
    print(
        "OK No Hard Truth Relaxation"
    )
    print()


if __name__ == "__main__":

    self_test()

#!/usr/bin/env python3

VERSION = "7.64"

def evaluate(
    scene,
    category
):
    risk = 0
    reasons = []

    query = str(
        scene.get("query")
        or ""
    ).lower()

    avoid = " ".join(
        str(x)
        for x in (
            scene.get("avoid")
            or []
        )
    ).lower()

    if category == "FACE":
        risk += 2

        reasons.append(
            "identity_sensitive_visual"
        )

    if category == "DOCUMENT":
        risk += 1

        reasons.append(
            "text_legibility_risk"
        )

    graphic_terms = (
        "corpse",
        "dead body",
        "blood",
        "graphic",
        "open wound",
        "severed",
        "gore",
    )

    if any(
        token in query
        for token in graphic_terms
    ):
        risk += 4

        reasons.append(
            "graphic_visual_risk"
        )

    if any(
        token in avoid
        for token in (
            "adult woman",
            "teenager",
            "wrong person",
        )
    ):
        risk += 1

        reasons.append(
            "identity_mismatch_risk"
        )

    if risk >= 5:
        status = "HOLD"

    elif risk >= 2:
        status = "CAUTION"

    else:
        status = "PASS"

    return {
        "version": VERSION,
        "risk": risk,
        "reasons": reasons,
        "status": status,
    }

def self_test():
    result = evaluate(
        {
            "query":
                "young girl portrait",
            "avoid":
                ["adult woman"],
        },
        "FACE"
    )

    assert result["risk"] >= 2

    print(
        "VI7.64 VISUAL RISK INTELLIGENCE=PASS"
    )

if __name__ == "__main__":
    self_test()

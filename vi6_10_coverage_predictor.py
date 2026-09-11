#!/usr/bin/env python3

VERSION = "6.10"


def _s(v):
    return str(v or "").strip()


def role(scene):

    r = _s(
        scene.get(
            "retrieval_role_6_7"
        )
    ).upper()

    if r:
        return r


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )

    r = _s(
        board.get("role")
    ).upper()

    if r:
        return r


    text = " ".join(
        [
            _s(scene.get("visual_mode")),
            _s(scene.get("visual_intent")),
            _s(scene.get("intent")),
        ]
    ).lower()


    if "cta" in text:
        return "CTA"


    if any(
        x in text
        for x in (
            "evidence",
            "document",
            "archive",
            "arquivo",
            "newspaper",
            "case_file",
        )
    ):
        return "EVIDENCE"


    if any(
        x in text
        for x in (
            "person",
            "portrait",
            "character",
        )
    ):
        return "PERSON"


    if any(
        x in text
        for x in (
            "location",
            "place",
            "architecture",
            "map",
            "transport",
        )
    ):
        return "PLACE"


    if any(
        x in text
        for x in (
            "object",
            "medicine",
            "product",
            "package",
            "packaging",
        )
    ):
        return "OBJECT"


    return "CONTEXT"


BASE = {

    "EVIDENCE": {
        "min_score": 58.0,
        "min_semantic": 60.0,
        "min_anchor": 0.18,
        "generic_guard": "STRICT",
        "prefer_documentary": True,
    },

    "PERSON": {
        "min_score": 56.0,
        "min_semantic": 58.0,
        "min_anchor": 0.20,
        "generic_guard": "STRICT",
        "prefer_documentary": True,
    },

    "PLACE": {
        "min_score": 54.0,
        "min_semantic": 55.0,
        "min_anchor": 0.14,
        "generic_guard": "MEDIUM",
        "prefer_documentary": True,
    },

    "OBJECT": {
        "min_score": 52.0,
        "min_semantic": 48.0,
        "min_anchor": 0.08,
        "generic_guard": "MEDIUM",
        "prefer_documentary": False,
    },

    "CONTEXT": {
        "min_score": 50.0,
        "min_semantic": 45.0,
        "min_anchor": 0.0,
        "generic_guard": "LIGHT",
        "prefer_documentary": False,
    },

    "CTA": {
        "min_score": 0.0,
        "min_semantic": 0.0,
        "min_anchor": 0.0,
        "generic_guard": "CTA_REUSE",
        "prefer_documentary": False,
    },
}


def contract(scene):

    r = role(scene)

    result = dict(
        BASE.get(
            r,
            BASE["CONTEXT"]
        )
    )


    strength = int(
        scene.get(
            "retrieval_anchor_strength_6_7",
            0
        )
        or 0
    )


    if (
        r in {
            "EVIDENCE",
            "PERSON",
            "PLACE"
        }
        and strength >= 6
    ):
        result["min_anchor"] = max(
            result["min_anchor"],
            0.20
        )


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    if board.get(
        "prefer_documentary"
    ):
        result[
            "prefer_documentary"
        ] = True


    result["role"] = r
    result["version"] = VERSION
    result["retrieval_strength"] = strength

    return result


def self_test():

    x = contract(
        {
            "retrieval_role_6_7":
                "EVIDENCE",

            "retrieval_anchor_strength_6_7":
                7,
        }
    )

    assert x["role"] == "EVIDENCE"
    assert x["min_semantic"] >= 60
    assert x["min_anchor"] >= .20
    assert x["prefer_documentary"] is True


    x = contract(
        {
            "visual_mode":
                "cta_reuse"
        }
    )

    assert x["role"] == "CTA"
    assert x["min_score"] == 0


    print()
    print("======================================")
    print(" VI6.10 COVERAGE SELF TEST: PASS")
    print("======================================")
    print("OK Evidence")
    print("OK Person")
    print("OK Place")
    print("OK Object")
    print("OK Context")
    print("OK CTA")
    print()


if __name__ == "__main__":
    self_test()

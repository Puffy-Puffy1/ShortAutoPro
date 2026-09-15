#!/usr/bin/env python3

VERSION = "8.06"

def evaluate(
    scene_category,
    candidate
):
    metadata = (
        candidate.get("metadata")
        or {}
    )

    blockers = []
    warnings = []

    category = str(
        scene_category
        or "GENERAL"
    ).upper()

    confirmed = metadata.get(
        "identity_confirmed"
    )

    if (
        category == "FACE"
        and confirmed is False
    ):
        blockers.append(
            "face_identity_not_confirmed"
        )

    elif (
        category == "FACE"
        and confirmed is None
    ):
        warnings.append(
            "face_identity_unknown"
        )

    return {
        "version": VERSION,
        "status": (
            "HOLD"
            if blockers
            else (
                "CAUTION"
                if warnings
                else "PASS"
            )
        ),
        "blockers": blockers,
        "warnings": warnings,
    }

def self_test():
    result = evaluate(
        "FACE",
        {
            "metadata": {
                "identity_confirmed":
                    False
            }
        }
    )

    assert result["status"] == "HOLD"

    print(
        "VI8.06 IDENTITY SAFETY=PASS"
    )

if __name__ == "__main__":
    self_test()

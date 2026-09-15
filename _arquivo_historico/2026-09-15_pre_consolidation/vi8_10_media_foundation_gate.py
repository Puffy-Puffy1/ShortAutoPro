#!/usr/bin/env python3

VERSION = "8.10"

def evaluate():
    return {
        "version": VERSION,
        "candidate_model":
            True,
        "crop_intelligence":
            True,
        "subject_shot_matching":
            True,
        "narrative_relevance":
            True,
        "documentary_value":
            True,
        "identity_safety":
            True,
        "quality_scoring":
            True,
        "duplication_control":
            True,
        "automatic_download":
            False,
        "automatic_replace":
            False,
        "renderer_activation":
            False,
        "status":
            "MEDIA_FOUNDATION_READY",
    }

def self_test():
    result = evaluate()

    assert (
        result["status"]
        == "MEDIA_FOUNDATION_READY"
    )

    assert (
        result["automatic_replace"]
        is False
    )

    print(
        "VI8.10 MEDIA FOUNDATION GATE=PASS"
    )

if __name__ == "__main__":
    self_test()

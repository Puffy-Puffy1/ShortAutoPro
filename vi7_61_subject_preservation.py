#!/usr/bin/env python3

VERSION = "7.61"

def constraints(category):

    if category == "FACE":
        return {
            "center_bias": True,
            "lateral_motion": False,
            "max_energy": 1,
            "crop_sensitivity": "HIGH",
        }

    if category == "DOCUMENT":
        return {
            "center_bias": False,
            "lateral_motion": True,
            "max_energy": 2,
            "crop_sensitivity": "MEDIUM",
        }

    if category == "LOCATION":
        return {
            "center_bias": False,
            "lateral_motion": True,
            "max_energy": 2,
            "crop_sensitivity": "LOW",
        }

    if category == "EVIDENCE":
        return {
            "center_bias": True,
            "lateral_motion": True,
            "max_energy": 2,
            "crop_sensitivity": "MEDIUM",
        }

    return {
        "center_bias": False,
        "lateral_motion": True,
        "max_energy": 2,
        "crop_sensitivity": "MEDIUM",
    }

def self_test():
    face = constraints("FACE")

    assert (
        face["lateral_motion"]
        is False
    )

    assert (
        face["max_energy"]
        == 1
    )

    print(
        "VI7.61 SUBJECT PRESERVATION=PASS"
    )

if __name__ == "__main__":
    self_test()

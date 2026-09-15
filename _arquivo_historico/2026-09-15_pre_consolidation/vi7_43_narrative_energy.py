#!/usr/bin/env python3

VERSION = "7.43"

def energy(scene):
    if scene == 1:
        return 3

    if scene in {2,3}:
        return 2

    if scene in {4,5,6,7,8}:
        return 1

    if scene in {9,10,11}:
        return 3

    if scene == 12:
        return 0

    return 1

def role(scene):
    if scene == 1:
        return "HOOK"

    if scene == 12:
        return "CTA"

    if scene in {9,10,11}:
        return "CLIMAX"

    return "CONTEXT"

def self_test():
    assert energy(10) == 3
    assert energy(12) == 0

    print("VI7.43 NARRATIVE ENERGY=PASS")

if __name__ == "__main__":
    self_test()

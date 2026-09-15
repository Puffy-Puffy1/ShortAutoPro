#!/usr/bin/env python3

from pathlib import Path
import shutil

import visual_pipeline_bridge_v42 as bridge


def key(candidate):

    return bridge._candidate_key(
        candidate
    )


def check(
    name,
    condition,
):

    print(
        f"{name}="
        f"{'PASS' if condition else 'FAIL'}"
    )

    if not condition:
        raise AssertionError(
            name
        )


def test_geo():

    bridge.reset_state()


    scene = {
        "busca":
            (
                "Investigação em apartamento "
                "na cidade de São Paulo Brasil"
            ),

        "must_have": [
            "apartamento",
            "São Paulo",
        ],
    }


    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "Empire State Building "
                "Manhattan New York"
            ),

        "must":
            "2/2",

        "score":
            250,

        "width":
            1920,

        "height":
            1080,
    }


    correct = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "Apartment building "
                "Sao Paulo Brazil"
            ),

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    result = bridge.finalize_pool(
        [
            wrong,
            correct,
        ],
        wrong,
        scene,
    )


    check(
        "GEO_HARD_MISMATCH_OVERRIDE",
        key(
            result[0]
        )
        ==
        key(
            correct
        ),
    )


def test_must_upgrade():

    bridge.reset_state()


    scene = {
        "busca":
            "police investigation apartment",

        "must_have": [
            "police",
            "apartment",
        ],
    }


    weak = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "generic apartment interior",

        "must":
            "1/2",

        "score":
            160,
    }


    strong = {
        "provider":
            "Pexels",

        "tipo":
            "video",

        "title":
            (
                "police investigation "
                "apartment building"
            ),

        "must":
            "2/2",

        "score":
            130,
    }


    result = bridge.finalize_pool(
        [
            weak,
            strong,
        ],
        weak,
        scene,
    )


    check(
        "MUST_1_TO_2_RESCUE",
        key(
            result[0]
        )
        ==
        key(
            strong
        ),
    )


def test_false_medicine():

    bridge.reset_state()


    scene = {
        "busca":
            (
                "forensic evidence "
                "crime investigation"
            ),

        "must_have": [
            "forensic",
            "evidence",
        ],
    }


    medicine = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "medicine pills tablets "
                "on desk"
            ),

        "must":
            "2/2",

        "score":
            300,
    }


    forensic = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "forensic laboratory "
                "crime evidence analysis"
            ),

        "must":
            "2/2",

        "score":
            120,
    }


    result = bridge.finalize_pool(
        [
            medicine,
            forensic,
        ],
        medicine,
        scene,
    )


    medicine_report = bridge.debug_score(
        medicine,
        scene,
    )


    check(
        "FALSE_MEDICINE_HARD_REJECT",
        medicine_report[
            "hard"
        ]
        is True,
    )


    check(
        "FORENSIC_MEDIA_WINS",
        key(
            result[0]
        )
        ==
        key(
            forensic
        ),
    )


def test_generic_lifestyle():

    bridge.reset_state()


    scene = {
        "busca":
            (
                "detective police "
                "crime investigation"
            )
    }


    lifestyle = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            (
                "happy woman relaxing "
                "in bedroom lifestyle"
            ),

        "must":
            "1/2",

        "score":
            190,
    }


    documentary = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            (
                "police detective "
                "crime investigation"
            ),

        "must":
            "1/2",

        "score":
            165,
    }


    a = bridge.debug_score(
        lifestyle,
        scene,
    )

    b = bridge.debug_score(
        documentary,
        scene,
    )


    check(
        "GENERIC_LIFESTYLE_PENALTY",
        b[
            "adjusted"
        ]
        >
        a[
            "adjusted"
        ],
    )


def test_provider_diversity():

    bridge.reset_state()


    history_item = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "previous unrelated asset",
    }


    for _ in range(3):

        bridge.note_success(
            history_item
        )


    scene = {
        "busca":
            "city police investigation"
    }


    pixabay = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "city police investigation",

        "must":
            "2/2",

        "score":
            150,
    }


    pexels = {
        "provider":
            "Pexels",

        "tipo":
            "foto",

        "title":
            "city police investigation",

        "must":
            "2/2",

        "score":
            150,
    }


    result = bridge.finalize_pool(
        [
            pixabay,
            pexels,
        ],
        pixabay,
        scene,
    )


    check(
        "PROVIDER_REPEAT_CONTROL",
        bridge._provider(
            result[0]
        )
        ==
        "pexels",
    )


def test_sibling_cleanup():

    root = (
        Path.home()
        / "ShortAutoPro"
        / "temp"
        / "vse42_sibling_test"
    )


    shutil.rmtree(
        root,
        ignore_errors=True,
    )


    root.mkdir(
        parents=True,
        exist_ok=True,
    )


    jpg = (
        root
        / "scene_03.jpg"
    )

    mp4 = (
        root
        / "scene_03.mp4"
    )


    jpg.write_bytes(
        b"jpg_test"
    )

    mp4.write_bytes(
        b"mp4_test"
    )


    bridge.commit_media(
        mp4
    )


    check(
        "SCENE_SIBLING_REMOVED",
        (
            mp4.exists()
            and
            not jpg.exists()
        ),
    )


    shutil.rmtree(
        root,
        ignore_errors=True,
    )


def main():

    test_geo()
    test_must_upgrade()
    test_false_medicine()
    test_generic_lifestyle()
    test_provider_diversity()
    test_sibling_cleanup()

    print()
    print(
        "VISUAL_QUALITY_REGRESSION_V42=PASS"
    )


if __name__ == "__main__":
    main()

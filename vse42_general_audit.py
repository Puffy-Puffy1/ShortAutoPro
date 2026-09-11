#!/usr/bin/env python3

from __future__ import annotations

import ast
import copy
import importlib
import inspect
import os
import py_compile
import subprocess
import symtable
import sys
import time
import traceback
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

os.chdir(ROOT)


PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0

RESULTS = []


def section(title):

    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def pass_result(name, detail=""):

    global PASS_COUNT

    PASS_COUNT += 1

    RESULTS.append(
        (
            "PASS",
            name,
            detail,
        )
    )

    print(
        f"PASS | {name}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def fail_result(name, detail=""):

    global FAIL_COUNT

    FAIL_COUNT += 1

    RESULTS.append(
        (
            "FAIL",
            name,
            detail,
        )
    )

    print(
        f"FAIL | {name}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def warn_result(name, detail=""):

    global WARN_COUNT

    WARN_COUNT += 1

    RESULTS.append(
        (
            "WARN",
            name,
            detail,
        )
    )

    print(
        f"WARN | {name}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def safe_test(name, fn):

    try:

        result = fn()

        if result is None:
            pass_result(name)
            return True

        if isinstance(
            result,
            tuple,
        ):

            ok = bool(
                result[0]
            )

            detail = (
                str(result[1])
                if len(result) >= 2
                else ""
            )

        else:

            ok = bool(
                result
            )

            detail = ""

        if ok:
            pass_result(
                name,
                detail,
            )

        else:
            fail_result(
                name,
                detail,
            )

        return ok

    except Exception as exc:

        fail_result(
            name,
            f"{type(exc).__name__}: {exc}",
        )

        traceback.print_exc()

        return False


def load_module(name):

    return importlib.import_module(
        name
    )


# ============================================================
# 1. FILE INVENTORY
# ============================================================

section(
    "1. CORE FILE INVENTORY"
)


essential = [
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "midia.py",
]


important = [
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
]


for filename in essential:

    path = ROOT / filename

    if path.is_file():

        pass_result(
            f"FILE_{filename}",
            f"bytes={path.stat().st_size}",
        )

    else:

        fail_result(
            f"FILE_{filename}",
            "essential file missing",
        )


for filename in important:

    path = ROOT / filename

    if path.is_file():

        pass_result(
            f"FILE_{filename}",
            f"bytes={path.stat().st_size}",
        )

    else:

        warn_result(
            f"FILE_{filename}",
            "file not present",
        )


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section(
    "2. PYTHON COMPILE"
)


core_python = [
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "midia.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
    "video.py",
    "v6.py",
]


for filename in core_python:

    path = ROOT / filename

    if not path.is_file():
        continue

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        pass_result(
            f"COMPILE_{filename}"
        )

    except Exception as exc:

        fail_result(
            f"COMPILE_{filename}",
            str(exc),
        )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


for path in sorted(
    ROOT.glob("*.sh")
):

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode == 0:

        pass_result(
            f"SHELL_{path.name}"
        )

    else:

        fail_result(
            f"SHELL_{path.name}",
            result.stderr.strip(),
        )


# ============================================================
# 4. LOAD ENGINE + BRIDGE
# ============================================================

section(
    "4. MODULE IMPORT / API"
)


engine = None
bridge = None


try:

    engine = load_module(
        "visual_selection_engine_v4"
    )

    pass_result(
        "ENGINE_IMPORT"
    )

except Exception as exc:

    fail_result(
        "ENGINE_IMPORT",
        f"{type(exc).__name__}: {exc}",
    )

    traceback.print_exc()


try:

    bridge = load_module(
        "visual_selection_bridge_v42"
    )

    pass_result(
        "BRIDGE_IMPORT"
    )

except Exception as exc:

    fail_result(
        "BRIDGE_IMPORT",
        f"{type(exc).__name__}: {exc}",
    )

    traceback.print_exc()


required_engine = [
    "score_candidate",
    "candidate_text",
    "tokens",
    "geo_hits",
    "concept_hits",
    "candidate_key",
    "provider",
    "media_type",
]


if engine:

    for name in required_engine:

        if callable(
            getattr(
                engine,
                name,
                None,
            )
        ):

            pass_result(
                f"ENGINE_API_{name}"
            )

        else:

            fail_result(
                f"ENGINE_API_{name}",
                "missing/not callable",
            )


required_bridge = [
    "rank_pool",
    "reset_state",
    "get_state",
    "commit_candidate",
]


if bridge:

    for name in required_bridge:

        if callable(
            getattr(
                bridge,
                name,
                None,
            )
        ):

            pass_result(
                f"BRIDGE_API_{name}"
            )

        else:

            fail_result(
                f"BRIDGE_API_{name}",
                "missing/not callable",
            )


# ============================================================
# 5. SIGNATURE REPORT
# ============================================================

section(
    "5. API SIGNATURES"
)


if bridge:

    for name in required_bridge:

        fn = getattr(
            bridge,
            name,
            None,
        )

        if callable(fn):

            try:

                print(
                    f"SIGNATURE {name}"
                    f"{inspect.signature(fn)}"
                )

            except Exception:

                pass


if engine:

    fn = getattr(
        engine,
        "score_candidate",
        None,
    )

    if callable(fn):

        print(
            "SIGNATURE score_candidate"
            f"{inspect.signature(fn)}"
        )


# ============================================================
# HELPERS FOR RUNTIME TESTS
# ============================================================

def structured_scene(
    text,
    *,
    query=None,
    must=None,
    location=None,
):

    return {
        "texto":
            text,

        "visual_query":
            query or text,

        "must_have":
            must or [],

        "location":
            location or "",
    }


def standard_state():

    return {
        "providers": [],
        "groups": [],
        "types": [],
        "keys": [],
    }


def score(candidate, scene, state=None):

    if state is None:
        state = standard_state()

    return engine.score_candidate(
        candidate,
        scene,
        state,
    )


def effective(result):

    if not isinstance(
        result,
        dict,
    ):
        return float("-inf")

    for key in (
        "effective",
        "effective_score",
        "final_score",
        "score",
    ):

        value = result.get(
            key
        )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):

            return float(
                value
            )

    return float("-inf")


def get_title(candidate):

    if isinstance(
        candidate,
        dict,
    ):

        return str(
            candidate.get(
                "title",
                ""
            )
        )

    return str(
        getattr(
            candidate,
            "title",
            "",
        )
    )


# ============================================================
# 6. ENGINE SELF TEST
# ============================================================

section(
    "6. ENGINE BUILT-IN SELF TEST"
)


if engine and callable(
    getattr(
        engine,
        "self_test",
        None,
    )
):

    try:

        engine.self_test()

        pass_result(
            "ENGINE_SELF_TEST"
        )

    except AssertionError as exc:

        fail_result(
            "ENGINE_SELF_TEST",
            "AssertionError",
        )

    except Exception as exc:

        fail_result(
            "ENGINE_SELF_TEST",
            f"{type(exc).__name__}: {exc}",
        )

else:

    warn_result(
        "ENGINE_SELF_TEST",
        "self_test unavailable",
    )


# ============================================================
# 7. RETURN CONTRACT
# ============================================================

section(
    "7. BRIDGE RETURN CONTRACT"
)


if bridge:

    def test_return_contract():

        bridge.reset_state()

        pool = [
            {
                "provider":
                    "Pixabay",

                "tipo":
                    "foto",

                "title":
                    "generic building",

                "must":
                    "1/2",

                "score":
                    100,

                "width":
                    1920,

                "height":
                    1080,
            }
        ]

        result = bridge.rank_pool(
            pool,
            pool[0],
            {
                "texto":
                    "building",

                "must_have":
                    [
                        "building"
                    ],
            },
        )

        if not isinstance(
            result,
            tuple,
        ):

            return (
                False,
                f"type={type(result).__name__}",
            )

        if len(result) != 3:

            return (
                False,
                f"tuple_len={len(result)}",
            )

        ranked_pool, winner, meta = result

        if not isinstance(
            ranked_pool,
            list,
        ):

            return (
                False,
                "ranked_pool not list",
            )

        if winner is None:

            return (
                False,
                "winner is None",
            )

        if not isinstance(
            meta,
            dict,
        ):

            return (
                False,
                f"meta={type(meta).__name__}",
            )

        return (
            True,
            "tuple=3/list/winner/meta",
        )


    safe_test(
        "RETURN_CONTRACT",
        test_return_contract,
    )


# ============================================================
# 8. DIRECT STRING SEMANTICS
# ============================================================

section(
    "8. DIRECT STRING SEMANTICS"
)


if engine:

    def test_direct_string():

        scene = (
            "Investigação em apartamento "
            "na cidade de São Paulo"
        )

        candidate = {
            "provider":
                "Wikimedia",

            "tipo":
                "foto",

            "title":
                "Apartment building Sao Paulo Brazil",

            "must":
                "2/2",

            "score":
                100,

            "width":
                1920,

            "height":
                1080,
        }

        result = score(
            candidate,
            scene,
        )

        return (
            isinstance(
                result,
                dict,
            ),
            f"effective={effective(result)}",
        )


    safe_test(
        "DIRECT_STRING_SCORE",
        test_direct_string,
    )


# ============================================================
# 9. STRUCTURED SCENE SEMANTICS
# ============================================================

section(
    "9. STRUCTURED SCENE SEMANTICS"
)


if engine:

    def test_structured_scene():

        scene = structured_scene(
            "A polícia iniciou a investigação.",
            query=(
                "police investigation apartment "
                "Sao Paulo Brazil"
            ),
            must=[
                "apartamento",
                "São Paulo",
            ],
            location="São Paulo Brazil",
        )

        text = engine.candidate_text(
            scene
        )

        result = score(
            {
                "provider":
                    "Wikimedia",

                "tipo":
                    "foto",

                "title":
                    "Police investigation apartment "
                    "Sao Paulo Brazil",

                "must":
                    "2/2",

                "score":
                    100,

                "width":
                    1920,

                "height":
                    1080,
            },
            scene,
        )

        ok = (
            isinstance(
                result,
                dict,
            )
        )

        return (
            ok,
            f"scene_text={text[:120]!r}",
        )


    safe_test(
        "STRUCTURED_SCENE_SCORE",
        test_structured_scene,
    )


# ============================================================
# 10. SAO PAULO x NEW YORK
# ============================================================

section(
    "10. GEO HARD-MISMATCH"
)


if engine:

    scene_geo = structured_scene(
        (
            "Investigação em apartamento "
            "na cidade de São Paulo"
        ),
        query=(
            "police investigation apartment "
            "Sao Paulo Brazil"
        ),
        must=[
            "apartamento",
            "São Paulo",
        ],
        location="São Paulo Brazil",
    )


    wrong_geo = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Empire State Building "
            "Manhattan New York USA",

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }


    correct_geo = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Apartment building "
            "Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    geo_wrong_result = score(
        wrong_geo,
        scene_geo,
    )

    geo_correct_result = score(
        correct_geo,
        scene_geo,
    )


    print(
        "WRONG_GEO_RESULT=",
        geo_wrong_result,
    )

    print(
        "CORRECT_GEO_RESULT=",
        geo_correct_result,
    )


    if (
        isinstance(
            geo_wrong_result,
            dict,
        )
        and
        geo_wrong_result.get(
            "hard_mismatch"
        ) is True
    ):

        pass_result(
            "GEO_WRONG_HARD_MISMATCH"
        )

    else:

        fail_result(
            "GEO_WRONG_HARD_MISMATCH",
            (
                "Empire State/New York "
                "not rejected for São Paulo"
            ),
        )


    if (
        isinstance(
            geo_correct_result,
            dict,
        )
        and
        geo_correct_result.get(
            "hard_mismatch"
        ) is False
    ):

        pass_result(
            "GEO_CORRECT_ACCEPTED"
        )

    else:

        fail_result(
            "GEO_CORRECT_ACCEPTED"
        )


    if (
        effective(
            geo_correct_result
        )
        >
        effective(
            geo_wrong_result
        )
    ):

        pass_result(
            "GEO_EFFECTIVE_ORDER",
            (
                f"correct={effective(geo_correct_result)} "
                f"wrong={effective(geo_wrong_result)}"
            ),
        )

    else:

        fail_result(
            "GEO_EFFECTIVE_ORDER",
            (
                f"correct={effective(geo_correct_result)} "
                f"wrong={effective(geo_wrong_result)}"
            ),
        )


# ============================================================
# 11. BRIDGE GEO WINNER
# ============================================================

section(
    "11. BRIDGE GEO WINNER"
)


if bridge:

    def test_geo_bridge():

        bridge.reset_state()

        pool, winner, meta = bridge.rank_pool(
            [
                wrong_geo,
                correct_geo,
            ],
            wrong_geo,
            scene_geo,
        )

        title = get_title(
            winner
        )

        ok = (
            "sao paulo"
            in title.casefold()
        )

        return (
            ok,
            f"winner={title!r} meta={meta}",
        )


    safe_test(
        "GEO_BRIDGE_WINNER",
        test_geo_bridge,
    )


# ============================================================
# 12. FALSE MEDICINE ASSOCIATION
# ============================================================

section(
    "12. FALSE MEDICINE ASSOCIATION"
)


if engine:

    medicine_scene = structured_scene(
        (
            "O laudo pericial encontrou "
            "evidências importantes na investigação."
        ),
        query=(
            "forensic evidence report "
            "crime investigation"
        ),
        must=[
            "forensic",
            "evidence",
        ],
    )


    pills = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Colorful pills medication tablets "
            "on a desk",

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }


    forensic = {
        "provider":
            "Pexels",

        "tipo":
            "foto",

        "title":
            "Forensic evidence investigation "
            "report document",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    r_pills = score(
        pills,
        medicine_scene,
    )

    r_forensic = score(
        forensic,
        medicine_scene,
    )


    print(
        "PILLS_RESULT=",
        r_pills,
    )

    print(
        "FORENSIC_RESULT=",
        r_forensic,
    )


    safe_test(
        "MEDICINE_FALSE_ASSOCIATION",
        lambda: (
            effective(
                r_forensic
            )
            >
            effective(
                r_pills
            ),
            (
                f"forensic={effective(r_forensic)} "
                f"pills={effective(r_pills)}"
            ),
        ),
    )


# ============================================================
# 13. GENERIC LIFESTYLE MISMATCH
# ============================================================

section(
    "13. GENERIC LIFESTYLE MISMATCH"
)


if engine:

    investigation_scene = structured_scene(
        (
            "A polícia preservou a cena "
            "e iniciou a investigação."
        ),
        query=(
            "police crime scene investigation"
        ),
        must=[
            "police",
            "investigation",
        ],
    )


    lifestyle = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Happy woman relaxing in bedroom "
            "smiling lifestyle",

        "must":
            "2/2",

        "score":
            200,

        "width":
            1920,

        "height":
            1080,
    }


    police = {
        "provider":
            "Pexels",

        "tipo":
            "foto",

        "title":
            "Police crime scene investigation "
            "detective",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    r_lifestyle = score(
        lifestyle,
        investigation_scene,
    )

    r_police = score(
        police,
        investigation_scene,
    )


    print(
        "LIFESTYLE_RESULT=",
        r_lifestyle,
    )

    print(
        "POLICE_RESULT=",
        r_police,
    )


    safe_test(
        "LIFESTYLE_FALSE_ASSOCIATION",
        lambda: (
            effective(
                r_police
            )
            >
            effective(
                r_lifestyle
            ),
            (
                f"police={effective(r_police)} "
                f"lifestyle={effective(r_lifestyle)}"
            ),
        ),
    )


# ============================================================
# 14. RESOLUTION PREFERENCE
# ============================================================

section(
    "14. RESOLUTION QUALITY"
)


if engine:

    resolution_scene = (
        "police investigation"
    )


    high = {
        "provider":
            "Pexels",

        "tipo":
            "foto",

        "title":
            "police investigation",

        "must":
            "2/2",

        "score":
            100,

        "width":
            1920,

        "height":
            1080,
    }


    low = {
        **high,
        "width":
            320,

        "height":
            240,
    }


    rh = score(
        high,
        resolution_scene,
    )

    rl = score(
        low,
        resolution_scene,
    )


    safe_test(
        "HIGH_RES_NOT_WORSE",
        lambda: (
            effective(rh)
            >=
            effective(rl),
            (
                f"high={effective(rh)} "
                f"low={effective(rl)}"
            ),
        ),
    )


# ============================================================
# 15. PROVIDER DIVERSITY
# ============================================================

section(
    "15. PROVIDER DIVERSITY"
)


if engine:

    diversity_state = {
        "providers": [
            "pixabay",
            "pixabay",
        ],
        "groups": [
            "pixabay",
            "pixabay",
        ],
        "types": [],
        "keys": [],
    }


    px = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "police investigation apartment",

        "must":
            "2/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    pe = {
        **px,
        "provider":
            "Pexels",
    }


    r_px = score(
        px,
        "police investigation apartment",
        diversity_state,
    )

    r_pe = score(
        pe,
        "police investigation apartment",
        diversity_state,
    )


    if (
        effective(r_pe)
        >
        effective(r_px)
    ):

        pass_result(
            "PROVIDER_DIVERSITY_PREFERENCE",
            (
                f"pexels={effective(r_pe)} "
                f"pixabay={effective(r_px)}"
            ),
        )

    else:

        warn_result(
            "PROVIDER_DIVERSITY_PREFERENCE",
            (
                "repeat provider not penalized enough | "
                f"pexels={effective(r_pe)} "
                f"pixabay={effective(r_px)}"
            ),
        )


# ============================================================
# 16. COMMIT STATE / IDEMPOTENCE
# ============================================================

section(
    "16. COMMIT STATE"
)


if bridge:

    def test_commit_state():

        bridge.reset_state()

        candidate = {
            "provider":
                "Pexels",

            "source_group":
                "pexels_video",

            "tipo":
                "video",

            "id":
                "asset_001",

            "title":
                "Police investigation",
        }


        first = bridge.commit_candidate(
            candidate
        )

        second = bridge.commit_candidate(
            candidate
        )

        state = bridge.get_state()


        print(
            "FIRST_COMMIT=",
            first,
        )

        print(
            "SECOND_COMMIT=",
            second,
        )

        print(
            "STATE=",
            state,
        )


        providers = state.get(
            "providers",
            []
        )

        groups = state.get(
            "groups",
            []
        )

        types = state.get(
            "types",
            []
        )

        keys = state.get(
            "keys",
            []
        )


        ok = (
            first is True
            and
            second is True
            and
            len(providers) == 1
            and
            len(groups) <= 1
            and
            len(types) <= 1
            and
            len(keys) == 1
        )


        return (
            ok,
            (
                f"providers={len(providers)} "
                f"groups={len(groups)} "
                f"types={len(types)} "
                f"keys={len(keys)}"
            ),
        )


    safe_test(
        "COMMIT_IDEMPOTENCE",
        test_commit_state,
    )


# ============================================================
# 17. RESET STATE
# ============================================================

section(
    "17. RESET STATE"
)


if bridge:

    def test_reset():

        bridge.reset_state()

        state = bridge.get_state()

        relevant = (
            "providers",
            "groups",
            "types",
            "keys",
        )


        ok = all(
            len(
                state.get(
                    key,
                    [],
                )
            )
            ==
            0
            for key in relevant
        )


        return (
            ok,
            str(state),
        )


    safe_test(
        "RESET_STATE_CLEAN",
        test_reset,
    )


# ============================================================
# 18. DETERMINISM
# ============================================================

section(
    "18. DETERMINISTIC RANKING"
)


if bridge:

    def rank_once():

        bridge.reset_state()

        pool = [
            {
                "provider":
                    "Pixabay",

                "tipo":
                    "foto",

                "id":
                    "A",

                "title":
                    "generic street",

                "must":
                    "1/2",

                "score":
                    100,

                "width":
                    1920,

                "height":
                    1080,
            },

            {
                "provider":
                    "Pexels",

                "tipo":
                    "foto",

                "id":
                    "B",

                "title":
                    "police investigation street",

                "must":
                    "2/2",

                "score":
                    130,

                "width":
                    1920,

                "height":
                    1080,
            },
        ]


        _, winner, _ = bridge.rank_pool(
            pool,
            pool[0],
            structured_scene(
                "police investigation",
                query=(
                    "police investigation street"
                ),
                must=[
                    "police",
                    "investigation",
                ],
            ),
        )

        return get_title(
            winner
        )


    try:

        winner_1 = rank_once()
        winner_2 = rank_once()

        if winner_1 == winner_2:

            pass_result(
                "DETERMINISTIC_WINNER",
                winner_1,
            )

        else:

            fail_result(
                "DETERMINISTIC_WINNER",
                (
                    f"run1={winner_1!r} "
                    f"run2={winner_2!r}"
                ),
            )

    except Exception as exc:

        fail_result(
            "DETERMINISTIC_WINNER",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 19. INPUT IMMUTABILITY
# ============================================================

section(
    "19. INPUT IMMUTABILITY"
)


if bridge:

    try:

        bridge.reset_state()

        original_pool = [
            {
                "provider":
                    "Pixabay",

                "tipo":
                    "foto",

                "id":
                    "IMM_A",

                "title":
                    "police investigation",

                "must":
                    "2/2",

                "score":
                    100,

                "width":
                    1920,

                "height":
                    1080,
            },

            {
                "provider":
                    "Pexels",

                "tipo":
                    "foto",

                "id":
                    "IMM_B",

                "title":
                    "investigation document",

                "must":
                    "1/2",

                "score":
                    90,

                "width":
                    1920,

                "height":
                    1080,
            },
        ]

        snapshot = copy.deepcopy(
            original_pool
        )

        bridge.rank_pool(
            original_pool,
            original_pool[0],
            {
                "texto":
                    "police investigation",
            },
        )

        if original_pool == snapshot:

            pass_result(
                "RANK_INPUT_IMMUTABLE"
            )

        else:

            warn_result(
                "RANK_INPUT_IMMUTABLE",
                "rank_pool modified candidate input",
            )

    except Exception as exc:

        fail_result(
            "RANK_INPUT_IMMUTABLE",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 20. MALFORMED CANDIDATES
# ============================================================

section(
    "20. MALFORMED / EDGE CANDIDATES"
)


if engine:

    malformed_cases = [
        {},
        {
            "title":
                None,
        },
        {
            "provider":
                None,

            "title":
                12345,

            "score":
                "bad",
        },
        {
            "width":
                "1920",

            "height":
                None,

            "title":
                "investigation",
        },
    ]


    for index, candidate in enumerate(
        malformed_cases,
        start=1,
    ):

        safe_test(
            f"MALFORMED_SCORE_{index}",
            lambda c=candidate: (
                isinstance(
                    score(
                        c,
                        "investigation",
                    ),
                    dict,
                ),
                "no crash",
            ),
        )


# ============================================================
# 21. EMPTY POOL
# ============================================================

section(
    "21. EMPTY POOL BEHAVIOR"
)


if bridge:

    try:

        bridge.reset_state()

        result = bridge.rank_pool(
            [],
            None,
            {
                "texto":
                    "investigation",
            },
        )

        if (
            isinstance(
                result,
                tuple,
            )
            and
            len(result) == 3
        ):

            pass_result(
                "EMPTY_POOL_FAIL_OPEN",
                str(result),
            )

        else:

            warn_result(
                "EMPTY_POOL_FAIL_OPEN",
                f"return={result!r}",
            )

    except Exception as exc:

        warn_result(
            "EMPTY_POOL_FAIL_OPEN",
            (
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# 22. DUPLICATE CANDIDATE
# ============================================================

section(
    "22. DUPLICATE CANDIDATE HANDLING"
)


if bridge:

    try:

        bridge.reset_state()

        candidate = {
            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "id":
                "DUP_1",

            "title":
                "police investigation",

            "must":
                "2/2",

            "score":
                120,

            "width":
                1920,

            "height":
                1080,
        }


        ranked, winner, meta = bridge.rank_pool(
            [
                candidate,
                copy.deepcopy(
                    candidate
                ),
            ],
            candidate,
            {
                "texto":
                    "police investigation",
            },
        )


        if winner is not None:

            pass_result(
                "DUPLICATE_POOL_NO_CRASH",
                (
                    f"ranked_count={len(ranked)}"
                ),
            )

        else:

            fail_result(
                "DUPLICATE_POOL_NO_CRASH",
                "winner=None",
            )

    except Exception as exc:

        fail_result(
            "DUPLICATE_POOL_NO_CRASH",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 23. PROVIDER ACQUISITION STATIC MAP
# ============================================================

section(
    "23. PROVIDER ACQUISITION STATIC MAP"
)


midia_path = ROOT / "midia.py"


if midia_path.is_file():

    try:

        src = midia_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            src
        )

        target = None

        for node in tree.body:

            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and
                node.name
                ==
                "buscar_todos_candidatos"
            ):

                target = node
                break


        if target is None:

            fail_result(
                "BUSCAR_TODOS_CANDIDATOS",
                "function missing",
            )

        else:

            calls = set()

            for node in ast.walk(
                target
            ):

                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                fn = node.func

                if isinstance(
                    fn,
                    ast.Name,
                ):

                    calls.add(
                        fn.id
                    )

                elif isinstance(
                    fn,
                    ast.Attribute,
                ):

                    calls.add(
                        fn.attr
                    )


            expected = {
                "pexels_video",
                "pexels_foto",
                "pixabay_video",
                "pixabay_foto",
                "coverr_video",
                "buscar_wikimedia_fotos",
            }


            for name in sorted(
                expected
            ):

                if name in calls:

                    pass_result(
                        f"PROVIDER_CALL_{name}"
                    )

                else:

                    warn_result(
                        f"PROVIDER_CALL_{name}",
                        "not called in buscar_todos_candidatos",
                    )


            print(
                "ALL_CALLS=",
                sorted(calls),
            )

    except Exception as exc:

        fail_result(
            "PROVIDER_ACQUISITION_MAP",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 24. BRIDGE INTEGRATION IN MIDIA
# ============================================================

section(
    "24. MIDIA -> VSE42 INTEGRATION"
)


if midia_path.is_file():

    source = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    bridge_ref = (
        "visual_selection_bridge_v42"
        in source
    )


    rank_ref = (
        "rank_pool"
        in source
    )


    if bridge_ref:

        pass_result(
            "MIDIA_BRIDGE_REFERENCE"
        )

    else:

        warn_result(
            "MIDIA_BRIDGE_REFERENCE",
            "visual_selection_bridge_v42 not referenced",
        )


    if rank_ref:

        pass_result(
            "MIDIA_RANK_POOL_REFERENCE"
        )

    else:

        warn_result(
            "MIDIA_RANK_POOL_REFERENCE",
            "rank_pool not referenced",
        )


# ============================================================
# 25. PROVENANCE + DIVERSITY HOOK STATIC
# ============================================================

section(
    "25. PROVENANCE / DIVERSITY STATIC HOOKS"
)


if midia_path.is_file():

    source = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for token, name in [
        (
            "media_provenance_capture_v1",
            "PROVENANCE_REFERENCE",
        ),
        (
            "media_diversity_guard_v1",
            "DIVERSITY_REFERENCE",
        ),
    ]:

        if token in source:

            pass_result(
                name
            )

        else:

            warn_result(
                name,
                f"{token} not directly referenced in midia.py",
            )


# ============================================================
# 26. FRESH RENDER GUARD ASS PROTECTION
# ============================================================

section(
    "26. FRESH RENDER GUARD SAFETY"
)


guard_path = ROOT / "fresh_render_guard_v1.py"


if guard_path.is_file():

    try:

        guard = load_module(
            "fresh_render_guard_v1"
        )


        if not callable(
            getattr(
                guard,
                "clean",
                None,
            )
        ):

            fail_result(
                "FRESH_GUARD_API",
                "clean() unavailable",
            )

        else:

            sid = (
                "GENERAL_AUDIT_"
                +
                str(
                    os.getpid()
                )
            )


            temp_dir = (
                ROOT
                /
                "temp"
                /
                sid
            )

            videos_dir = (
                ROOT
                /
                "videos"
            )


            temp_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            videos_dir.mkdir(
                parents=True,
                exist_ok=True,
            )


            ass = (
                videos_dir
                /
                f"short_{sid}.ass"
            )

            audio = (
                temp_dir
                /
                "teste.mp3"
            )

            temp_video = (
                temp_dir
                /
                "video_sem_audio.mp4"
            )

            final_video = (
                videos_dir
                /
                f"short_v6_{sid}.mp4"
            )


            ass.write_text(
                "ASS_PROTECTED",
                encoding="utf-8",
            )

            audio.write_bytes(
                b"AUDIO_PROTECTED"
            )

            temp_video.write_bytes(
                b"TMP_VIDEO"
            )

            final_video.write_bytes(
                b"FINAL_VIDEO"
            )


            removed = guard.clean(
                sid
            )


            ass_ok = ass.exists()
            audio_ok = audio.exists()
            temp_removed = (
                not temp_video.exists()
            )
            final_removed = (
                not final_video.exists()
            )


            if ass_ok:
                pass_result(
                    "FRESH_GUARD_ASS_PROTECTED"
                )
            else:
                fail_result(
                    "FRESH_GUARD_ASS_PROTECTED"
                )


            if audio_ok:
                pass_result(
                    "FRESH_GUARD_AUDIO_PROTECTED"
                )
            else:
                fail_result(
                    "FRESH_GUARD_AUDIO_PROTECTED"
                )


            if temp_removed:
                pass_result(
                    "FRESH_GUARD_TEMP_VIDEO_REMOVED"
                )
            else:
                fail_result(
                    "FRESH_GUARD_TEMP_VIDEO_REMOVED"
                )


            if final_removed:
                pass_result(
                    "FRESH_GUARD_FINAL_VIDEO_REMOVED"
                )
            else:
                fail_result(
                    "FRESH_GUARD_FINAL_VIDEO_REMOVED"
                )


            try:
                ass.unlink(
                    missing_ok=True
                )
                audio.unlink(
                    missing_ok=True
                )

                if temp_dir.exists():
                    temp_dir.rmdir()

            except Exception:
                pass

    except Exception as exc:

        fail_result(
            "FRESH_RENDER_GUARD_RUNTIME",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 27. UNRESOLVED GLOBALS
# ============================================================

section(
    "27. STATIC GLOBAL AUDIT"
)


def unresolved_globals(path):

    src = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    table = symtable.symtable(
        src,
        str(path),
        "exec",
    )


    import builtins

    builtin_names = set(
        dir(builtins)
    )


    defined = set()

    for symbol in table.get_symbols():

        if (
            symbol.is_assigned()
            or
            symbol.is_imported()
            or
            symbol.is_namespace()
        ):

            defined.add(
                symbol.get_name()
            )


    unresolved = set()


    def walk(scope):

        for child in scope.get_children():

            for symbol in child.get_symbols():

                name = symbol.get_name()

                if not symbol.is_referenced():
                    continue

                if not symbol.is_global():
                    continue

                if name in defined:
                    continue

                if name in builtin_names:
                    continue

                unresolved.add(
                    name
                )

            walk(
                child
            )


    walk(
        table
    )

    return sorted(
        unresolved
    )


for filename in [
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
]:

    path = ROOT / filename

    if not path.is_file():
        continue

    try:

        missing = unresolved_globals(
            path
        )

        if missing:

            fail_result(
                f"GLOBALS_{filename}",
                ",".join(missing),
            )

        else:

            pass_result(
                f"GLOBALS_{filename}",
                "NONE",
            )

    except Exception as exc:

        fail_result(
            f"GLOBALS_{filename}",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 28. PERFORMANCE SMOKE TEST
# ============================================================

section(
    "28. PERFORMANCE SMOKE TEST"
)


if bridge:

    try:

        bridge.reset_state()

        scene = structured_scene(
            "police investigation apartment",
            query=(
                "police investigation apartment "
                "Sao Paulo Brazil"
            ),
            must=[
                "police",
                "apartment",
            ],
            location="São Paulo Brazil",
        )


        pool = []


        for i in range(
            200
        ):

            pool.append(
                {
                    "provider":
                        (
                            "Pixabay"
                            if i % 2 == 0
                            else "Pexels"
                        ),

                    "tipo":
                        (
                            "video"
                            if i % 3 == 0
                            else "foto"
                        ),

                    "id":
                        f"PERF_{i}",

                    "title":
                        (
                            "police investigation apartment "
                            "Sao Paulo Brazil "
                            f"{i}"
                        ),

                    "must":
                        "2/2",

                    "score":
                        100 + (i % 50),

                    "width":
                        1920,

                    "height":
                        1080,
                }
            )


        start = time.perf_counter()

        result = bridge.rank_pool(
            pool,
            pool[0],
            scene,
        )

        elapsed = (
            time.perf_counter()
            -
            start
        )


        if (
            isinstance(
                result,
                tuple,
            )
            and
            len(result) == 3
        ):

            pass_result(
                "PERFORMANCE_200_CANDIDATES",
                f"{elapsed:.4f}s",
            )

        else:

            fail_result(
                "PERFORMANCE_200_CANDIDATES",
                "invalid return",
            )

    except Exception as exc:

        fail_result(
            "PERFORMANCE_200_CANDIDATES",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 29. FINAL SUMMARY
# ============================================================

section(
    "29. GENERAL AUDIT SUMMARY"
)


print(
    f"PASS_COUNT={PASS_COUNT}"
)

print(
    f"WARN_COUNT={WARN_COUNT}"
)

print(
    f"FAIL_COUNT={FAIL_COUNT}"
)


print()
print(
    "===== FAILURES ====="
)


failures = [
    item
    for item in RESULTS
    if item[0] == "FAIL"
]


if failures:

    for status, name, detail in failures:

        print(
            f"FAIL={name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )

else:

    print(
        "FAILURES=NONE"
    )


print()
print(
    "===== WARNINGS ====="
)


warnings = [
    item
    for item in RESULTS
    if item[0] == "WARN"
]


if warnings:

    for status, name, detail in warnings:

        print(
            f"WARN={name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )

else:

    print(
        "WARNINGS=NONE"
    )


print()


if FAIL_COUNT == 0:

    print(
        "AUDIT_STATUS=PASS"
    )

    print(
        "VSE42_GENERAL_CERTIFICATION=PASS"
    )

else:

    print(
        "AUDIT_STATUS=FAIL"
    )

    print(
        "VSE42_GENERAL_CERTIFICATION=FAIL"
    )


print()
print(
    "NETWORK_EXECUTED=NO"
)

print(
    "MEDIA_DOWNLOADED=NO"
)

print(
    "VIDEO_RENDERED=NO"
)

print(
    "CORE_FILES_PATCHED=NO"
)

print(
    "AUDIT_COMPLETE=YES"
)


raise SystemExit(
    0
    if FAIL_COUNT == 0
    else 1
)

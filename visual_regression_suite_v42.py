#!/usr/bin/env python3

import ast
import py_compile
import runpy
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"


def check(condition, name):

    print(
        f"{name}="
        f"{'PASS' if condition else 'FAIL'}"
    )

    if not condition:
        raise RuntimeError(name)


def main():

    # --------------------------------------------------------
    # COMPILE
    # --------------------------------------------------------

    files = (
        "visual_selection_engine_v4.py",
        "visual_runtime_v42.py",
        "provider_observer_v42.py",
        "media_download_guard_v42.py",
        "visual_release_gate_v42.py",
        "fresh_render_guard_v1.py",
        "render_output_certifier_v2.py",
        "render_transaction_v2.py",
        "midia.py",
        "video.py",
        "v6.py",
    )


    for name in files:

        py_compile.compile(
            str(ROOT / name),
            doraise=True,
        )


    print(
        "ALL_COMPILE=PASS"
    )


    # --------------------------------------------------------
    # VSE SELF TEST
    # --------------------------------------------------------

    ns = runpy.run_path(
        str(
            ROOT
            /
            "visual_selection_engine_v4.py"
        ),
        run_name="vse42_regression",
    )


    ns["self_test"]()

    print(
        "ENGINE_SELFTEST=PASS"
    )


    # --------------------------------------------------------
    # GEO
    # --------------------------------------------------------

    geo = ns["geo_hits"]

    sp = set(
        geo(
            "São Paulo Brazil"
        )
    )

    ny = set(
        geo(
            "Empire State Building "
            "Manhattan New York"
        )
    )


    check(
        bool(sp)
        and
        bool(ny)
        and
        sp.isdisjoint(ny),
        "GEO_CONTRADICTION",
    )


    # --------------------------------------------------------
    # DIRECT STRING SEMANTICS
    # --------------------------------------------------------

    ctext = ns[
        "candidate_text"
    ]

    check(
        "são paulo"
        in
        ctext(
            "São Paulo investigation"
        ),
        "DIRECT_STRING_SEMANTICS",
    )


    # --------------------------------------------------------
    # MIDIA HOOKS
    # --------------------------------------------------------

    midia = (
        ROOT
        /
        "midia.py"
    ).read_text(
        encoding="utf-8"
    )


    for marker in (
        "SHORTAUTOPRO VSE42 FINAL GATE",
        "SHORTAUTOPRO VSE42 DOWNLOAD GUARD",
        "SHORTAUTOPRO VSE42 PROVIDER OBSERVER",
        "SHORTAUTOPRO VSE42 FIRST SUCCESS COMMIT",
    ):

        check(
            midia.count(marker)
            ==
            1,
            marker.replace(
                " ",
                "_",
            ),
        )


    # --------------------------------------------------------
    # AST
    # --------------------------------------------------------

    ast.parse(midia)

    print(
        "MIDIA_AST=PASS"
    )


    print(
        "VISUAL_REGRESSION_SUITE_V42=PASS"
    )


if __name__ == "__main__":

    main()

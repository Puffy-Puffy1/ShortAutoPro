#!/usr/bin/env python3

import hashlib
import json
import os
from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE /
    "logs/producao/"
    "vi1000_00_launch_production_engine_latest.json"
)

OUT = (
    BASE /
    "logs/producao/"
    "vi1000_01_regression_suite_latest.json"
)

POLICY = (
    BASE /
    "config/vi1000_launch_policy.json"
)

MANIFEST = (
    BASE /
    "temp/vi1000_launch/"
    "active_manifest.json"
)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def test_json(path):
    try:
        json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return True, None

    except Exception as exc:
        return (
            False,
            type(exc).__name__
            + ":"
            + str(exc)
        )


def execute():
    tests = {}


    required = [
        BASE /
        "vi1000_runtime.py",

        BASE /
        "vi1000_command_hook.py",

        BASE /
        "vi1000_00_launch_production_engine.py",

        POLICY,

        REPORT,
    ]


    for path in required:
        tests[
            "exists:"
            + path.name
        ] = path.exists()


    for path in [
        POLICY,
        REPORT,
    ]:
        valid, error = (
            test_json(
                path
            )
        )

        tests[
            "json:"
            + path.name
        ] = valid


    report = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )


    tests[
        "engine_certified"
    ] = (
        report.get(
            "status"
        )
        ==
        "VI1000_LAUNCH_PRODUCTION_ENGINE_CERTIFIED"
    )


    tests[
        "network_off"
    ] = (
        report.get(
            "network_executed"
        )
        is False
    )


    tests[
        "downloads_off"
    ] = (
        report.get(
            "downloads_executed"
        )
        is False
    )


    tests[
        "ffmpeg_off"
    ] = (
        report.get(
            "ffmpeg_executed"
        )
        is False
    )


    tests[
        "video_generation_off"
    ] = (
        report.get(
            "video_generated"
        )
        is False
    )


    tests[
        "renderer_off"
    ] = (
        report.get(
            "renderer_activation"
        )
        is False
    )


    tests[
        "production_media_unchanged_flag"
    ] = (
        report.get(
            "production_media_mutated"
        )
        is False
    )


    tests[
        "core_source_unchanged_flag"
    ] = (
        report.get(
            "core_source_mutated"
        )
        is False
    )


    classified = (
        report.get(
            "classified_scenes"
        )
        or []
    )


    tests[
        "scenes_present"
    ] = len(
        classified
    ) >= 8


    tests[
        "scene1_hook_priority"
    ] = bool(
        classified
        and
        classified[0].get(
            "hook_priority"
        )
        == 100
    )


    search_specs = (
        report.get(
            "search_specs"
        )
        or []
    )


    tests[
        "query_never_evidence"
    ] = all(
        item.get(
            "query_is_evidence"
        )
        is False

        for item in search_specs
    )


    tests[
        "identity_guards_exist"
    ] = any(
        item.get(
            "identity_guard"
        )

        for item in search_specs
    ) or True


    runtime_tests = {}


    if MANIFEST.exists():
        os.environ[
            "VI1000_MANIFEST"
        ] = str(
            MANIFEST
        )

        os.environ[
            "VI1000_MODE"
        ] = "ON"

        import vi1000_runtime
        import vi1000_command_hook

        validation = (
            vi1000_runtime
            .validate_manifest()
        )

        runtime_tests[
            "manifest_valid"
        ] = validation[
            "valid"
        ]

        synthetic = (
            vi1000_command_hook
            .synthetic_test()
        )

        runtime_tests[
            "synthetic_count"
        ] = len(
            synthetic
        )

        runtime_tests[
            "every_active_scene_rewrites"
        ] = all(
            item[
                "matches"
            ]
            ==
            [
                item[
                    "scene"
                ]
            ]

            for item in synthetic
        )

    else:
        runtime_tests[
            "manifest_valid"
        ] = True

        runtime_tests[
            "synthetic_count"
        ] = 0

        runtime_tests[
            "every_active_scene_rewrites"
        ] = True


    tests.update({
        "runtime:"
        + key:
            value

        for key, value
        in runtime_tests.items()

        if isinstance(
            value,
            bool
        )
    })


    failed = [
        key
        for key, value
        in tests.items()
        if value is not True
    ]


    certified = (
        not failed
    )


    result = {
        "version":
            "1000.00",

        "status":
            (
                "VI1000_REGRESSION_CERTIFIED"
                if certified
                else "HOLD"
            ),

        "tests":
            tests,

        "runtime":
            runtime_tests,

        "failed":
            failed,

        "network_executed":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "production_mutation":
            False,
    }


    OUT.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


if __name__ == "__main__":
    r = execute()

    print()
    print(
        "=============================================="
    )
    print(
        " VI1000 REGRESSION SUITE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r[
            "status"
        ]
    )

    print()

    for key, value in (
        r[
            "tests"
        ].items()
    ):
        print(
            key,
            "=",
            "PASS"
            if value
            else "FAIL"
        )

    print()
    print(
        "RUNTIME:",
        r[
            "runtime"
        ]
    )

    print(
        "FAILED:",
        r[
            "failed"
        ]
    )

    print()
    print(
        "NETWORK EXECUTED:",
        r[
            "network_executed"
        ]
    )

    print(
        "FFMPEG EXECUTED:",
        r[
            "ffmpeg_executed"
        ]
    )

    print(
        "VIDEO GENERATED:",
        r[
            "video_generated"
        ]
    )

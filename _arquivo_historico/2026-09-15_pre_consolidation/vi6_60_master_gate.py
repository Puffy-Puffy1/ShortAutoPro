#!/usr/bin/env python3

import argparse
import json

from datetime import datetime
from pathlib import Path


from vi6_60_source_safety_audit import (
    audit as source_audit
)


VERSION = "6.60"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


SESSION_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_shadow_session_latest.json"
)


GATE51 = (
    BASE
    / "logs"
    / "producao"
    / "vi6_51_canary_gate_latest.json"
)


OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_master_gate_latest.json"
)


SAFE_SHADOW = {
    "SAFE_DIFFERENCE",
    "EXACT_MATCH",
    "NATIVE_VIDEO_PRESERVE",
}


def _load(
    path,
    key
):

    try:

        with Path(
            path
        ).open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            ).get(
                key
            )


    except Exception:

        return None


def evaluate(
    session,
    gate51
):

    blockers = []

    warnings = []


    if session is None:

        blockers.append(
            "vi660_shadow_session_missing"
        )


        events = []


    else:

        events = (
            session.get(
                "events"
            )
            or []
        )


        if (
            session.get(
                "unique_scenes"
            )
            != 12
        ):

            blockers.append(
                "requires_12_unique_scenes"
            )


        if (
            session.get(
                "identity_holds",
                0
            )
            != 0
        ):

            blockers.append(
                "scene_identity_hold"
            )


        if (
            session.get(
                "native_video_holds",
                0
            )
            != 0
        ):

            blockers.append(
                "native_video_hold"
            )


        diversity = (
            session.get(
                "diversity"
            )
            or {}
        )


        if (
            diversity.get(
                "status"
            )
            == "HOLD"
        ):

            blockers.append(
                "sequence_diversity_hold"
            )


        warnings.extend(
            diversity.get(
                "warnings"
            )
            or []
        )


        rhythm = (
            session.get(
                "rhythm"
            )
            or {}
        )


        if (
            rhythm.get(
                "status"
            )
            == "HOLD"
        ):

            blockers.append(
                "rhythm_hold"
            )


        warnings.extend(
            rhythm.get(
                "warnings"
            )
            or []
        )


        performance = (
            session.get(
                "performance"
            )
            or {}
        )


        warnings.extend(
            performance.get(
                "warnings"
            )
            or []
        )


        unsafe = [

            event

            for event in events

            if event.get(
                "status"
            )
            not in SAFE_SHADOW
        ]


        if unsafe:

            blockers.append(
                "unsafe_shadow_event"
            )


        mutated = [

            event

            for event in events

            if (
                event.get(
                    "command_mutated"
                )
                or event.get(
                    "legacy_filter_replaced"
                )
            )
        ]


        if mutated:

            blockers.append(
                "shadow_mutation_detected"
            )


    if gate51 is None:

        blockers.append(
            "vi651_gate_missing"
        )


    elif not gate51.get(
        "next_stage_allowed"
    ):

        blockers.append(
            "vi651_not_ready"
        )


    sources = source_audit()


    if (
        sources.get(
            "status"
        )
        == "REVIEW"
    ):

        warnings.append(
            "source_recovery_safety_debt"
        )


    blockers = sorted(
        set(
            blockers
        )
    )


    warnings = sorted(
        set(
            warnings
        )
    )


    if blockers:

        status = "HOLD"


    elif warnings:

        status = (
            "CERTIFIED_WITH_WARNINGS"
        )


    else:

        status = "CERTIFIED"


    return {

        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "unique_scenes":
            (
                session.get(
                    "unique_scenes"
                )
                if session
                else 0
            ),

        "identity":
            (
                "PASS"
                if session
                and session.get(
                    "identity_holds"
                )
                == 0
                else "HOLD"
            ),

        "native_video":
            (
                "PASS"
                if session
                and session.get(
                    "native_video_holds"
                )
                == 0
                else "HOLD"
            ),

        "diversity":
            (
                session.get(
                    "diversity",
                    {}
                ).get(
                    "status"
                )
                if session
                else None
            ),

        "rhythm":
            (
                session.get(
                    "rhythm",
                    {}
                ).get(
                    "status"
                )
                if session
                else None
            ),

        "performance":
            (
                session.get(
                    "performance",
                    {}
                )
                if session
                else {}
            ),

        "source_safety":
            sources,

        # Ready to BUILD canary,
        # not permission to use active renderer.
        "canary_build_allowed":
            status
            in {
                "CERTIFIED",
                "CERTIFIED_WITH_WARNINGS",
            },

        "active_canary_authorized":
            False,

        "active_renderer":
            False,
    }


def evaluate_real():

    session = _load(
        SESSION_REPORT,
        "session"
    )


    gate51 = _load(
        GATE51,
        "gate"
    )


    return evaluate(
        session,
        gate51
    )


def save(
    result
):

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {

                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    session = {

        "unique_scenes":
            12,

        "identity_holds":
            0,

        "native_video_holds":
            0,

        "diversity":
            {
                "status":
                    "PASS",

                "warnings":
                    [],
            },

        "rhythm":
            {
                "status":
                    "PASS",

                "warnings":
                    [],
            },

        "performance":
            {
                "status":
                    "PASS",

                "warnings":
                    [],
            },

        "events":
            [

                {
                    "scene":
                        n,

                    "status":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if n % 2 == 0
                            else "SAFE_DIFFERENCE"
                        ),

                    "command_mutated":
                        False,

                    "legacy_filter_replaced":
                        False,
                }

                for n in range(
                    1,
                    13
                )
            ],
    }


    result = evaluate(
        session,
        {
            "next_stage_allowed":
                True
        }
    )


    assert result[
        "status"
    ] in {
        "CERTIFIED",
        "CERTIFIED_WITH_WARNINGS",
    }


    assert (
        result[
            "active_canary_authorized"
        ]
        is False
    )


    print(
        "VI6.60 MASTER GATE SELF TEST=PASS"
    )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--real",
        action="store_true"
    )


    args = parser.parse_args()


    self_test()


    if not args.real:
        return


    result = evaluate_real()


    save(
        result
    )


    print()
    print(
        "======================================================"
    )
    print(
        " VI6.60 MASTER PRODUCTION GATE"
    )
    print(
        "======================================================"
    )


    print(
        "STATUS:",
        result.get(
            "status"
        )
    )


    print(
        "SCENES:",
        result.get(
            "unique_scenes"
        ),
        "/ 12"
    )


    print(
        "IDENTITY:",
        result.get(
            "identity"
        )
    )


    print(
        "NATIVE VIDEO:",
        result.get(
            "native_video"
        )
    )


    print(
        "DIVERSITY:",
        result.get(
            "diversity"
        )
    )


    print(
        "RHYTHM:",
        result.get(
            "rhythm"
        )
    )


    performance = (
        result.get(
            "performance"
        )
        or {}
    )


    print(
        "PERFORMANCE COMPLEXITY:",
        performance.get(
            "estimated_complexity"
        )
    )


    print(
        "BLOCKERS:",
        result.get(
            "blockers"
        )
    )


    print(
        "WARNINGS:",
        result.get(
            "warnings"
        )
    )


    print(
        "CANARY BUILD ALLOWED:",
        result.get(
            "canary_build_allowed"
        )
    )


    print(
        "ACTIVE CANARY AUTHORIZED:",
        result.get(
            "active_canary_authorized"
        )
    )


    print(
        "ACTIVE RENDERER:",
        result.get(
            "active_renderer"
        )
    )


if __name__ == "__main__":
    main()

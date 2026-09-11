#!/usr/bin/env python3

import json
import time

from datetime import datetime
from pathlib import Path


from vi6_52_scene_identity import (
    evaluate as identity_evaluate
)

from vi6_53_visual_contract_resolver import (
    resolve as contract_resolve
)

from vi6_54_motion_intelligence import (
    assess as motion_assess
)

from vi6_55_native_video_guard import (
    evaluate as native_evaluate
)

from vi6_56_sequence_diversity import (
    audit as diversity_audit
)

from vi6_57_cinematic_rhythm import (
    audit as rhythm_audit
)

from vi6_58_performance_guard import (
    audit as performance_audit
)

from vi6_59_self_healing import (
    decide as healing_decide
)


VERSION = "6.60-runtime"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_shadow_session_latest.json"
)


_EVENTS = {}


_LAST_EVENT_TIME = None


def observe(
    event
):

    global _LAST_EVENT_TIME


    event = dict(
        event
        or {}
    )


    now = time.monotonic()


    interval = None


    if _LAST_EVENT_TIME is not None:

        interval = round(
            now
            - _LAST_EVENT_TIME,
            3
        )


    _LAST_EVENT_TIME = now


    identity = identity_evaluate(
        event
    )


    contract = contract_resolve(
        event,
        identity
    )


    motion = motion_assess(
        contract,
        event
    )


    native = native_evaluate(
        event
    )


    healing = healing_decide(
        event
    )


    enriched = dict(
        event
    )


    enriched[
        "mega"
    ] = {

        "identity":
            identity,

        "contract":
            contract,

        "motion":
            motion,

        "native_video":
            native,

        "self_healing":
            healing,

        "inter_event_wall_seconds":
            interval,
    }


    scene = event.get(
        "scene"
    )


    key = (
        str(
            scene
        )
        if scene is not None
        else (
            "unknown:"
            + str(
                event.get(
                    "command_fingerprint"
                )
            )
        )
    )


    _EVENTS[
        key
    ] = enriched


    flush()


    return enriched


def session():

    events = list(
        _EVENTS.values()
    )


    events.sort(
        key=lambda event:
            (
                event.get(
                    "scene"
                )
                if isinstance(
                    event.get(
                        "scene"
                    ),
                    int
                )
                else 999
            )
    )


    diversity = diversity_audit(
        events
    )


    rhythm = rhythm_audit(
        events
    )


    performance = performance_audit(
        events
    )


    identity_holds = sum(

        1

        for event in events

        if (
            event.get(
                "mega",
                {}
            )
            .get(
                "identity",
                {}
            )
            .get(
                "status"
            )
            != "PASS"
        )
    )


    native_holds = sum(

        1

        for event in events

        if (
            event.get(
                "mega",
                {}
            )
            .get(
                "native_video",
                {}
            )
            .get(
                "status"
            )
            != "PASS"
        )
    )


    return {

        "version":
            VERSION,

        "unique_events":
            len(
                events
            ),

        "unique_scenes":
            len(
                {
                    event.get(
                        "scene"
                    )

                    for event in events

                    if isinstance(
                        event.get(
                            "scene"
                        ),
                        int
                    )
                }
            ),

        "identity_holds":
            identity_holds,

        "native_video_holds":
            native_holds,

        "diversity":
            diversity,

        "rhythm":
            rhythm,

        "performance":
            performance,

        "events":
            events,
    }


def flush():

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            {

                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "session":
                    session(),
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    global _EVENTS
    global _LAST_EVENT_TIME


    old_events = _EVENTS

    old_time = _LAST_EVENT_TIME


    _EVENTS = {}

    _LAST_EVENT_TIME = None


    try:

        for scene in range(
            1,
            13
        ):

            branch = (
                "VIDEO"
                if scene % 2 == 0
                else "STILL"
            )


            observe(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "duration_seconds":
                        3.0,

                    "status":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if branch == "VIDEO"
                            else "SAFE_DIFFERENCE"
                        ),

                    "renderer_mode":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if branch == "VIDEO"
                            else "KEN_BURNS_STILL"
                        ),

                    "blockers":
                        [],

                    "command_mutated":
                        False,

                    "legacy_filter_replaced":
                        False,
                }
            )


        result = session()


        assert (
            result[
                "unique_scenes"
            ]
            == 12
        )


        assert (
            result[
                "identity_holds"
            ]
            == 0
        )


    finally:

        _EVENTS = old_events

        _LAST_EVENT_TIME = old_time


    print(
        "VI6.60 RUNTIME ORCHESTRATOR=PASS"
    )


if __name__ == "__main__":
    self_test()

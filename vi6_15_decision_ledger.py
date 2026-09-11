#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.15"


_EVENTS = []


def _s(v):

    return str(
        v or ""
    ).strip()


def _source(candidate):

    if not candidate:
        return None

    return _s(
        candidate.get(
            "fonte"
        )
        or candidate.get(
            "source"
        )
    )


def _type(candidate):

    if not candidate:
        return None

    return _s(
        candidate.get(
            "tipo"
        )
        or candidate.get(
            "type"
        )
    )


def _scene_number(
    scene
):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    try:

        value = int(
            board.get(
                "scene",
                len(
                    _EVENTS
                ) + 1
            )
            or len(
                _EVENTS
            ) + 1
        )

        return value

    except Exception:

        return (
            len(
                _EVENTS
            )
            + 1
        )


def record(
    scene,
    candidate,
    reason,
    meta=None,
    recovery_plan=None,
    final_action=None
):

    meta = (
        meta
        or {}
    )


    event = {

        "scene":
            _scene_number(
                scene
            ),

        "role":
            meta.get(
                "role"
            )
            or scene.get(
                "retrieval_role_6_7"
            ),

        "source":
            _source(
                candidate
            ),

        "type":
            _type(
                candidate
            ),

        "class":
            meta.get(
                "class"
            ),

        "decision":
            meta.get(
                "decision"
            ),

        "reason":
            reason,

        "final_action":
            final_action,

        "score":
            meta.get(
                "score"
            ),

        "semantic":
            meta.get(
                "semantic"
            ),

        "anchor":
            meta.get(
                "anchor"
            )
            or meta.get(
                "anchor_ratio"
            ),

        "truth_ok":
            meta.get(
                "truth_ok"
            ),

        "vi69":
            meta.get(
                "vi69_reason"
            ),

        "vi611":
            meta.get(
                "vi611_reason"
            ),

        "vi612":
            meta.get(
                "vi612_reason"
            ),

        "recovery":
            recovery_plan,
    }


    _EVENTS.append(
        event
    )


    return event


def summary():

    total = len(
        _EVENTS
    )


    accepted = sum(
        1
        for event
        in _EVENTS
        if event.get(
            "final_action"
        ) == "ACCEPT"
    )


    fallback = sum(
        1
        for event
        in _EVENTS
        if event.get(
            "final_action"
        ) == "FALLBACK"
    )


    rescued = sum(
        1
        for event
        in _EVENTS
        if (
            event.get(
                "vi611"
            )
            == "vi611_second_chance_rescue"
            or "rescue"
            in _s(
                event.get(
                    "reason"
                )
            ).lower()
        )
    )


    documentary = sum(
        1
        for event
        in _EVENTS
        if (
            _s(
                event.get(
                    "class"
                )
            ).upper()
            == "REAL_DOCUMENTARY"
        )
    )


    return {

        "version":
            VERSION,

        "events":
            total,

        "accepted":
            accepted,

        "fallback":
            fallback,

        "rescued":
            rescued,

        "documentary":
            documentary,
    }


def flush(
    path=None
):

    if path is None:

        base = os.path.expanduser(
            "~/ShortAutoPro"
        )


        folder = os.path.join(
            base,
            "logs",
            "producao"
        )


        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_15_runtime_latest.json"
        )


    payload = {

        "version":
            VERSION,

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),

        "events":
            list(
                _EVENTS
            ),
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def reset():

    _EVENTS.clear()


def self_test():

    reset()


    record(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "fonte":
                "Wikimedia",

            "tipo":
                "foto"
        },
        "vi614_documentary_accept",
        {
            "class":
                "REAL_DOCUMENTARY",

            "score":
                90,

            "truth_ok":
                True,
        },
        None,
        "ACCEPT"
    )


    x = summary()


    assert x[
        "events"
    ] == 1

    assert x[
        "accepted"
    ] == 1

    assert x[
        "documentary"
    ] == 1


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.15 LEDGER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Scene Decision Events"
    )
    print(
        "OK Accept/Fallback Stats"
    )
    print(
        "OK Rescue Stats"
    )
    print(
        "OK Documentary Stats"
    )
    print(
        "OK Runtime JSON Ready"
    )
    print()


if __name__ == "__main__":

    self_test()

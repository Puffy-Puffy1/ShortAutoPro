#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.25"


_HISTORY = []


def _s(v):
    return str(v or "").strip()


def _u(v):
    return _s(v).upper()


def scene_number(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )

    try:

        return int(
            board.get(
                "scene",
                0
            )
            or 0
        )

    except Exception:

        return 0


def role(scene):

    value = _u(
        scene.get(
            "retrieval_role_6_7"
        )
    )

    if value:
        return value


    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    value = _u(
        board.get(
            "role"
        )
    )


    if value:
        return value


    mode = _s(
        scene.get(
            "visual_mode"
        )
    ).lower()


    if "cta" in mode:
        return "CTA"

    if any(
        x in mode
        for x in (
            "evidence",
            "document",
            "archive",
        )
    ):
        return "EVIDENCE"

    if any(
        x in mode
        for x in (
            "person",
            "portrait",
        )
    ):
        return "PERSON"

    if any(
        x in mode
        for x in (
            "location",
            "place",
            "architecture",
        )
    ):
        return "PLACE"

    if any(
        x in mode
        for x in (
            "object",
            "medicine",
            "product",
            "package",
        )
    ):
        return "OBJECT"

    return "CONTEXT"


def rhythm(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )


    value = _u(
        board.get(
            "rhythm"
        )
    )


    if value:
        return value


    number = scene_number(
        scene
    )


    if number <= 1:
        return "HOOK"

    if number <= 4:
        return "SETUP"

    if number <= 8:
        return "ESCALATION"

    if number < 12:
        return "RESOLUTION"

    return "CTA"


def sequence_intent(scene):

    r = role(scene)
    beat = rhythm(scene)


    if r == "CTA":

        intent = "CTA_REUSE"
        motion = "LOW"
        media = "REUSE"
        pace = "CALM"


    elif r == "EVIDENCE":

        intent = "EVIDENCE_HOLD"
        motion = "LOW"
        media = "STILL_PREFERRED"
        pace = "CONTROLLED"


    elif r == "PERSON":

        intent = "PORTRAIT_FOCUS"
        motion = "LOW"
        media = "STILL_PREFERRED"
        pace = "CONTROLLED"


    elif r == "PLACE":

        if beat in {
            "HOOK",
            "SETUP",
        }:

            intent = "ESTABLISHING"
            motion = "MEDIUM"
            media = "EITHER"

        else:

            intent = "LOCATION_DETAIL"
            motion = "LOW"
            media = "STILL_PREFERRED"

        pace = "CONTROLLED"


    elif r == "OBJECT":

        intent = "DETAIL_INSERT"
        motion = "MEDIUM"
        media = "EITHER"
        pace = "QUICK"


    else:

        intent = "DYNAMIC_CONTEXT"

        if beat in {
            "HOOK",
            "ESCALATION",
        }:

            motion = "HIGH"
            pace = "QUICK"

        else:

            motion = "MEDIUM"
            pace = "CONTROLLED"

        media = "VIDEO_PREFERRED"


    return {

        "version":
            VERSION,

        "scene":
            scene_number(
                scene
            ),

        "role":
            r,

        "rhythm":
            beat,

        "intent":
            intent,

        "motion_need":
            motion,

        "media_preference":
            media,

        "pace":
            pace,
    }


def media_type(candidate):

    if not candidate:
        return "NONE"


    raw = _s(
        candidate.get(
            "tipo"
        )
        or candidate.get(
            "type"
        )
    ).lower()


    if any(
        x in raw
        for x in (
            "video",
            "vídeo",
            "mp4",
        )
    ):
        return "VIDEO"


    if any(
        x in raw
        for x in (
            "foto",
            "photo",
            "image",
            "imagem",
            "jpg",
            "jpeg",
            "png",
        )
    ):
        return "STILL"


    return "UNKNOWN"


def source(candidate):

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


def family(candidate):

    if not candidate:
        return None


    return _u(
        candidate.get(
            "family"
        )
        or candidate.get(
            "visual_family"
        )
    )


def candidate_class(
    candidate,
    meta=None
):

    meta = (
        meta
        or {}
    )


    if not candidate:
        return "FALLBACK"


    return _u(
        meta.get(
            "class"
        )
        or candidate.get(
            "_vi611_class"
        )
        or candidate.get(
            "_vi6_class"
        )
        or candidate.get(
            "class"
        )
        or "UNKNOWN"
    )


def record_choice(
    scene,
    candidate,
    meta=None
):

    number = scene_number(
        scene
    )


    if (
        number == 1
        and _HISTORY
    ):

        reset()


    intent = sequence_intent(
        scene
    )


    event = {

        "scene":
            number,

        "intent":
            intent[
                "intent"
            ],

        "role":
            intent[
                "role"
            ],

        "rhythm":
            intent[
                "rhythm"
            ],

        "motion_need":
            intent[
                "motion_need"
            ],

        "media_type":
            media_type(
                candidate
            ),

        "source":
            source(
                candidate
            ),

        "family":
            family(
                candidate
            ),

        "class":
            candidate_class(
                candidate,
                meta
            ),
    }


    _HISTORY.append(
        event
    )


    return event


def history():

    return list(
        _HISTORY
    )


def previous():

    if not _HISTORY:
        return None


    return dict(
        _HISTORY[-1]
    )


def recent_media_types(
    limit=2
):

    return [
        event[
            "media_type"
        ]

        for event
        in _HISTORY[
            -limit:
        ]
    ]


def summary():

    videos = sum(
        1

        for event
        in _HISTORY

        if event[
            "media_type"
        ] == "VIDEO"
    )


    stills = sum(
        1

        for event
        in _HISTORY

        if event[
            "media_type"
        ] == "STILL"
    )


    return {

        "version":
            VERSION,

        "scenes":
            len(
                _HISTORY
            ),

        "videos":
            videos,

        "stills":
            stills,

        "history":
            history(),
    }


def flush(
    path=None
):

    if path is None:

        folder = os.path.expanduser(
            "~/ShortAutoPro/logs/producao"
        )

        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_25_sequence_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),
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

    _HISTORY.clear()


def self_test():

    reset()


    evidence = sequence_intent(
        {
            "retrieval_role_6_7":
                "EVIDENCE",

            "_vi68_storyboard":
                {
                    "scene": 3,
                    "rhythm": "SETUP"
                }
        }
    )


    assert (
        evidence[
            "intent"
        ]
        == "EVIDENCE_HOLD"
    )


    assert (
        evidence[
            "media_preference"
        ]
        == "STILL_PREFERRED"
    )


    context = sequence_intent(
        {
            "retrieval_role_6_7":
                "CONTEXT",

            "_vi68_storyboard":
                {
                    "scene": 6,
                    "rhythm":
                        "ESCALATION"
                }
        }
    )


    assert (
        context[
            "motion_need"
        ]
        == "HIGH"
    )


    record_choice(
        {
            "_vi68_storyboard":
                {
                    "scene": 1
                }
        },
        {
            "fonte": "Wikimedia",
            "tipo": "foto",
            "_vi6_class":
                "REAL_DOCUMENTARY",
        }
    )


    assert (
        summary()[
            "stills"
        ]
        == 1
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.25 SEQUENCE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Scene Intent"
    )
    print(
        "OK Evidence Hold"
    )
    print(
        "OK Dynamic Context"
    )
    print(
        "OK Motion Need"
    )
    print(
        "OK Sequence Memory"
    )
    print()


if __name__ == "__main__":

    self_test()

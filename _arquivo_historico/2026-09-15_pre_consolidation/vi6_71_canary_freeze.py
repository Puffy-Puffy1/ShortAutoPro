#!/usr/bin/env python3

import hashlib
import json

from datetime import datetime
from pathlib import Path


VERSION = "6.71"

BASE = Path.home() / "ShortAutoPro"

PLAN = (
    BASE
    / "logs/producao/"
      "vi6_70_canary_plan_latest.json"
)

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi6_71_canary_freeze_latest.json"
)


def fingerprint(value):

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def freeze():

    data = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )["plan"]


    candidate = data.get(
        "candidate"
    ) or {}


    preview = data.get(
        "filter_preview"
    ) or {}


    blockers = []


    if data.get("status") not in {
        "CANARY_PREVIEW_READY",
        "CANARY_PREVIEW_READY_WITH_WARNINGS",
    }:
        blockers.append(
            "vi670_plan_not_ready"
        )


    if candidate.get("role") != "CONTEXT":
        blockers.append(
            "unsafe_candidate_role"
        )


    if preview.get("status") != "PREVIEW_READY":
        blockers.append(
            "preview_not_ready"
        )


    payload = {
        "version": VERSION,

        "status":
            (
                "FROZEN"
                if not blockers
                else "HOLD"
            ),

        "scene":
            candidate.get("scene"),

        "duration_seconds":
            candidate.get(
                "duration_seconds"
            ),

        "role":
            candidate.get("role"),

        "legacy_vf":
            preview.get(
                "legacy_vf"
            ),

        "vi6_vf":
            preview.get(
                "proposed_vi6_vf"
            ),

        "source_session_fingerprint":
            candidate.get(
                "command_fingerprint"
            ),

        "decision_fingerprint":
            fingerprint(
                {
                    "candidate":
                        candidate,

                    "preview":
                        preview,
                }
            ),

        "blockers":
            blockers,

        "filter_applied":
            False,

        "video_py_modified":
            False,
    }


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

                "freeze":
                    payload,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return payload


def self_test():

    assert fingerprint(
        {"a": 1}
    ) == fingerprint(
        {"a": 1}
    )

    print(
        "VI6.71 CANARY FREEZE=PASS"
    )


if __name__ == "__main__":

    self_test()

    print(
        json.dumps(
            freeze(),
            ensure_ascii=False,
            indent=2
        )
    )

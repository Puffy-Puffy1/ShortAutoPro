#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.97"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi6_97_three_scene_canary_latest.json"
)

_EVENTS = []


def reset():

    _EVENTS.clear()

    if REPORT.exists():
        REPORT.unlink()


def record(event):

    _EVENTS.append(
        dict(event or {})
    )

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

                "version":
                    VERSION,

                "events":
                    _EVENTS,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    assert VERSION == "6.97"

    print(
        "VI6.97 TELEMETRY=PASS"
    )


if __name__ == "__main__":
    self_test()

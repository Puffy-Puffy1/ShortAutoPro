#!/usr/bin/env python3

import json
import os

from datetime import datetime


VERSION = "6.48-module"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


FLAG = os.path.join(
    BASE,
    "temp",
    "vi648_force_legacy.flag"
)


LOG = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_48_emergency_latest.json"
)


def forced_legacy():

    return os.path.exists(
        FLAG
    )


def trip(reason):

    try:

        os.makedirs(
            os.path.dirname(
                FLAG
            ),
            exist_ok=True
        )


        os.makedirs(
            os.path.dirname(
                LOG
            ),
            exist_ok=True
        )


        payload = {

            "version":
                VERSION,

            "forced_legacy":
                True,

            "reason":
                str(
                    reason
                )[:400],

            "time":
                datetime.now().isoformat(
                    timespec="seconds"
                ),
        }


        with open(
            FLAG,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                payload[
                    "reason"
                ]
                + "\n"
            )


        with open(
            LOG,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2
            )


    except Exception:

        pass


def resolve_mode(
    requested
):

    requested = str(
        requested
        or "LEGACY"
    ).strip().upper()


    if forced_legacy():

        return (
            "LEGACY",
            "emergency_force_legacy"
        )


    if requested not in {
        "LEGACY",
        "SHADOW",
        "ACTIVE",
    }:

        return (
            "LEGACY",
            "invalid_mode"
        )


    # ACTIVE ainda permanece fechado.
    if requested == "ACTIVE":

        return (
            "LEGACY",
            "active_not_authorized"
        )


    return (
        requested,
        "ok"
    )


def self_test():

    assert (
        resolve_mode(
            "LEGACY"
        )[0]
        == "LEGACY"
    )


    assert (
        resolve_mode(
            "ACTIVE"
        )[0]
        == "LEGACY"
    )


    assert (
        resolve_mode(
            "INVALID"
        )[0]
        == "LEGACY"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.48 MODULE FAILSAFE: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK LEGACY"
    )
    print(
        "OK ACTIVE blocked"
    )
    print(
        "OK Invalid -> LEGACY"
    )
    print()


if __name__ == "__main__":
    self_test()
